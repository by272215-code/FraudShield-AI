
import pandas as pd


def generate_investigation_alerts(transactions, accounts):
    """
    Transaction aur account indicators se investigation alerts banata hai.
    Alerts review ke liye hain, confirmed fraud verdict nahi.
    """

    alerts = []

    required_tx = {
        "transaction_id",
        "from_account",
        "to_account",
        "amount",
        "risk_score",
        "risk_reasons",
    }

    if not required_tx.issubset(transactions.columns):
        raise ValueError("Transaction data mein required columns missing hain.")

    required_accounts = {
    "account",
    "account_risk_score",
    "account_risk_level",
    "investigation_indicators",
    "total_sent",
    "total_received",
}

    if not required_accounts.issubset(accounts.columns):
        raise ValueError("Account analysis mein required columns missing hain.")

    # Transaction-level alerts
    for _, row in transactions.iterrows():
        score = float(row["risk_score"])

        if score >= 50:
            priority = "High" if score >= 75 else "Medium"

            alerts.append({
                "alert_id": f"TX-{row['transaction_id']}",
                "alert_type": "Transaction Pattern",
                "priority": priority,
                "risk_score": score,
                "related_accounts": (
                    f"{row['from_account']} -> {row['to_account']}"
                ),
                "transaction_ids": str(row["transaction_id"]),
                "reason": str(row["risk_reasons"]),
                "amount": float(row["amount"]),
            })

    # Account-level alerts
    for _, row in accounts.iterrows():
        score = float(row["account_risk_score"])

        if score >= 50:
            priority = "High" if score >= 75 else "Medium"

            related = transactions[
                (transactions["from_account"] == row["account"])
                | (transactions["to_account"] == row["account"])
            ]

            transaction_ids = ", ".join(
                related["transaction_id"].astype(str).tolist()
            )

            alerts.append({
                "alert_id": f"ACCT-{row['account']}",
                "alert_type": "Account Pattern",
                "priority": priority,
                "risk_score": score,
                "related_accounts": str(row["account"]),
                "transaction_ids": transaction_ids,
                "reason": str(row["investigation_indicators"]),
                "amount": float(row["total_sent"] + row["total_received"]),
            })

    columns = [
        "alert_id",
        "alert_type",
        "priority",
        "risk_score",
        "related_accounts",
        "transaction_ids",
        "reason",
        "amount",
    ]

    result = pd.DataFrame(alerts, columns=columns)

    if not result.empty:
        result = result.drop_duplicates(subset=["alert_id"])
        result = result.sort_values(
            ["risk_score", "amount"],
            ascending=False,
        ).reset_index(drop=True)

    return result
