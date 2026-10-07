from odoo import fields, models


class SaleOrderApprovalHistory(models.Model):
    """An audit record produced by the sales approval workflow methods."""

    _name = "sale.order.approval.history"
    _description = "Sales Order Approval History"
    _order = "action_date desc, id desc"
    _rec_name = "sale_order_id"

    sale_order_id = fields.Many2one(
        "sale.order",
        required=True,
        ondelete="cascade",
        index=True,
        readonly=True,
    )
    action = fields.Selection(
        [
            ("submitted", "Submitted for approval"),
            ("manager_approved", "Manager approved"),
            ("director_approved", "Director approved"),
            ("rejected", "Rejected"),
            ("reset", "Approval reset"),
        ],
        required=True,
        readonly=True,
    )
    from_state = fields.Selection(
        selection=lambda self: self.env["sale.order"]._fields["approval_state"].selection,
        required=True,
        readonly=True,
    )
    to_state = fields.Selection(
        selection=lambda self: self.env["sale.order"]._fields["approval_state"].selection,
        required=True,
        readonly=True,
    )
    user_id = fields.Many2one("res.users", required=True, readonly=True)
    action_date = fields.Datetime(required=True, readonly=True)
    note = fields.Text(readonly=True)
