"""
Budget App — combined Tracker + Dashboard
Single Flask process, SQLite storage, no pandas dependency.
"""
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)

DB_PATH         = os.environ.get("DB_PATH", "/data/budget.db")
WEEKLY_LIMIT    = int(os.environ.get("WEEKLY_LIMIT", 500))
APP_TITLE       = os.environ.get("APP_TITLE", "Budget Tracker")
CURRENCY_SYMBOL = os.environ.get("CURRENCY_SYMBOL", "$")
CATEGORIES   = list(dict.fromkeys(
    category.strip()
    for category in os.environ.get("CATEGORIES", "Food,Groceries").split(",")
    if category.strip()
))
if not CATEGORIES:
    raise ValueError("CATEGORIES must contain at least one comma-separated category")


@app.context_processor
def inject_app_settings():
    return {
        "app_title": APP_TITLE,
        "currency_symbol": CURRENCY_SYMBOL,
    }


CATEGORY_PALETTE = [
    ("#e8448c", "#fce7f3", "#be185d", "#4a1535", "#f9a8d4"),
    ("#2d8ff4", "#dbeafe", "#1d4ed8", "#1e3a5f", "#93c5fd"),
    ("#f59e0b", "#fef3c7", "#92400e", "#4a3210", "#fbbf24"),
    ("#22c55e", "#dcfce7", "#166534", "#143d25", "#86efac"),
    ("#8b5cf6", "#ede9fe", "#5b21b6", "#31205f", "#c4b5fd"),
    ("#14b8a6", "#ccfbf1", "#115e59", "#123f3b", "#5eead4"),
    ("#f97316", "#ffedd5", "#9a3412", "#4a2715", "#fdba74"),
    ("#ec4899", "#fce7f3", "#9d174d", "#4a1535", "#f9a8d4"),
]

# ─────────────────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                description TEXT    NOT NULL,
                category    TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                year_week   TEXT    NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_year_week ON transactions(year_week)")
        conn.commit()


# ─────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────

def yearweek_for(dt: datetime) -> str:
    y, w, _ = dt.isocalendar()
    return f"{y}-W{w:02d}"


def category_styles(categories):
    names = list(CATEGORIES)
    names.extend(sorted(set(categories) - set(CATEGORIES)))
    styles = {}
    for index, name in enumerate(names):
        color, background, text, dark_background, dark_text = CATEGORY_PALETTE[
            index % len(CATEGORY_PALETTE)
        ]
        styles[name] = {
            "category_color": color,
            "category_badge_background": background,
            "category_badge_color": text,
            "category_dark_badge_background": dark_background,
            "category_dark_badge_color": dark_text,
        }
    return styles


# ─────────────────────────────────────────────────────────────────
# Tracker helpers
# ─────────────────────────────────────────────────────────────────

def get_weekly_summary():
    now = datetime.now()
    yw  = yearweek_for(now)
    with get_db() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount),0) AS total FROM transactions WHERE year_week=?",
            (yw,)
        ).fetchone()
    budget_available = WEEKLY_LIMIT - row["total"]
    days_to_end      = 6 - now.weekday()
    return budget_available, days_to_end


def get_last_week_summary():
    yw = yearweek_for(datetime.now() - timedelta(weeks=1))
    with get_db() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount),0) AS total FROM transactions WHERE year_week=?",
            (yw,)
        ).fetchone()
    total = row["total"]
    return total, WEEKLY_LIMIT - total


def get_current_week_rows():
    yw = yearweek_for(datetime.now())
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE year_week=? ORDER BY date ASC",
            (yw,)
        ).fetchall()

    styles = category_styles(r["category"] for r in rows)
    running = 0.0
    enriched = []
    for r in rows:
        running += r["amount"]
        enriched.append({
            **dict(r),
            **styles[r["category"]],
            "weekly_total": round(running, 2),
        })
    enriched.reverse()   # newest first for display
    return enriched


# ─────────────────────────────────────────────────────────────────
# Dashboard helpers
# ─────────────────────────────────────────────────────────────────

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def all_year_weeks():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT year_week FROM transactions ORDER BY year_week"
        ).fetchall()
    weeks = [r["year_week"] for r in rows]
    # Always include current week even if empty
    current = yearweek_for(datetime.now())
    if current not in weeks:
        weeks.append(current)
    return sorted(weeks)


def week_transactions(yw: str):
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM transactions WHERE year_week=? ORDER BY date DESC",
            (yw,)
        ).fetchall()]


