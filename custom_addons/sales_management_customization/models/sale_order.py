from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    approval_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("manager_pending", "Pending Manager Approval"),
            ("director_pending", "Pending Director Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval Status",
        default="not_required",
        copy=False,
        tracking=True,
        index=True,
    )
    approval_required = fields.Boolean(
        compute="_compute_approval_requirements",
        string="Approval Required",
    )
    requires_director_approval = fields.Boolean(
        compute="_compute_approval_requirements",
        string="Director Approval Required",
    )
    approval_submitted_by_id = fields.Many2one(
        "res.users",
        string="Submitted By",
        copy=False,
        readonly=True,
    )
    approval_submitted_on = fields.Datetime(copy=False, readonly=True)
    approval_reviewed_by_id = fields.Many2one(
        "res.users",
        string="Last Reviewed By",
        copy=False,
        readonly=True,
    )
    approval_reviewed_on = fields.Datetime(copy=False, readonly=True)
    rejection_reason = fields.Text(copy=False, readonly=True)
    approval_history_ids = fields.One2many(
        "sale.order.approval.history",
        "sale_order_id",
        string="Approval History",
        readonly=True,
    )

    def _get_approval_thresholds(self):
        parameters = self.env["ir.config_parameter"].sudo()
        manager_threshold = float(
            parameters.get_param("sales_management_customization.approval_threshold", "10000.0")
        )
        director_threshold = float(
            parameters.get_param("sales_management_customization.director_approval_threshold", "50000.0")
        )
        return manager_threshold, director_threshold

    def _amount_in_company_currency(self):
        self.ensure_one()
        company_currency = self.company_id.currency_id
        order_date = self.date_order or fields.Date.context_today(self)
        return self.currency_id._convert(
            self.amount_total,
            company_currency,
            self.company_id,
            order_date,
        )

    @api.depends("amount_total", "currency_id", "company_id", "date_order")
    def _compute_approval_requirements(self):
        manager_threshold, director_threshold = self._get_approval_thresholds()
        for order in self:
            amount = order._amount_in_company_currency()
            order.approval_required = amount >= manager_threshold
            order.requires_director_approval = amount >= director_threshold

    def _check_quotation_is_editable(self):
        for order in self:
            if order.state not in ("draft", "sent"):
                raise UserError(_("Only quotations can be submitted for approval."))

    def _check_group(self, group_xmlid, message):
        if not self.env.is_superuser() and not self.env.user.has_group(group_xmlid):
            raise AccessError(message)

    def _create_approval_history(self, action, from_state, to_state, note=False):
        self.ensure_one()
        self.env["sale.order.approval.history"].sudo().create(
            {
                "sale_order_id": self.id,
                "action": action,
                "from_state": from_state,
                "to_state": to_state,
                "user_id": self.env.user.id,
                "action_date": fields.Datetime.now(),
                "note": note,
            }
        )

    def _transition_approval(self, new_state, action, note=False, extra_values=None):
        self.ensure_one()
        old_state = self.approval_state
        values = {"approval_state": new_state}
        if extra_values:
            values.update(extra_values)
        self.with_context(skip_sales_approval_reset=True).write(values)
        self._create_approval_history(action, old_state, new_state, note)

    def action_submit_for_approval(self):
        self._check_group(
            "sales_management_customization.group_sales_workflow_user",
            _("Only Sales Workflow Users can submit quotations for approval."),
        )
        self._check_quotation_is_editable()
        for order in self:
            if not order.approval_required:
                raise UserError(_("This quotation is below the configured approval threshold."))
            if order.approval_state == "manager_pending":
                raise UserError(_("This quotation is already waiting for manager approval."))
            if order.approval_state not in ("not_required", "rejected"):
                raise UserError(
                    _("Only a new or rejected quotation can be submitted for approval. Change the quotation to restart review.")
                )
            order._transition_approval(
                "manager_pending",
                "submitted",
                _("Quotation submitted for manager approval."),
                {
                    "approval_submitted_by_id": self.env.user.id,
                    "approval_submitted_on": fields.Datetime.now(),
                    "approval_reviewed_by_id": False,
                    "approval_reviewed_on": False,
                    "rejection_reason": False,
                },
            )
        return True

    def action_manager_approve(self):
        self._check_group(
            "sales_management_customization.group_sales_workflow_manager",
            _("Only Sales Workflow Managers can approve this stage."),
        )
        for order in self:
            if order.approval_state != "manager_pending":
                raise UserError(_("The quotation is not awaiting manager approval."))
            next_state = "director_pending" if order.requires_director_approval else "approved"
            order._transition_approval(
                next_state,
                "manager_approved",
                _("Approved by manager."),
                {
                    "approval_reviewed_by_id": self.env.user.id,
                    "approval_reviewed_on": fields.Datetime.now(),
                    "rejection_reason": False,
                },
            )
        return True

    def action_director_approve(self):
        self._check_group(
            "sales_management_customization.group_sales_workflow_director",
            _("Only Sales Workflow Directors can approve this stage."),
        )
        for order in self:
            if order.approval_state != "director_pending":
                raise UserError(_("The quotation is not awaiting director approval."))
            order._transition_approval(
                "approved",
                "director_approved",
                _("Approved by director."),
                {
                    "approval_reviewed_by_id": self.env.user.id,
                    "approval_reviewed_on": fields.Datetime.now(),
                    "rejection_reason": False,
                },
            )
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        if self.approval_state not in ("manager_pending", "director_pending"):
            raise UserError(_("Only a quotation pending review can be rejected."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Quotation"),
            "res_model": "sale.order.approval.reject.wizard",
            "view_mode": "form",
            "view_id": self.env.ref(
                "sales_management_customization.view_sale_order_reject_wizard_form"
            ).id,
            "target": "new",
            "context": {"default_sale_order_id": self.id},
        }

    def _reject_approval(self, reason):
        self.ensure_one()
        if self.approval_state == "manager_pending":
            self._check_group(
                "sales_management_customization.group_sales_workflow_manager",
                _("Only Sales Workflow Managers can reject this stage."),
            )
        elif self.approval_state == "director_pending":
            self._check_group(
                "sales_management_customization.group_sales_workflow_director",
                _("Only Sales Workflow Directors can reject this stage."),
            )
        else:
            raise UserError(_("The quotation is no longer awaiting approval."))
        self._transition_approval(
            "rejected",
            "rejected",
            reason,
            {
                "approval_reviewed_by_id": self.env.user.id,
                "approval_reviewed_on": fields.Datetime.now(),
                "rejection_reason": reason,
            },
        )

    def _reset_approval_after_change(self, reason):
        for order in self:
            if not order.approval_required or order.state not in ("draft", "sent"):
                continue
            if order.approval_state in ("not_required", "manager_pending"):
                continue
            order._transition_approval(
                "manager_pending",
                "reset",
                reason,
                {
                    "approval_submitted_by_id": self.env.user.id,
                    "approval_submitted_on": fields.Datetime.now(),
                    "approval_reviewed_by_id": False,
                    "approval_reviewed_on": False,
                    "rejection_reason": False,
                },
            )

    def write(self, values):
        commercial_fields = {
            "partner_id",
            "partner_invoice_id",
            "partner_shipping_id",
            "pricelist_id",
            "payment_term_id",
            "fiscal_position_id",
            "validity_date",
            "date_order",
        }
        should_reset = bool(commercial_fields.intersection(values))
        result = super().write(values)
        if should_reset and not self.env.context.get("skip_sales_approval_reset"):
            self._reset_approval_after_change(_("Commercial terms were changed; approval was reset."))
        return result

    def action_confirm(self):
        for order in self:
            if order.approval_required and order.approval_state != "approved":
                raise UserError(
                    _("This quotation requires approval before it can be confirmed. Current status: %s")
                    % dict(order._fields["approval_state"].selection).get(order.approval_state)
                )
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, values_list):
        lines = super().create(values_list)
        if not self.env.context.get("skip_sales_approval_reset"):
            lines.mapped("order_id")._reset_approval_after_change(
                _("Order lines were changed; approval was reset.")
            )
        return lines

    def write(self, values):
        orders = self.mapped("order_id")
        result = super().write(values)
        if not self.env.context.get("skip_sales_approval_reset"):
            orders._reset_approval_after_change(_("Order lines were changed; approval was reset."))
        return result

    def unlink(self):
        orders = self.mapped("order_id")
        result = super().unlink()
        if not self.env.context.get("skip_sales_approval_reset"):
            orders._reset_approval_after_change(_("Order lines were changed; approval was reset."))
        return result
