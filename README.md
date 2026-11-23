# Budget Tracker

A self-hosted weekly budget tracker with a transaction list and spending dashboard. It runs in Docker and stores its data in a local SQLite database.

## Features

- Weekly spending dashboard with category breakdown and transaction history
- Add, edit, and delete transactions
- Configurable weekly budget, categories, timezone, currency symbol, and app title
- SQLite database stored separately from the container
- Responsive layout and system-aware dark mode

## Requirements

- Docker Engine
- Docker Compose v2

## Quick start

Clone the repository and start the app:

```sh
git clone https://github.com/stvnmn/budget-tracker.git
cd budget-tracker
docker compose up -d --build
```

Open [http://localhost:3080](http://localhost:3080).

The Compose setup stores the database at `/DATA/AppData/budget_app/data/budget.db` on the host. To use a different location, change the host path in the `volumes` section of `docker-compose.yml`. Back up this directory regularly.

## Configuration

Open **Settings** in the app to change the weekly limit, categories, and currency symbol. Settings are saved in the SQLite database and persist across container restarts and updates. Enter one category per line; removing or renaming a category does not change existing transactions. Historical transactions remain visible and retain their original category.

The weekly limit applies to all displayed weeks, including historical weeks. The currency symbol is for display only; changing it does not convert amounts.

Set the timezone in the `environment` section of `docker-compose.yml`. The app title can also be set in a `.env` file in the project directory:

```dotenv
APP_TITLE=Budget Tracker
```

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `/data/budget.db` | SQLite database path inside the container; change in Compose if needed |
| `TZ` | `Etc/UTC` | Timezone used for transaction timestamps and week calculations |
| `APP_TITLE` | `Budget Tracker` | Name shown in the app and browser title |

New databases default to a weekly limit of 500, categories Food and Groceries, and the `$` symbol.

### Upgrading from environment-based settings

On the first start with this version, the app initializes database settings from the existing `WEEKLY_LIMIT`, `CATEGORIES` (comma-separated), and `CURRENCY_SYMBOL` environment variables, if supplied. If replacing your Compose file, keep your old values in its `environment` section for that first start, or enter them on the Settings page afterward. Once initialized, the saved settings take precedence and these variables can be removed; changing them later will not change saved settings.

## ZimaOS / CasaOS

### Publish the image to GitHub Container Registry

The workflow in `.github/workflows/publish-image.yml` automatically builds and publishes multi-architecture images (`linux/amd64` and `linux/arm64`) to `ghcr.io/stvnmn/budget-tracker` when code is pushed to `main` or a version tag such as `v1.0.0` is pushed. It also supports manual runs from the repository's **Actions** tab. The `main` branch image is tagged `latest`, which is what the ZimaOS Compose file uses. The workflow uses GitHub's built-in token; no registry credentials need to be added to repository secrets.

After the first successful workflow run, open the container package from the repository's **Packages** section and set its visibility to **Public** in **Package settings** so ZimaOS can pull without registry credentials. This is separate from making the source repository public.

In ZimaOS, open **App Store → Custom Install → Compose**, paste the ZimaOS Compose file, and install. The `pull_policy: always` setting tells Docker Compose to check GHCR for the current image when deploying.

The ZimaOS Compose template supports app title and timezone changes through its environment section. Use the Settings page for the weekly limit, categories, and currency symbol. Keep its database mount path, `/DATA/AppData/budget_app/data:/data`, unchanged when updating if you want to continue using the same database. Back up the database before replacing an existing deployment. Stop or uninstall a previous deployment first, but do not delete its app data; duplicate deployments can conflict because they use the same container name and port.

For code updates, push to `main`, wait for the **Publish container image** workflow to succeed, then redeploy/update the ZimaOS app so it pulls the new `latest` image. To use this template for a fork, change the image in both the workflow and the Compose file to the fork's GHCR package path.

## Security and privacy

The app stores transactions in its SQLite database on the host; the repository and container image contain the application, not your runtime database. Do not commit `.env` files, database backups, or personal transaction data.

The app does **not** provide user accounts, authentication, or access control. Anyone who can reach the published port (`3080` by default) may be able to view or change the budget data. Keep it on a trusted network; do not expose it directly to the public internet. For remote access, use a VPN or an access-controlled HTTPS reverse proxy.

Making the source repository or container image public makes the code and image downloadable by anyone; it does not by itself expose your NAS or its database.

## Data backup

The database is stored in `/DATA/AppData/budget_app/data/budget.db` by default. To make a consistent backup, stop the container, copy the file to a safe location outside the repository, then start the container again. The default container name is `budget_app`:

```sh
docker stop budget_app
cp /DATA/AppData/budget_app/data/budget.db "$HOME/budget-backup.db"
docker start budget_app
```

Do not commit the backup file. If you changed the host data path in Compose, use that path instead.

## Tech stack

Python (version specified in `Dockerfile`) · Flask · SQLite · Gunicorn · Jinja templates · Docker