def build_dashboard_data(yw: str):
    rows = week_transactions(yw)

    # ── parse week date range ──────────────────────────────────
    year, week = yw.split("-W")
    year, week = int(year), int(week)
    monday = datetime.fromisocalendar(year, week, 1).date()
    sunday = datetime.fromisocalendar(year, week, 7).date()
    week_range_label = f"{monday.strftime('%b %d, %Y')} – {sunday.strftime('%b %d, %Y')}"

    today     = datetime.now().date()
    days_left = max((sunday - today).days, 0)

    # ── totals ────────────────────────────────────────────────
    total_spend = round(sum(r["amount"] for r in rows), 2)
    remaining   = round(WEEKLY_LIMIT - total_spend, 2)

    # ── category breakdown ────────────────────────────────────
    by_category = {}
    for r in rows:
        by_category[r["category"]] = by_category.get(r["category"], 0) + r["amount"]
    styles = category_styles(by_category)
    category_names = list(styles)
    category_total = sum(by_category.values())

    # ── highest transaction ────────────────────────────────────
    if rows:
        highest = max(rows, key=lambda r: r["amount"])
    else:
        highest = {"amount": 0, "description": "—"}

    # ── daily pivot (Mon–Sun) ─────────────────────────────────
    pivot = {day: {cat: 0.0 for cat in category_names} for day in DAY_ORDER}
    for r in rows:
        dt       = datetime.strptime(r["date"], "%Y-%m-%d %H:%M:%S")
        day_name = dt.strftime("%A")
        cat      = r["category"]
        if day_name in pivot and cat in pivot[day_name]:
            pivot[day_name][cat] += r["amount"]

    category_data = []
    for category in category_names:
        daily = [round(pivot[day][category], 2) for day in DAY_ORDER]
        total = round(by_category.get(category, 0), 2)
        category_data.append({
            "name": category,
            "total": total,
            "pct": round((total / category_total) * 100, 1) if category_total else 0,
            "daily": daily,
            **styles[category],
        })

    daily_totals = [
        round(sum(pivot[day].values()), 2)
        for day in DAY_ORDER
    ]

    max_val = max(daily_totals) if max(daily_totals) > 0 else 1
    scale   = 180 / max_val

    for category in category_data:
        category["heights"] = [int(value * scale) for value in category["daily"]]

    for transaction in rows:
        transaction.update(styles[transaction["category"]])

    tick_step = max_val / 5
    y_ticks   = [round(tick_step * i, 1) for i in range(6)]

    return dict(
        budget           = WEEKLY_LIMIT,
        total_spend      = total_spend,
        remaining        = remaining,
        days_left        = days_left,
        week_range_label = week_range_label,
        category_data    = category_data,
        highest_item     = highest,
        day_order        = DAY_ORDER,
        daily_totals     = daily_totals,
        y_ticks          = y_ticks,
        y_max            = max_val,
        transactions     = rows,
        last_refreshed   = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


# ─────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────

@app.route("/")
def root():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    weeks    = all_year_weeks()
    selected = request.args.get("YearWeek", weeks[-1] if weeks else yearweek_for(datetime.now()))
    if selected not in weeks:
        selected = weeks[-1]

    data = build_dashboard_data(selected)
    return render_template("dashboard.html",
        weeks=weeks, selected_week=selected, **data)


@app.route("/frameo")
def frameo():
    """Lightweight dashboard for low-power displays (Frameo, e-ink, kiosk).
    Pure HTML/CSS — no JavaScript, no web fonts, minimal CPU/GPU load."""
    weeks    = all_year_weeks()
    selected = yearweek_for(datetime.now())
    if selected not in weeks:
        selected = weeks[-1] if weeks else selected
    data = build_dashboard_data(selected)
    return render_template("frameo.html", selected_week=selected, **data)


@app.route("/tracker", methods=["GET", "POST"])
def tracker():
    if request.method == "POST":
        now      = datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        yw       = yearweek_for(now)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO transactions (date,description,category,amount,year_week) VALUES (?,?,?,?,?)",
                (date_str,
                 request.form["description"],
                 request.form["category"],
                 float(request.form["amount"]),
                 yw)
            )
            conn.commit()
        return redirect(url_for("tracker"))

    budget_available, days_to_end    = get_weekly_summary()
    last_week_total,  last_week_diff = get_last_week_summary()
    rows = get_current_week_rows()

    return render_template("tracker.html",
        data             = rows,
        categories       = CATEGORIES,
        budget_available = budget_available,
        days_to_end      = days_to_end,
        weekly_limit     = WEEKLY_LIMIT,
        last_week_total  = last_week_total,
        last_week_diff   = last_week_diff,
    )


@app.route("/delete/<int:row_id>")
def delete(row_id):
    with get_db() as conn:
        conn.execute("DELETE FROM transactions WHERE id=?", (row_id,))
        conn.commit()
    return redirect(url_for("tracker"))


@app.route("/edit/<int:row_id>", methods=["GET", "POST"])
def edit(row_id):
    with get_db() as conn:
        if request.method == "POST":
            conn.execute(
                "UPDATE transactions SET description=?,category=?,amount=? WHERE id=?",
                (request.form["description"],
                 request.form["category"],
                 float(request.form["amount"]),
                 row_id)
            )
            conn.commit()
            return redirect(url_for("tracker"))
        row = dict(conn.execute(
            "SELECT * FROM transactions WHERE id=?", (row_id,)
        ).fetchone())
    return render_template("edit.html", row=row, categories=CATEGORIES)


# ─────────────────────────────────────────────────────────────────
init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3080, debug=False)
