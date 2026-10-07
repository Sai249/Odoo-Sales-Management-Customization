# Odoo Sales Management Customization

A production-style Odoo 18 add-on for managing the quotation approval process. It adds configurable approval thresholds, role-based manager/director reviews, rejection reasons, audit history, and confirmation validation to the standard Sales application.

## What is included

- A two-stage approval workflow for sales quotations.
- Configurable manager and director approval thresholds.
- Workflow roles: Sales Workflow User, Sales Workflow Manager, and Sales Workflow Director.
- A rejection wizard that requires a reason.
- An immutable-style approval audit trail shown on every quotation.
- Validation that prevents confirmation of an approval-required quotation until it is approved.
- Automatic re-submission when commercial terms or order lines change after review.
- Docker Compose, VS Code tasks, technical documentation, tests, and Git-ready project files.

## Prerequisites

- Docker Desktop (with Docker Compose v2)
- Visual Studio Code (recommended)

No local PostgreSQL or Python/Odoo installation is necessary when using Docker.

## Run the project

1. Open this folder in VS Code.
2. Copy the environment template:

   ```powershell
   Copy-Item .env.example .env
   ```

3. Start Odoo and PostgreSQL:

   ```powershell
   docker compose up -d
   ```

4. Open [http://localhost:8069](http://localhost:8069), create a database, then sign in.
5. Go to **Apps**, remove the **Apps** filter if needed, search for **Sales Management Customization**, and install it.
6. Assign users one of the workflow groups under **Settings → Users & Companies → Users → Access Rights**.
7. Configure the thresholds under **Sales → Configuration → Settings → Approval Workflow**.

For a live log while developing, run:

```powershell
docker compose logs -f odoo
```

To apply Python/XML changes after the first install, upgrade the app from Apps or run:

```powershell
docker compose exec odoo odoo -d <database_name> -u sales_management_customization --stop-after-init
```

## Workflow

| Quotation total (company currency) | Workflow |
| --- | --- |
| Below the manager threshold | Can be confirmed normally |
| At or above manager threshold | Sales Workflow Manager approval is required |
| At or above director threshold | Manager approval followed by Sales Workflow Director approval is required |

Changing key commercial fields or order lines after approval returns an approval-required quotation to the manager review queue. A quotation can only be confirmed after reaching **Approved**.

## Project layout

```text
custom_addons/sales_management_customization/  Odoo add-on
docs/                                         Technical and test documentation
.vscode/                                      Helpful Docker tasks for VS Code
docker-compose.yml                            Odoo 18 + PostgreSQL development stack
```

See [docs/TECHNICAL_DOCUMENTATION.md](docs/TECHNICAL_DOCUMENTATION.md) for the data model, permissions, and testing notes.

## Stop or reset local services

```powershell
docker compose down
```

To delete only the local Docker database and start over, use `docker compose down -v`. This intentionally removes all databases created by this project.
