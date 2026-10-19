
import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "fraudgraph_cases.db"

VALID_STATUSES = {"Open", "Under Review", "Resolved"}

TEAM_MEMBERS = [
    "Team Member 1",
    "Team Member 2",
    "Team Member 3",
    "Team Member 4",
]


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS investigation_cases (
                case_id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                risk_score REAL NOT NULL,
                related_accounts TEXT,
                transaction_ids TEXT,
                reason TEXT,
                amount REAL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Open',
                investigator_notes TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Existing database mein naye columns safely add karo.
        existing_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(investigation_cases)"
            ).fetchall()
        }

        new_columns = {
            "assigned_investigator": (
                "TEXT NOT NULL DEFAULT 'Team Member 1'"
            ),
            "review_deadline": "TEXT",
            "evidence_summary": "TEXT DEFAULT ''",
        }

        for column, definition in new_columns.items():
            if column not in existing_columns:
                conn.execute(
                    f"ALTER TABLE investigation_cases "
                    f"ADD COLUMN {column} {definition}"
                )


def sync_alerts(alerts):
    initialize_database()

    if alerts.empty:
        return

    with get_connection() as conn:
        for _, alert in alerts.iterrows():
            conn.execute("""
                INSERT OR IGNORE INTO investigation_cases (
                    case_id, alert_type, priority, risk_score,
                    related_accounts, transaction_ids, reason, amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(alert["alert_id"]),
                str(alert["alert_type"]),
                str(alert["priority"]),
                float(alert["risk_score"]),
                str(alert["related_accounts"]),
                str(alert["transaction_ids"]),
                str(alert["reason"]),
                float(alert["amount"]),
            ))


def load_cases():
    initialize_database()

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT *
            FROM investigation_cases
            ORDER BY
                CASE priority
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    ELSE 3
                END,
                updated_at DESC
        """).fetchall()

    return pd.DataFrame([dict(row) for row in rows])


def update_case(
    case_id,
    status,
    notes,
    assigned_investigator="Team Member 1",
    review_deadline=None,
    evidence_summary="",
):
    initialize_database()

    if status not in VALID_STATUSES:
        raise ValueError("Invalid case status.")

    if assigned_investigator not in TEAM_MEMBERS:
        raise ValueError("Invalid investigator.")

    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE investigation_cases
            SET status = ?,
                investigator_notes = ?,
                assigned_investigator = ?,
                review_deadline = ?,
                evidence_summary = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE case_id = ?
        """, (
            status,
            notes,
            assigned_investigator,
            str(review_deadline) if review_deadline else None,
            evidence_summary,
            case_id,
        ))

        if cursor.rowcount == 0:
            raise ValueError("Case nahi mila.")
