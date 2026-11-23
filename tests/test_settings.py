import importlib
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


def setUpModule():
    global budget, import_dir
    import_dir = tempfile.TemporaryDirectory()
    with patch.dict(os.environ, {"DB_PATH": os.path.join(import_dir.name, "import.db")}):
        budget = importlib.import_module("app")


def tearDownModule():
    import_dir.cleanup()


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.old_path = budget.DB_PATH
        self.addCleanup(setattr, budget, "DB_PATH", self.old_path)
        budget.DB_PATH = os.path.join(self.directory.name, "budget.db")
        with patch.dict(os.environ, {
            "WEEKLY_LIMIT": "750",
            "CATEGORIES": "Food, Travel,Food",
            "CURRENCY_SYMBOL": "£",
        }):
            budget.init_db()
        self.client = budget.app.test_client()

    def test_initialization_and_settings_persist_across_restart(self):
        response = self.client.get("/settings")
        self.assertIn(b"750.0", response.data)
        self.assertIn("Food\nTravel".encode(), response.data)
        self.assertIn("£".encode(), response.data)
        response = self.client.post("/settings", data={
            "weekly_limit": "1200.50",
            "categories": "Home\nDining",
            "currency_symbol": "€",
        })
        self.assertEqual(response.status_code, 302)
        with patch.dict(os.environ, {
            "WEEKLY_LIMIT": "invalid",
            "CATEGORIES": "",
            "CURRENCY_SYMBOL": "",
        }):
            budget.init_db()
        response = self.client.get("/settings")
        self.assertIn(b"1200.5", response.data)
        self.assertIn(b"Home\nDining", response.data)
        self.assertIn("€".encode(), response.data)

    def test_settings_apply_everywhere_and_preserve_old_categories(self):
        self.client.post("/tracker", data={
            "description": "Lunch", "category": "Food", "amount": "10",
        })
        with budget.get_db() as conn:
            row_id = conn.execute("SELECT id FROM transactions").fetchone()["id"]
        self.client.post("/settings", data={
            "weekly_limit": "100", "categories": "Travel\nHome", "currency_symbol": "€",
        })
        for path in ("/dashboard", "/tracker", "/frameo"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("€90.00".encode(), response.data, path)
            self.assertIn(b"Food", response.data, path)
        tracker = self.client.get("/tracker").get_data(as_text=True)
        self.assertIn('<option value="Home">Home</option>', tracker)
        self.assertNotIn('<option value="Food">Food</option>', tracker)
        edit = self.client.get(f"/edit/{row_id}").get_data(as_text=True)
        self.assertIn('<option value="Food" selected>Food</option>', edit)
        self.client.post(f"/edit/{row_id}", data={
            "description": "Updated lunch", "category": "Food", "amount": "10",
        })
        self.assertIn(b"Updated lunch", self.client.get("/tracker").data)

    def test_invalid_input_does_not_change_saved_settings(self):
        for limit, categories, symbol in [
            ("0", "Home", "$"),
            ("nan", "Home", "$"),
            ("0.001", "Home", "$"),
            ("100", " \n ", "$"),
            ("100", "Home\nHome", "$"),
            ("100", "Home", " "),
            ("100", "Home", "a" * 17),
        ]:
            with self.subTest(limit=limit, categories=categories, symbol=symbol):
                response = self.client.post("/settings", data={
                    "weekly_limit": limit, "categories": categories, "currency_symbol": symbol,
                })
                self.assertEqual(response.status_code, 400)
                self.assertIn(b'role="alert"', response.data)
                with budget.app.test_request_context():
                    self.assertEqual(budget.get_settings()["weekly_limit"], 750)
                    self.assertEqual(budget.get_settings()["categories"], ["Food", "Travel"])
                    self.assertEqual(budget.get_settings()["currency_symbol"], "£")

    def test_defaults_without_legacy_environment(self):
        budget.DB_PATH = os.path.join(self.directory.name, "defaults.db")
        with patch.dict(os.environ, {}, clear=True):
            budget.init_db()
        with budget.app.test_request_context():
            self.assertEqual(budget.get_settings(), {
                "weekly_limit": 500, "categories": ["Food", "Groceries"],
                "currency_symbol": "$",
            })

    def test_existing_database_is_migrated_without_losing_transactions(self):
        budget.DB_PATH = os.path.join(self.directory.name, "legacy.db")
        with sqlite3.connect(budget.DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
                    description TEXT NOT NULL, category TEXT NOT NULL,
                    amount REAL NOT NULL, year_week TEXT NOT NULL
                )
            """)
            conn.execute(
                "INSERT INTO transactions (date, description, category, amount, year_week) "
                "VALUES (?, ?, ?, ?, ?)",
                ("2025-01-01 12:00:00", "Old purchase", "Food", 10, "2025-W01"),
            )
        with patch.dict(os.environ, {"WEEKLY_LIMIT": "900", "CATEGORIES": "Travel",
                                     "CURRENCY_SYMBOL": "€"}):
            budget.init_db()
        response = self.client.get("/dashboard?YearWeek=2025-W01")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Old purchase", response.data)
        self.assertIn("€890.00".encode(), response.data)


if __name__ == "__main__":
    unittest.main()
