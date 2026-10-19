
import pandas as pd


def analyze_transactions_data(transactions):
    """
    Transaction risk ko simple heuristic rules se assess karta hai.
    Sirf repeated payments ko High Risk nahi maana jata.
    """

    df = transactions.copy()

    required = {
        "transaction_id",
        "timestamp",
        "from_account",
        "to_account",
        "amount",
    }

    if not required.issubset(df.columns):
        raise ValueError("CSV mein required transaction columns missing hain.")

    # Amount ko numeric format mein convert karo
    df["amount"] = pd.to_numeric(df["amount"], errors="raise")

    if df["amount"].isna().any() or (df["amount"] < 0).any():
        raise ValueError("Transaction amount valid hona chahiye.")

    # Missing account details ko handle karo
    df["from_account"] = (
        df["from_account"].fillna("UNKNOWN_SENDER").astype(str)
    )
    df["to_account"] = (
        df["to_account"].fillna("UNKNOWN_RECEIVER").astype(str)
    )

    # Uploaded data mein transaction frequency
    sender_counts = df["from_account"].value_counts()
    receiver_counts = df["to_account"].value_counts()

    scores = []
    reasons_list = []

    for _, row in df.iterrows():
        score = 0
        reasons = []

        # High amount ek signal hai, fraud ka proof nahi
        if row["amount"] >= 150000:
            score += 30
            reasons.append("Very high transaction amount")
        elif row["amount"] >= 50000:
            score += 15
            reasons.append("High transaction amount")

        # Frequency ko low weight diya gaya hai
        if sender_counts.get(row["from_account"], 0) >= 3:
            score += 10
            reasons.append("Repeated outgoing transactions")

        if receiver_counts.get(row["to_account"], 0) >= 3:
            score += 10
            reasons.append("Repeated incoming transactions")

        if sender_counts.get(row["from_account"], 0) >= 5:
            score += 10
            reasons.append("Frequent outgoing transactions")

        scores.append(min(score, 100))

        if reasons:
            reasons_list.append(", ".join(reasons))
        else:
            reasons_list.append("No configured risk indicators found")

    df["risk_score"] = scores

    # High Risk ke liye multiple indicators chahiye
    df["risk_level"] = df["risk_score"].apply(
        lambda score: (
            "High" if score >= 60
            else "Medium" if score >= 25
            else "Low"
        )
    )

    df["risk_reasons"] = reasons_list

    return df


def analyze_transactions(file_path):
    """CSV file read karke transactions ka risk assess karta hai."""
    transactions = pd.read_csv(file_path)
    return analyze_transactions_data(transactions)
