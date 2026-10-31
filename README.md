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
git clone https://github.com/stevenea985/budget-tracker.git
cd budget-tracker
docker compose up -d --build
```

Open [http://localhost:3080](http://localhost:3080).

The Compose setup stores the database at `/DATA/AppData/budget_app/data/budget.db` on the host. To use a different location, change the host path in the `volumes` section of `docker-compose.yml`. Back up this directory regularly.

## Configuration

The app's default settings are in the `environment` section of `docker-compose.yml`. Edit them there to change the weekly limit, categories, or timezone. The app title and currency symbol can also be set in a `.env` file in the project directory:

```dotenv
APP_TITLE=Budget Tracker
CURRENCY_SYMBOL="$"
```

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `/data/budget.db` | SQLite database path inside the container; change in Compose if needed |
| `WEEKLY_LIMIT` | `500` | Weekly budget, in the units you choose |
| `CATEGORIES` | `Food,Groceries` | Comma-separated transaction categories |
| `TZ` | `Etc/UTC` | Timezone used for transaction timestamps and week calculations |
| `CURRENCY_SYMBOL` | `$` | Display symbol only; changing it does not convert amounts |
| `APP_TITLE` | `Budget Tracker` | Name shown in the app and browser title |

For another currency symbol, set `CURRENCY_SYMBOL` to a value such as `€`, `£`, or `¥`. The app does not perform currency conversion.

## ZimaOS / CasaOS

### Publish the image to GitHub Container Registry

The ZimaOS Compose file uses `ghcr.io/stevenea985/budget-tracker:latest`. This checkout does not include a GitHub Actions workflow to publish the image, so publish that package to GitHub Container Registry before installing. Make the package public in its **Package settings** so ZimaOS can pull it without registry credentials; this is separate from making the source repository public.

In ZimaOS, open **App Store → Custom Install → Compose**, paste the ZimaOS Compose file, and install. The `pull_policy: always` setting tells Docker Compose to check GHCR for the current image when deploying.

The ZimaOS Compose template supports app title, currency symbol, timezone, and budget changes through its environment section. Keep its database mount path, `/DATA/AppData/budget_app/data:/data`, unchanged when updating if you want to continue using the same database. Back up the database before replacing an existing deployment. Stop or uninstall a previous deployment first, but do not delete its app data; duplicate deployments can conflict because they use the same container name and port.

For code updates, publish the updated image to the same GHCR package, then redeploy/update the ZimaOS app so it pulls the new `latest` image. To use this template for a fork, change the Compose `image` value to the fork's GHCR package path.

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

Python 3.12 · Flask · SQLite · Gunicorn · Jinja templates · Docker
