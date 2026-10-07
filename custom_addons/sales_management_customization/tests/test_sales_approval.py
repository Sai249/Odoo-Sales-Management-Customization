from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestSalesApprovalWorkflow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_management_customization.approval_threshold", "100.0"
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_management_customization.director_approval_threshold", "1000.0"
        )
        cls.partner = cls.env["res.partner"].create({"name": "Approval Test Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Approval Test Product", "list_price": 200.0}
        )

    def _create_order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1, "price_unit": 200.0})
                ],
            }
        )

    def test_confirmation_is_blocked_before_approval(self):
        order = self._create_order()
        self.assertTrue(order.approval_required)
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_submission_creates_an_audit_entry(self):
        order = self._create_order()
        order.action_submit_for_approval()
        self.assertEqual(order.approval_state, "manager_pending")
        self.assertEqual(len(order.approval_history_ids), 1)
        self.assertEqual(order.approval_history_ids.action, "submitted")
