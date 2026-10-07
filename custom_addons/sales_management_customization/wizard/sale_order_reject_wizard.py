from odoo import _, fields, models
from odoo.exceptions import ValidationError


class SaleOrderApprovalRejectWizard(models.TransientModel):
    _name = "sale.order.approval.reject.wizard"
    _description = "Reject Sales Order Approval"

    sale_order_id = fields.Many2one("sale.order", required=True, readonly=True)
    reason = fields.Text(required=True)

    def action_reject(self):
        self.ensure_one()
        if not self.reason.strip():
            raise ValidationError(_("A rejection reason is required."))
        self.sale_order_id._reject_approval(self.reason.strip())
        return {"type": "ir.actions.act_window_close"}
