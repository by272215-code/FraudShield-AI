
import pandas as pd


def analyze_account_network(transactions):
    """Account-level investigation indicators aur heuristic risk score."""

    required = {
        "from_account",
        "to_account",
        "amount",
        "risk_score",
    }

    if not required.issubset(transactions.columns):
        raise ValueError("Required transaction columns missing hain.")

    df = transactions.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="raise")
    df["risk_score"] = pd.to_numeric(df["risk_score"], errors="raise")

    if (
        df["amount"].isna().any()
        or df["risk_score"].isna().any()
        or (df["amount"] < 0).any()
        or (df["risk_score"] < 0).any()
        or (df["risk_score"] > 100).any()
    ):
        raise ValueError("Invalid amount ya risk score.")

    # Accounts aur connected groups.
    import networkx as nx

    graph = nx.Graph()

    for _, row in df.iterrows():
        source = row["from_account"]
        target = row["to_account"]

        if pd.isna(source) or pd.isna(target):
            continue

        graph.add_edge(source, target)

    group_lookup = {}

    for group_id, members in enumerate(
        nx.connected_components(graph), start=1
    ):
        for account in members:
            group_lookup[account] = group_id

    accounts = sorted(
        set(df["from_account"].dropna())
        | set(df["to_account"].dropna())
    )

    rows = []

    for account in accounts:
        outgoing = df[df["from_account"] == account]
        incoming = df[df["to_account"] == account]

        sent = float(outgoing["amount"].sum())
        received = float(incoming["amount"].sum())

        sent_count = len(outgoing)
        received_count = len(incoming)

        score = 0
        indicators = []

        # Independent indicators. These are not proof of fraud.
        if sent_count >= 3:
            score += 25
            indicators.append("Multiple outgoing transfers")

        if received_count >= 3:
            score += 25
            indicators.append("Multiple incoming transfers")

        if sent >= 100000:
            score += 25
            indicators.append("High total outgoing value")

        if received >= 100000:
            score += 25
            indicators.append("High total incoming value")

        score = min(score, 100)

        level = (
    "High" if score >= 50
    else "Medium" if score >= 25
    else "Low"
)

        linked = pd.concat([outgoing, incoming])

        max_transaction_risk = (
            float(linked["risk_score"].max())
            if not linked.empty else 0.0
        )

        rows.append({
            "account": account,
            "transactions_sent": sent_count,
            "transactions_received": received_count,
            "total_sent": sent,
            "total_received": received,
            "net_flow": received - sent,
            "connected_group": group_lookup.get(account, 0),
            "max_linked_transaction_risk": max_transaction_risk,
            "account_risk_score": score,
            "account_risk_level": level,
            "investigation_indicators": (
                "; ".join(indicators)
                if indicators else "No configured indicator triggered"
            ),
        })

    result = pd.DataFrame(rows)

    if not result.empty:
        result = result.sort_values(
            ["account_risk_score", "max_linked_transaction_risk"],
            ascending=False,
        ).reset_index(drop=True)

    return result
