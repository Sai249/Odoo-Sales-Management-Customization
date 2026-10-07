from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        readonly=True,
    )
    approval_threshold = fields.Monetary(
        string="Manager Approval Threshold",
        config_parameter="sales_management_customization.approval_threshold",
        currency_field="company_currency_id",
        help="Quotations at or above this total require manager approval.",
    )
    director_approval_threshold = fields.Monetary(
        string="Director Approval Threshold",
        config_parameter="sales_management_customization.director_approval_threshold",
        currency_field="company_currency_id",
        help="Quotations at or above this total require manager and director approval.",
    )

    @api.constrains("approval_threshold", "director_approval_threshold")
    def _check_approval_thresholds(self):
        for settings in self:
            if settings.approval_threshold < 0 or settings.director_approval_threshold < 0:
                raise ValidationError(_("Approval thresholds cannot be negative."))
            if settings.director_approval_threshold < settings.approval_threshold:
                raise ValidationError(
                    _("The director approval threshold must be greater than or equal to the manager threshold.")
                )
