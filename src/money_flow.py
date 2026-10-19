
from collections import defaultdict
import pandas as pd
import networkx as nx


def trace_money_flow(transactions, source, destination, max_hops=5):
    """
    Source se destination tak possible account paths dhoondhta hai.
    Ye transaction connectivity trace karta hai, exact fund provenance nahi.
    """

    required = {
        "transaction_id",
        "timestamp",
        "from_account",
        "to_account",
        "amount",
    }

    if not required.issubset(transactions.columns):
        raise ValueError("Transaction data mein required columns missing hain.")

    if max_hops < 1:
        raise ValueError("max_hops kam se kam 1 hona chahiye.")

    df = transactions.copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="raise")

    if df["amount"].isna().any() or (df["amount"] < 0).any():
        raise ValueError("Invalid transaction amount.")

    graph = nx.DiGraph()
    edge_transactions = defaultdict(list)

    for _, row in df.iterrows():
        sender = row["from_account"]
        receiver = row["to_account"]

        if pd.isna(sender) or pd.isna(receiver):
            continue

        graph.add_edge(sender, receiver)
        edge_transactions[(sender, receiver)].append(row.to_dict())

    if source not in graph:
        return [], "Source account dataset mein nahi mila."

    if destination not in graph:
        return [], "Destination account dataset mein nahi mila."

    if source == destination:
        return [], "Source aur destination alag hone chahiye."

    paths = []

    try:
        candidates = nx.all_simple_paths(
            graph,
            source=source,
            target=destination,
            cutoff=max_hops,
        )

        for path in candidates:
            path_details = []

            for sender, receiver in zip(path, path[1:]):
                for transaction in edge_transactions[(sender, receiver)]:
                    path_details.append({
                        "path": " → ".join(path),
                        "from_account": sender,
                        "to_account": receiver,
                        "transaction_id": transaction["transaction_id"],
                        "timestamp": transaction["timestamp"],
                        "amount": transaction["amount"],
                    })

            if path_details:
                paths.extend(path_details)

    except nx.NetworkXNoPath:
        pass

    if not paths:
        return [], "Is hop limit mein koi transaction path nahi mila."

    return paths, "Possible connected paths mil gaye."
