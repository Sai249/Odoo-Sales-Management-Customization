# Technical Documentation

## Architecture

The `sales_management_customization` module extends Odoo's `sale.order` model; it does not replace the standard quotation/order flow. The module uses the existing Odoo ORM, standard Sales models, and PostgreSQL database supplied by Odoo.

### Added models

| Model | Purpose |
| --- | --- |
| `sale.order` (inherited) | Stores the approval state, reviewer metadata, calculated approval requirements, and confirmation guard. |
| `sale.order.approval.history` | Read-only audit entries for submission, approval, rejection, and re-submission. |
| `sale.order.approval.reject.wizard` | A transient form that enforces a rejection reason. |
| `res.config.settings` (inherited) | Stores configurable manager/director thresholds in `ir.config_parameter`. |

## Workflow states

```text
Not Required ───────► Confirm quotation

Manager Pending ──manager──► Approved ─────► Confirm quotation
       │
       └──manager──► Rejected

Manager Pending ──manager──► Director Pending ──director──► Approved
       │                             │
       └────────── manager ──────────┴──────────► Rejected
```

If a reviewed quotation is changed, it returns to **Manager Pending** and a `reset` audit record is created.

## Security roles

| Group | Permissions |
| --- | --- |
| Sales Workflow User | Can submit approval-required quotations and view audit history. |
| Sales Workflow Manager | Includes Workflow User permissions; can approve/reject manager-stage quotations and use Sales manager features. |
| Sales Workflow Director | Includes Manager permissions; can approve/reject director-stage quotations. |

The Python methods also verify groups, so access is enforced even if a request bypasses the form buttons. Audit records are created by trusted server-side workflow methods and users receive read-only access.

## Configuration

Values live in Odoo's `ir.config_parameter` table:

- `sales_management_customization.approval_threshold` (default `10000.0`)
- `sales_management_customization.director_approval_threshold` (default `50000.0`)

The quotation total is converted into the company currency before comparison. Director threshold must be at least equal to the manager threshold.

## Verification checklist

1. Install the module on a fresh Odoo database.
2. Assign a test salesperson, manager, and director the matching workflow roles.
3. Set thresholds to 100 and 1,000 in Sales Settings.
4. Create a 200 quotation, submit it, approve it as manager, and confirm it.
5. Create a 1,200 quotation, approve it as manager then director, and confirm it.
6. Reject a quotation and verify the reason and audit record appear on its Approval Workflow tab.
7. Change a reviewed quotation's quantity or price and verify it returns to Manager Pending.
8. Attempt to confirm a pending quotation and verify that Odoo blocks the action.

## Automated test command

With a database named `odoo_dev` and the container running:

```powershell
docker compose exec odoo odoo -d odoo_dev -i sales_management_customization --test-enable --stop-after-init
```

Run this against a disposable test database: installation and tests may create or modify test data.
