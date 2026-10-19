
from pathlib import Path
import sqlite3
import re

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from reportlab.lib import colors
from reportlab.lib import colors as pdf_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from io import BytesIO
from src.fraud_engine import analyze_transactions, analyze_transactions_data
from src.graph_analysis import analyze_account_network
from src.money_flow import trace_money_flow
from src.alert_engine import generate_investigation_alerts
from src.case_manager import sync_alerts, load_cases, update_case, TEAM_MEMBERS


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "transactions.csv"


def create_evidence_report(case_row):
    """Selected investigation case ki PDF report generate kare."""
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(
        "FraudShield AI",
        styles["Title"],
    ))
    story.append(Paragraph(
        "Investigation Evidence Report",
        styles["Heading2"],
    ))
    story.append(Spacer(1, 16))

    fields = [
        ("Case ID", "case_id"),
        ("Priority", "priority"),
        ("Risk Score", "risk_score"),
        ("Status", "status"),
        ("Assigned Investigator", "assigned_investigator"),
        ("Review Deadline", "review_deadline"),
        ("Related Accounts", "related_accounts"),
        ("Related Transactions", "transaction_ids"),
        ("Alert Reason", "reason"),
        ("Investigation Notes", "investigator_notes"),
        ("Evidence Summary", "evidence_summary"),
        ("Last Updated", "updated_at"),
    ]

    table_data = [["Field", "Details"]]

    for label, key in fields:
        value = case_row.get(key, "")
        if pd.isna(value):
            value = "Not provided"

        table_data.append([
            Paragraph(str(label), styles["BodyText"]),
            Paragraph(str(value), styles["BodyText"]),
        ])

    table = Table(table_data, colWidths=[145, 365], repeatRows=1)

    
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),
         pdf_colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), pdf_colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, pdf_colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))


    story.append(table)
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Note: This report summarizes the available case records. "
        "Risk indicators require investigator verification and do not "
        "by themselves establish fraud.",
        styles["Italic"],
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


st.set_page_config(
    page_title="FraudShield AI",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root { --fs-bg:#080f1c; --fs-panel:#101c2e; --fs-panel2:#14243a; --fs-line:#243750; --fs-cyan:#55d6ff; --fs-text:#eef5ff; --fs-muted:#9db0c8; }
.stApp { background: radial-gradient(ellipse at 75% 0%, #132b46 0%, #0a1423 42%, #080f1c 78%); font-family: Inter, sans-serif; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#081321 0%,#0b1727 100%); border-right:1px solid #20344d; }
[data-testid="stSidebar"] > div:first-child { padding-top:1.1rem; }
[data-testid="stSidebar"] * { color:#e9f2ff; }
.block-container { padding-top:5.2rem; padding-bottom:3rem; max-width:1450px; }
h1,h2,h3 { color:#f4f8ff !important; letter-spacing:-.035em; }
h1 { font-weight:800 !important; }
p, label, .stMarkdown { color:#d8e5f5; }
[data-testid="stMetric"] { background:linear-gradient(145deg,#14263d,#0f1c2e); border:1px solid #263d58; padding:18px 20px; border-radius:17px; box-shadow:0 10px 28px rgba(0,0,0,.13); min-height:125px; }
[data-testid="stMetricLabel"] { color:#9db4ce !important; font-size:.83rem !important; }
[data-testid="stMetricValue"] { color:#f7fbff !important; font-weight:750 !important; }
[data-testid="stMetricDelta"] { font-size:.78rem !important; }
div[data-testid="stAlert"] { border-radius:13px; border:1px solid #29415d; }
div.stButton > button, div.stDownloadButton > button { border-radius:10px; border:1px solid #2b779d; background:#12314b; color:#eaf8ff; font-weight:600; min-height:2.65rem; }
div.stButton > button:hover, div.stDownloadButton > button:hover { border-color:#61d7ff; color:white; background:#194263; }
div[data-testid="stFileUploader"] { background:#101e30; padding:14px; border-radius:14px; border:1px dashed #3c6b8c; }
[data-testid="stDataFrame"] { border:1px solid #253b54; border-radius:12px; overflow:hidden; }
[data-testid="stRadio"] label { padding:7px 9px; border-radius:9px; }
[data-testid="stRadio"] label:hover { background:#132943; }
hr { border-color:#253a53; }
/* FraudShield top navigation */
.fs-topbar { background:linear-gradient(110deg,rgba(14,30,49,.98),rgba(10,22,37,.98)); border:1px solid #263f5b; border-radius:18px; padding:12px 16px; margin:0 0 22px 0; }
.fs-brand-name { color:#f3f8ff; font-size:1.28rem; line-height:1.2; font-weight:850; letter-spacing:-.035em; }
.fs-brand-sub { color:#8ea9c6; font-size:.72rem; letter-spacing:.12em; font-weight:750; text-transform:uppercase; margin-top:4px; }
.fs-logo-mark { display:flex; align-items:center; justify-content:center; width:48px; height:48px; border-radius:15px; background:linear-gradient(145deg,#1a668a,#153652); border:1px solid #3c9ec4; color:#70e2ff; font-size:1.7rem; box-shadow:0 0 22px rgba(85,214,255,.13); }
.fs-top-status { display:inline-block; color:#75e5b4; border:1px solid #23694f; background:#10382f; border-radius:999px; padding:5px 9px; font-size:.68rem; font-weight:800; letter-spacing:.06em; }
.fs-eyebrow { color:#5ed7ff; font-size:.73rem; font-weight:800; letter-spacing:.16em; text-transform:uppercase; margin-bottom:.35rem; }
.fs-hero { background:linear-gradient(115deg,rgba(18,43,68,.98),rgba(13,27,45,.96)); border:1px solid #284968; border-radius:22px; padding:28px 30px; margin:0 0 22px 0; box-shadow:0 18px 45px rgba(0,0,0,.18); }
.fs-hero-title { font-size:2.1rem; line-height:1.15; font-weight:800; color:#f5f9ff; letter-spacing:-.05em; }
.fs-hero-copy { color:#a9bfd7; margin-top:9px; font-size:.98rem; }
.fs-pill { display:inline-block; padding:6px 10px; border-radius:999px; color:#74e2ff; background:#123751; border:1px solid #285b78; font-size:.75rem; font-weight:700; }
.fs-section-label { color:#8da8c5; text-transform:uppercase; letter-spacing:.13em; font-size:.74rem; font-weight:800; margin:1rem 0 .65rem; }
.fs-panel { background:linear-gradient(145deg,#111f32,#0e1a2a); border:1px solid #263a53; border-radius:17px; padding:18px 20px; }
.fs-panel-title { color:#eff6ff; font-size:1.05rem; font-weight:700; margin-bottom:5px; }
.fs-panel-copy { color:#91a8c2; font-size:.86rem; }
.fs-nav-note { color:#819bb8; font-size:.77rem; line-height:1.45; }
</style>
""", unsafe_allow_html=True)

# Compact brand bar and quick navigation across the top of the main dashboard.
# The image is optional: a built-in shield mark is shown if assets/logo.png is absent.
logo_path = BASE_DIR / "assets" / "logo.png"
brand_col, home_col, txn_col, network_col, cases_col = st.columns([3.3, 1.05, 1.25, 1.1, 1.0], vertical_alignment="center")
with brand_col:
    mark_col, name_col = st.columns([0.62, 4], vertical_alignment="center")
    with mark_col:
        if logo_path.exists():
            st.image(str(logo_path), width=48)
        else:
            st.markdown('<div class="fs-logo-mark">🛡</div>', unsafe_allow_html=True)
    with name_col:
        st.markdown('<div class="fs-brand-name">FraudShield AI</div><div class="fs-brand-sub">Financial fraud intelligence</div>', unsafe_allow_html=True)
with home_col:
    if st.button("⌂  Overview", key="topnav_home", use_container_width=True):
        st.session_state["fraudshield_navigation"] = "Home Dashboard"
        st.rerun()
with txn_col:
    if st.button("⇄  Transactions", key="topnav_transactions", use_container_width=True):
        st.session_state["fraudshield_navigation"] = "Transaction Investigation"
        st.rerun()
with network_col:
    if st.button("◎  Network", key="topnav_network", use_container_width=True):
        st.session_state["fraudshield_navigation"] = "Account Relationship Graph"
        st.rerun()
with cases_col:
    if st.button("▣  Cases", key="topnav_cases", use_container_width=True):
        st.session_state["fraudshield_navigation"] = "Case Management"
        st.rerun()
st.markdown('<div class="fs-top-status">● SECURE WORKSPACE</div>', unsafe_allow_html=True)

with st.sidebar:
    logo_path = BASE_DIR / "assets" / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=135)
    else:
        st.markdown("# 🛡️ FraudShield AI")
    st.markdown('<div class="fs-eyebrow">Financial Intelligence Platform</div>', unsafe_allow_html=True)
    st.markdown("**Detect** · **Analyze** · **Investigate**")
    st.markdown('<div class="fs-nav-note">Risk indicators for investigator review. Not proof of fraud.</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown("### Data workspace")
    uploaded_file = st.file_uploader(
        "Upload transaction data or statement",
        type=["csv", "pdf", "png", "jpg", "jpeg", "docx"],
        key="transaction_file_upload",
        help="Supported: CSV, text/table-based PDF, JPG/PNG image, and DOCX. Scanned PDFs/images need Tesseract OCR installed.",
    )
    if uploaded_file is None:
        st.caption("Demo dataset is active until you upload a file.")
    else:
        st.caption(f"Selected file: {uploaded_file.name}")
    st.divider()
    st.markdown("### Workspace")
    page = st.radio(
        "GO TO",
        ["Home Dashboard", "Transaction Investigation", "Account Investigation", "Account Relationship Graph", "Money-Flow Tracing", "Alerts", "Case Management"],
        key="fraudshield_navigation",
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown('<div class="fs-nav-note">FRAUDSHIELD AI · HACKATHON PROTOTYPE<br>Rules-based risk scoring · Review before action</div>', unsafe_allow_html=True)


def _clean_column_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _normalize_table_columns(raw):
    """Common transaction-table column names ko FraudShield AI schema mein map kare."""
    if raw is None or raw.empty:
        raise ValueError("Uploaded file mein readable transaction table nahi mili.")

    raw = raw.copy()
    raw.columns = [str(c).strip().replace('"', "") for c in raw.columns]
    aliases = {
        "transaction_id": ["transactionid", "txn id", "txn id.", "id", "utr", "reference", "referenceno", "refno"],
        "timestamp": ["timestamp", "datetime", "date time", "transactiondatetime", "date", "transactiondate"],
        "time": ["time", "transactiontime"],
        "from_account": ["fromaccount", "sender", "senderaccount", "payer", "paidby", "debitaccount"],
        "to_account": ["toaccount", "receiver", "receiveraccount", "payee", "beneficiary", "creditedto"],
        "amount": ["amount", "transactionamount", "txnamount", "value", "debit", "credit"],
        "transaction_type": ["transactiontype", "type", "drcr", "direction", "debitcredit"],
        "transaction_details": ["transactiondetails", "details", "description", "narration", "remarks", "particulars"],
    }
    normalized_lookup = {_clean_column_name(c): c for c in raw.columns}
    mapped = {}
    for target, names in aliases.items():
        for alias in names:
            key = _clean_column_name(alias)
            if key in normalized_lookup:
                mapped[target] = normalized_lookup[key]
                break

    if "amount" not in mapped:
        raise ValueError(
            "Transaction table mein Amount column identify nahi hua. "
            f"Available columns: {', '.join(map(str, raw.columns))}"
        )

    out = pd.DataFrame(index=raw.index)
    out["amount"] = pd.to_numeric(
        raw[mapped["amount"]].astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("INR", "", regex=False)
        .str.strip(),
        errors="coerce",
    )

    if "timestamp" in mapped:
        out["timestamp"] = pd.to_datetime(raw[mapped["timestamp"]], errors="coerce")
    else:
        out["timestamp"] = pd.NaT

    if "time" in mapped and "timestamp" in mapped and _clean_column_name(mapped["timestamp"]) in {"date", "transactiondate"}:
        out["timestamp"] = pd.to_datetime(
            raw[mapped["timestamp"]].astype(str) + " " + raw[mapped["time"]].astype(str),
            errors="coerce",
        )

    if "transaction_id" in mapped:
        out["transaction_id"] = raw[mapped["transaction_id"]].fillna("").astype(str).str.strip()
    else:
        out["transaction_id"] = [f"UPLOADED-{i+1}" for i in range(len(raw))]

    if "transaction_details" in mapped:
        details = raw[mapped["transaction_details"]].fillna("").astype(str).str.strip()
    else:
        details = pd.Series([""] * len(raw), index=raw.index)

    kind = raw[mapped["transaction_type"]].astype(str).str.upper().str.strip() if "transaction_type" in mapped else pd.Series([""] * len(raw), index=raw.index)
    if "from_account" in mapped and "to_account" in mapped:
        out["from_account"] = raw[mapped["from_account"]].fillna("Unknown sender").astype(str).str.strip()
        out["to_account"] = raw[mapped["to_account"]].fillna("Unknown receiver").astype(str).str.strip()
    else:
        # If only statement narration exists, derive a readable counterparty label,
        # but clearly mark it as unverified rather than pretending it is a bank ID.
        out["from_account"] = "UPLOADED_STATEMENT_ACCOUNT"
        out["to_account"] = "COUNTERPARTY: " + details.replace("", "Unknown counterparty")
        credit_mask = kind.str.contains(r"CREDIT|CR|RECEIVED|INCOMING", regex=True)
        debit_mask = kind.str.contains(r"DEBIT|DR|PAID|OUTGOING", regex=True)
        out.loc[credit_mask, "from_account"] = "COUNTERPARTY: " + details[credit_mask].replace("", "Unknown counterparty")
        out.loc[credit_mask, "to_account"] = "UPLOADED_STATEMENT_ACCOUNT"
        # Do not infer direction when the statement does not provide a recognizable type.
        unknown_mask = ~(credit_mask | debit_mask)
        out.loc[unknown_mask, "from_account"] = "Unknown direction"
        out.loc[unknown_mask, "to_account"] = "Unknown direction"

    out["transaction_type"] = kind.replace("", "UNKNOWN")
    out["transaction_details"] = details
    out["utr"] = ""
    out["account_mapping_note"] = "Account labels were read from the uploaded file and may not be verified bank account IDs."
    out = out.dropna(subset=["amount"]).copy()
    out = out[out["amount"] >= 0].copy()
    if out.empty:
        raise ValueError("File se valid numeric transaction amounts extract nahi hue.")
    if (out["from_account"] == "Unknown direction").all():
        raise ValueError("Transaction direction identify nahi hui. Table mein sender/receiver ya debit/credit/type column add karein.")
    return out.reset_index(drop=True)


def normalize_phonepe_statement(file_obj):
    """PhonePe CSV statement ko FraudShield AI ke common transaction schema mein badle."""
    file_obj.seek(0)
    raw = pd.read_csv(file_obj, skiprows=3, encoding="utf-8-sig")
    raw.columns = [str(c).strip().replace('"', "") for c in raw.columns]
    required_cols = {"Date", "Time", "Transaction Details", "Transaction ID", "Transaction Type", "Amount"}
    if not required_cols.issubset(set(raw.columns)):
        # A normal CSV may use a standard table rather than PhonePe's 3 metadata lines.
        file_obj.seek(0)
        generic = pd.read_csv(file_obj, encoding="utf-8-sig")
        return _normalize_table_columns(generic)

    raw["Amount"] = pd.to_numeric(
        raw["Amount"].astype(str).str.replace(",", "", regex=False).str.replace("₹", "", regex=False).str.strip(),
        errors="coerce",
    )
    raw = raw.dropna(subset=["Amount", "Transaction ID"]).copy()
    raw["Transaction Type"] = raw["Transaction Type"].astype(str).str.upper().str.strip()
    raw["Transaction Details"] = raw["Transaction Details"].fillna("Unknown counterparty").astype(str).str.strip()

    def counterparty_label(details):
        text = str(details).strip()
        for prefix in ("Paid to ", "Received from ", "Transfer to ", "Transfer from ", "Payment to ", "Payment from "):
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
                break
        return text or "Unknown counterparty"

    rows = []
    own_account = "MY_PHONEPE_ACCOUNT"
    for _, row in raw.iterrows():
        kind = row["Transaction Type"]
        details = counterparty_label(row["Transaction Details"])
        counterparty = "COUNTERPARTY: " + details
        if kind == "DEBIT":
            sender, receiver = own_account, counterparty
        elif kind == "CREDIT":
            sender, receiver = counterparty, own_account
        else:
            continue
        date_time = pd.to_datetime(f"{row['Date']} {row['Time']}", errors="coerce")
        rows.append({
            "transaction_id": str(row["Transaction ID"]).strip(),
            "timestamp": date_time.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(date_time) else "Unknown",
            "from_account": sender,
            "to_account": receiver,
            "amount": float(row["Amount"]),
            "transaction_type": kind,
            "transaction_details": row["Transaction Details"],
            "utr": str(row.get("UTR", "")),
            "account_mapping_note": "Counterparty label from statement text; not a verified bank account ID",
        })
    if not rows:
        raise ValueError("No valid debit/credit transactions were found in the account.")
    return pd.DataFrame(rows)


def extract_pdf_table(file_bytes):
    """Reads text/table content from PDFs; OCR is required separately for scanned PDFs."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise ValueError("For PDF support, install `pdfplumber`: pip install pdfplumber") from exc

    tables = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            for table in (page.extract_tables() or []):
                if table and len(table) >= 2:
                    header = [str(v or "").strip() for v in table[0]]
                    rows = table[1:]
                    if any(header):
                        tables.append(pd.DataFrame(rows, columns=header))
    if not tables:
        raise ValueError("No readable table was found in the PDF. If it is a scanned PDF," 
        " please install OCR software, or upload the table in CSV/DOCX format.")
    # Use the first detected table; mixed tables need user review.
    return _normalize_table_columns(tables[0])


def extract_docx_table(file_bytes):
    """Extract the first readable translation table from the DOCX file."""
    try:
        from docx import Document
    except ImportError as exc:
        raise ValueError("Install `python-docx` for Word support.") from exc

    document = Document(BytesIO(file_bytes))
    for table in document.tables:
        rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
        if len(rows) >= 2 and any(any(cell for cell in row) for row in rows[1:]):
            frame = pd.DataFrame(rows[1:], columns=rows[0])
            try:
                return _normalize_table_columns(frame)
            except ValueError:
                continue
    raise ValueError("The readable transaction table was not found in the Word file." \
    " Please use a table that includes a header row and transaction rows.")


def extract_image_table(file_bytes):
    """Run OCR on photos/screenshots; the Tesseract binary must be installed separately."""
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        raise ValueError("Install Pillow and Tesseract for image OCR: pip install Pillow Tesseract") from exc

    try:
        image_obj = Image.open(BytesIO(file_bytes)).convert("RGB")
        extracted_text = pytesseract.image_to_string(image_obj)
    except Exception as exc:
        raise ValueError(
            "Image OCR fail hua. Tesseract OCR engine install karke PATH mein add karein; "
            "sirf Python package install karna enough nahi hai."
        ) from exc

    # OCR text can vary by statement layout. Only proceed when each line can be
    # interpreted conservatively; do not invent missing sender/receiver direction.
    st.text_area("OCR extracted text (review before relying on it)", extracted_text, height=180)
    rows = []
    for line in extracted_text.splitlines():
        line = line.strip()
        if not line:
            continue
        amount_match = re.search(r"(?:₹|INR\s*)?([\d,]+(?:\.\d{1,2})?)\s*$", line, flags=re.IGNORECASE)
        date_match = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", line)
        direction_match = re.search(r"\b(DEBIT|CREDIT|DR|CR|PAID|RECEIVED)\b", line, flags=re.IGNORECASE)
        if not amount_match or not direction_match:
            continue
        amount = pd.to_numeric(amount_match.group(1).replace(",", ""), errors="coerce")
        if pd.isna(amount):
            continue
        direction = direction_match.group(1).upper()
        is_credit = direction in {"CREDIT", "CR", "RECEIVED"}
        is_debit = direction in {"DEBIT", "DR", "PAID"}
        if not (is_credit or is_debit):
            continue
        description = line[:amount_match.start()].strip()
        description = re.sub(r"\b(DEBIT|CREDIT|DR|CR|PAID|RECEIVED)\b", "", description, flags=re.IGNORECASE).strip(" -|:")
        counterparty = "COUNTERPARTY: " + (description or "OCR extracted label")
        rows.append({
            "transaction_id": f"OCR-{len(rows)+1}",
            "timestamp": pd.to_datetime(date_match.group(1), dayfirst=True, errors="coerce") if date_match else pd.NaT,
            "from_account": counterparty if is_credit else "UPLOADED_STATEMENT_ACCOUNT",
            "to_account": "UPLOADED_STATEMENT_ACCOUNT" if is_credit else counterparty,
            "amount": float(amount),
            "transaction_type": "CREDIT" if is_credit else "DEBIT",
            "transaction_details": line,
            "utr": "",
            "account_mapping_note": "OCR-derived counterparty label; verify manually; not a verified bank account ID",
        })
    if not rows:
        raise ValueError(
            "Photo se transaction rows confidently parse nahi hue. Image clear rakhein aur "
            "date, DEBIT/CREDIT (ya DR/CR/PAID/RECEIVED), aur amount clearly visible ho. "
            "For best results, PDF/CSV/DOCX table use karein."
        )
    return pd.DataFrame(rows)


def load_uploaded_transactions(file_obj):
    """CSV, PDF, DOCX aur image ko common transaction schema mein convert kare."""
    name = file_obj.name.lower()
    file_obj.seek(0)
    if name.endswith(".csv"):
        return normalize_phonepe_statement(file_obj), "Uploaded CSV"
    file_bytes = file_obj.getvalue()
    if name.endswith(".pdf"):
        return extract_pdf_table(file_bytes), "Uploaded PDF"
    if name.endswith(".docx"):
        return extract_docx_table(file_bytes), "Uploaded Word document"
    if name.endswith((".png", ".jpg", ".jpeg")):
        return extract_image_table(file_bytes), "Uploaded image (OCR)"
    raise ValueError("Unsupported file type.")


try:
    if uploaded_file is not None:
        raw_transactions, data_source_label = load_uploaded_transactions(uploaded_file)
        df = analyze_transactions_data(raw_transactions)
        st.success(f"{data_source_label} loaded: {len(df)} transactions analyzed.")
        st.caption("Extracted account/counterparty labels may not be verified bank-account IDs. Uploaded records must be reviewed.")
        with st.expander("Preview normalized transactions"):
            preview_cols = [c for c in ["timestamp", "transaction_id", "transaction_type", "transaction_details", "from_account", "to_account", "amount"] if c in df.columns]
            st.dataframe(df[preview_cols].head(30), use_container_width=True, hide_index=True)
    else:
        df = analyze_transactions(DATA_FILE)
        data_source_label = "Demo transactions.csv"
        st.info("Demo data active hai. CSV, PDF, JPG/PNG image, ya DOCX transaction table upload kar sakte hain.")
    accounts = analyze_account_network(df)
except (OSError, ValueError, KeyError, pd.errors.ParserError, TypeError) as error:
    st.error(f"Analysis failed: {error}")
    st.stop()
    

try:
    alerts = generate_investigation_alerts(df, accounts)
except (ValueError, KeyError, TypeError) as error:
    alerts = pd.DataFrame()
    st.warning(f"Alert generation failed: {error}")

if page == "Home Dashboard":
    st.markdown('<div class="fs-hero"><div class="fs-eyebrow">Investigation command center</div><div class="fs-hero-title">See the signals.<br>Follow the money.</div><div class="fs-hero-copy">A single workspace for transaction risk, account relationships, money-flow trails and investigation cases.</div><br><span class="fs-pill">● WORKSPACE READY</span></div>', unsafe_allow_html=True)

    total_transactions = len(df)
    high_risk_count = int((df["risk_level"] == "High").sum()) if "risk_level" in df.columns else 0
    medium_risk_count = int((df["risk_level"] == "Medium").sum()) if "risk_level" in df.columns else 0
    total_accounts = len(accounts) if accounts is not None else 0
    total_value = float(pd.to_numeric(df["amount"], errors="coerce").fillna(0).sum())

    st.markdown('<div class="fs-section-label">Risk overview</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Transactions reviewed", f"{total_transactions:,}")
    k2.metric("High-risk transactions", f"{high_risk_count:,}")
    k3.metric("Accounts in network", f"{total_accounts:,}")
    k4.metric("Transaction value", f"₹{total_value:,.0f}")
    st.caption(f"Active dataset: {data_source_label} · Risk scores are heuristic indicators, not fraud probabilities.")

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown('<div class="fs-section-label">Transaction risk distribution</div>', unsafe_allow_html=True)
        risk_counts = df["risk_level"].value_counts().reindex(["High", "Medium", "Low"], fill_value=0)
        risk_fig = go.Figure(data=[go.Pie(labels=risk_counts.index, values=risk_counts.values, hole=.72, sort=False,
            marker=dict(colors=["#ff657a", "#ffc45c", "#4bd6a0"], line=dict(color="#0b1727", width=3)),
            textinfo="label+value", textfont=dict(color="#edf5ff", size=12), hovertemplate="%{label}: %{value}<extra></extra>")])
        risk_fig.update_layout(height=320, margin=dict(l=5,r=5,t=10,b=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, annotations=[dict(text=f"{total_transactions}<br><span style='font-size:11px'>transactions</span>", x=.5, y=.5, showarrow=False, font=dict(size=22,color="#f4f8ff"))])
        st.plotly_chart(risk_fig, use_container_width=True, config={"displayModeBar": False})
    with right:
        st.markdown('<div class="fs-section-label">Investigation snapshot</div>', unsafe_allow_html=True)
        alert_total = len(alerts) if alerts is not None else 0
        high_alerts = int((alerts["priority"] == "High").sum()) if alerts is not None and not alerts.empty and "priority" in alerts.columns else 0
        st.markdown(f'<div class="fs-panel"><div class="fs-panel-title">Automated alerts</div><div class="fs-panel-copy">Rule-based indicators requiring investigator review.</div><h2 style="margin:.65rem 0 0 0">{alert_total}</h2><div class="fs-panel-copy">{high_alerts} high-priority alert(s)</div></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown(f'<div class="fs-panel"><div class="fs-panel-title">Network coverage</div><div class="fs-panel-copy">Unique accounts represented in the active dataset.</div><h2 style="margin:.65rem 0 0 0">{total_accounts}</h2><div class="fs-panel-copy">Connected through observed transaction records</div></div>', unsafe_allow_html=True)
        st.write("")
        st.markdown(f'<div class="fs-panel"><div class="fs-panel-title">Medium-risk transactions</div><div class="fs-panel-copy">Review queue for additional context.</div><h2 style="margin:.65rem 0 0 0">{medium_risk_count}</h2></div>', unsafe_allow_html=True)

    st.markdown('<div class="fs-section-label">Latest transaction records</div>', unsafe_allow_html=True)
    recent_cols = [c for c in ["timestamp", "transaction_id", "from_account", "to_account", "amount", "risk_level", "risk_score"] if c in df.columns]
    recent = df[recent_cols].copy()
    if "timestamp" in recent.columns:
        recent = recent.sort_values("timestamp", ascending=False, na_position="last")
    st.dataframe(recent.head(8), use_container_width=True, hide_index=True)

    st.markdown('<div class="fs-section-label">Investigation tools</div>', unsafe_allow_html=True)
    tool_cards = st.columns(3)
    cards = [
        ("Transaction investigation", "Filter, inspect and export transaction records."),
        ("Account relationship graph", "Explore links between sender and receiver accounts."),
        ("Case management", "Track investigator assignments, deadlines and evidence."),
    ]
    for col, (title, copy) in zip(tool_cards, cards):
        with col:
            st.markdown(f'<div class="fs-panel"><div class="fs-panel-title">{title}</div><div class="fs-panel-copy">{copy}</div></div>', unsafe_allow_html=True)

    st.warning("Prototype note: risk indicators are generated by configured heuristics. They are not proof of fraud; verify source records and supporting evidence before taking action.")


if page == 'Transaction Investigation':
    # Transaction investigation.
    st.header("1. Transaction Investigation")
    if uploaded_file is not None:
        st.write("Uploaded statement preview (normalized for analysis):")
        preview_cols = [c for c in ["timestamp", "transaction_id", "transaction_type", "transaction_details", "from_account", "to_account", "amount"] if c in df.columns]
        st.dataframe(df[preview_cols].head(10), use_container_width=True, hide_index=True)



    risk_filter = st.selectbox(
        "Filter transactions by risk",
        ["All", "High", "Medium", "Low"],
    )

    filtered = df.copy()


    if risk_filter != "All":
        filtered = filtered[filtered["risk_level"] == risk_filter]

    st.dataframe(filtered, use_container_width=True, hide_index=True)

    st.download_button(
        "Download Transaction Report",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="FraudShield_AI_transactions.csv",
        mime="text/csv",
    )

    st.divider()


if page == 'Account Investigation':
    # Account-level investigation.
    st.header("2. Account Investigation")

    if not accounts.empty:
        st.dataframe(
            accounts,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download Account Investigation",
            data=accounts.to_csv(index=False).encode("utf-8"),
            file_name="FraudShield_AI_accounts.csv",
            mime="text/csv",
        )

        selected_account = st.selectbox(
            "Investigate an account",
            accounts["account"].tolist(),
        )

        account_info = accounts[
            accounts["account"] == selected_account
        ].iloc[0]

        st.subheader(f"Account: {selected_account}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Transactions Sent", int(account_info["transactions_sent"]))
        c2.metric("Transactions Received", int(account_info["transactions_received"]))
        c3.metric(
            "Highest Linked Risk",
            f'{account_info["max_linked_transaction_risk"]:.0f}/100',
        )

        st.write("Investigation indicators:")
        st.info(account_info["investigation_indicators"])

        related = df[
            (df["from_account"] == selected_account)
            | (df["to_account"] == selected_account)
        ]

        st.write("Related transactions")
        st.dataframe(related, use_container_width=True, hide_index=True)

    st.divider()



if page == 'Account Relationship Graph':
    # Interactive transaction network with suspicious transaction highlighting.
    st.header("3. Account Relationship Graph")

    st.subheader("Network Investigation Filters")

    high_risk_only = st.checkbox(
        "Show only high-risk transaction connections",
        value=False,
        key="high_risk_network_filter",
    )


    accounts_list = sorted(
        set(df["from_account"].astype(str))
        | set(df["to_account"].astype(str))
    )

    selected_account = st.selectbox(
        "Select account to investigate",
        ["None"] + accounts_list,
        key="selected_account_filter",
    )


    # Selected account ka financial activity summary
    if selected_account != "None":
        account_transactions = df[
            (df["from_account"] == selected_account)
            | (df["to_account"] == selected_account)
        ]

        outgoing = df[df["from_account"] == selected_account]
        incoming = df[df["to_account"] == selected_account]

        total_outgoing = float(outgoing["amount"].sum())
        total_incoming = float(incoming["amount"].sum())

        highest_risk = (
            int(account_transactions["risk_score"].max())
            if not account_transactions.empty
            else 0
        )

        st.subheader(f"Investigation Summary: {selected_account}")

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Transactions Sent", len(outgoing))
        s2.metric("Transactions Received", len(incoming))
        s3.metric("Total Outgoing", f"₹{total_outgoing:,.0f}")
        s4.metric("Total Incoming", f"₹{total_incoming:,.0f}")

        st.metric("Highest Linked Transaction Risk", f"{highest_risk}/100")


    # graph = nx.DiGraph()

    # for _, row in df.iterrows():
    #     if high_risk_only and row["risk_score"] < 50:
    #         continue

    #     graph.add_edge(
    #         row["from_account"],
    #         row["to_account"],
    #     )

    # st.caption(
    #     "Red edges indicate linked transactions with risk scores >= 50. "
    #     "Node color represents the highest linked transaction risk score, "
    #     "not a confirmed account fraud probability."
    # )

    graph = nx.DiGraph()


    for _, row in df.iterrows():
        if high_risk_only and row["risk_score"] < 50:
            continue

        graph.add_edge(
            row["from_account"],
            row["to_account"],
        )



    # Graph investigation controls
    st.subheader("Network Investigation Filters")

    high_risk_transactions = df[df["risk_score"] >= 50]
    high_risk_accounts = set(
        high_risk_transactions["from_account"].tolist()
        + high_risk_transactions["to_account"].tolist()
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Accounts in Network", graph.number_of_nodes())
    m2.metric("High-Risk Transactions", len(high_risk_transactions))
    m3.metric("Accounts Linked to High-Risk Transactions", len(high_risk_accounts))

    # high_risk_only = st.checkbox(
    #     "Show only high-risk transaction connections",
    #     value=False,
    # )


    if graph.number_of_nodes() > 0:
        positions = nx.spring_layout(graph, seed=42)

        # Har source-target pair ke liye edge draw karo.
        edge_traces = []
        for source, target in graph.edges():
            x0, y0 = positions[source]
            x1, y1 = positions[target]
            linked = df[
                (df["from_account"] == source)
                & (df["to_account"] == target)
            ]
            if high_risk_only:
                linked = linked[linked["risk_score"] >= 50]
            if linked.empty:
                continue
            highest_edge_risk = int(linked["risk_score"].max())
            total_amount = float(linked["amount"].sum())
            is_suspicious = highest_edge_risk >= 50
            edge_traces.append(
                go.Scatter(
                    x=[x0, x1], y=[y0, y1], mode="lines",
                    line=dict(color="#dc2626" if is_suspicious else "#64748b",
                              width=3 if is_suspicious else 1),
                    text=(f"{source} → {target}<br>"
                          f"Transaction count: {len(linked)}<br>"
                          f"Total amount: ₹{total_amount:,.2f}<br>"
                          f"Highest linked risk: {highest_edge_risk}/100"),
                    hoverinfo="text", showlegend=False,
                )
            )

        # Prepare account nodes.
        node_x, node_y, labels, node_colors, hover = [], [], [], [], []
        node_sizes = []
        node_border_colors = [] 
        for node in graph.nodes():
            x, y = positions[node]
            node_x.append(x)
            node_y.append(y)
            labels.append(node)

            related = df[
                (df["from_account"] == node)
                | (df["to_account"] == node)
            ]

            highest_risk = int(related["risk_score"].max())
            node_colors.append(highest_risk)

        
            is_selected = node == selected_account

       
            #is_selected = node == selected_account

            is_neighbor = False

            if selected_account != "None" and not is_selected:
                is_neighbor = (
                    (
                        (df["from_account"] == selected_account)
                        & (df["to_account"] == node)
                    ).any()
                    or
                    (
                        (df["to_account"] == selected_account)
                        & (df["from_account"] == node)
                    ).any()
                )

            node_sizes.append(
                28 if is_selected else 22 if is_neighbor else 18
            )

            node_border_colors.append(
                "#00FFFF" if is_selected
                else "#FFA500" if is_neighbor
                else "#FFFFFF"
            )



            sent = int((df["from_account"] == node).sum())
            received = int((df["to_account"] == node).sum())

            hover.append(
                f"Account: {node}<br>"
                f"Sent transactions: {sent}<br>"
                f"Received transactions: {received}<br>"
                f"Highest linked risk: {highest_risk}/100"
            )

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=labels,
            textposition="top center",
            hovertext=hover,
            hoverinfo="text",
            marker=dict(
                size=node_sizes,
                color=node_colors,
                colorscale="RdYlGn_r",
                cmin=0,
                cmax=100,
                showscale=True,
                colorbar=dict(title="Risk score"),
              line=dict(
        width=3,
        color=node_border_colors,
    ),
            ),
            showlegend=True,
        )

        fig = go.Figure(data=edge_traces + [node_trace])

    
        # Legend for transaction connection risk
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                line=dict(color="#dc2626", width=3),
                name="High risk (score ≥ 50)",
                hoverinfo="skip",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                line=dict(color="#64748b", width=1),
                name="Lower risk (score < 50)",
                hoverinfo="skip",
            )
        )


        fig.update_layout(
            height=600,
            showlegend=False,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No transaction relationships available to display.")

    st.warning(
        "Demo prototype using fictional transactions and heuristic rules. "
        "Risk indicators are not proof of fraud. Review supporting evidence "
        "before making any real-world decision."
    )


    st.divider()

if page == 'Money-Flow Tracing':
    st.header("4. Money-Flow Tracing")

    st.caption(
        "Accounts ke beech possible transaction routes trace karo. "
        "Connectivity actual paise ki provenance prove nahi karti."
    )

    account_options = sorted(
        set(df["from_account"].dropna())
        | set(df["to_account"].dropna())
    )

    if len(account_options) >= 2:
        col_source, col_destination = st.columns(2)

        with col_source:
            source_account = st.selectbox(
                "Source account",
                account_options,
                index=0,
            )

        with col_destination:
            destination_index = (
                1 if account_options[0] == source_account else 0
            )

            destination_account = st.selectbox(
                "Destination account",
                account_options,
                index=destination_index,
            )

        max_hops = st.slider(
            "Maximum transfer steps",
            min_value=1,
            max_value=5,
            value=3,
        )

        if st.button("Trace Money Flow"):
            if source_account == destination_account:
                st.error("Source aur destination alag select karo.")
            else:
                try:
                    paths, message = trace_money_flow(
                        df,
                        source_account,
                        destination_account,
                        max_hops=max_hops,
                    )

                    st.info(message)

                    if paths:
                        path_df = pd.DataFrame(paths)
                        st.dataframe(
                            path_df,
                            use_container_width=True,
                            hide_index=True,
                        )

                        st.download_button(
                            "Download Money-Flow Report",
                            data=path_df.to_csv(index=False).encode("utf-8"),
                            file_name="FraudShield_AI_money_flow.csv",
                            mime="text/csv",
                        )

                except (ValueError, KeyError, nx.NetworkXException) as error:
                    st.error(f"Tracing failed: {error}")



if page == 'Alerts':
    # Automated investigation alerts
    st.divider()
    st.header("5. Automated Investigation Alerts")

    st.caption(
        "Rule-based alerts for investigator review. "
        "An alert is not proof of fraud."
    )

    try:
        if alerts.empty:
            st.success(
                "Configured alert thresholds ke hisaab se "
                "koi investigation alert generate nahi hua."
            )
        else:
            high_count = int((alerts["priority"] == "High").sum())
            medium_count = int((alerts["priority"] == "Medium").sum())

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Alerts", len(alerts))
            c2.metric("High Priority", high_count)
            c3.metric("Medium Priority", medium_count)

        
            priority_filter = st.selectbox(
                "Filter alerts by priority",
                ["All", "High", "Medium"],
                key="alert_priority_filter",
            )

            alert_search = st.text_input(
                "Search alerts",
                placeholder="Search transaction ID, account, or reason...",
                key="alert_search",
            )

            visible_alerts = alerts.copy()

            if priority_filter != "All":
                visible_alerts = visible_alerts[
                    visible_alerts["priority"] == priority_filter
                ]

            if alert_search.strip():
                search_text = alert_search.strip()
                searchable_columns = [
                    "alert_id",
                    "alert_type",
                    "priority",
                    "related_accounts",
                    "transaction_ids",
                    "reason",
                ]

                mask = visible_alerts[searchable_columns].fillna("").astype(str).apply(
                    lambda column: column.str.contains(
                        search_text,
                        case=False,
                        regex=False,
                    )
                ).any(axis=1)

                visible_alerts = visible_alerts[mask]

            st.caption(f"Showing {len(visible_alerts)} of {len(alerts)} alerts")

            st.dataframe(
                visible_alerts,
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
        "Download Investigation Alerts",
        data=visible_alerts.to_csv(index=False).encode("utf-8"),
        file_name="FraudShield_AI_alerts.csv",
        mime="text/csv",
        key="download_investigation_alerts",
    )


    #         st.download_button(
    #     "Download Investigation Alerts",
    #     data=visible_alerts.to_csv(index=False).encode("utf-8"),
    #     file_name="FraudShield_AI_alerts.csv",
    #     mime="text/csv",
    #     key="download_investigation_alerts",
    # )

    except (ValueError, KeyError, TypeError) as error:
        st.error(f"Alert generation failed: {error}")





if page == 'Case Management':
    # Case Management
    st.divider()
    st.header("6. Investigation Case Management")

    st.caption(
        "Assign investigators, set review deadlines, and record evidence."
    )

    try:
        sync_alerts(alerts)
        cases = load_cases()

        if cases.empty:
            st.info("Abhi koi investigation case available nahi hai.")

        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Open Cases", int((cases["status"] == "Open").sum()))
            c2.metric(
                "Under Review",
                int((cases["status"] == "Under Review").sum()),
            )
            c3.metric(
                "Resolved Cases",
                int((cases["status"] == "Resolved").sum()),
            )


            # Investigator Performance Dashboard
            st.subheader("Investigator Performance Dashboard")

            performance = cases.copy()

            # Missing investigator names ko default member assign karo
            performance["assigned_investigator"] = (
                performance["assigned_investigator"]
                .fillna("Unassigned")
            )

            # Har investigator ke cases ka summary
            summary = []

            for member in TEAM_MEMBERS:
                member_cases = performance[
                    performance["assigned_investigator"] == member
                ]

                assigned = len(member_cases)
                pending = int(
                    member_cases["status"].isin(
                        ["Open", "Under Review"]
                    ).sum()
                )
                resolved = int(
                    (member_cases["status"] == "Resolved").sum()
                )

                summary.append({
                    "Investigator": member,
                    "Assigned Cases": assigned,
                    "Pending Cases": pending,
                    "Resolved Cases": resolved,
                })

            summary_df = pd.DataFrame(summary)

        
            # Investigator-wise Filter
            investigator_filter = st.selectbox(
                "Filter by Investigator",
                ["All Investigators"] + TEAM_MEMBERS,
            )

            if investigator_filter != "All Investigators":
                summary_df = summary_df[
                    summary_df["Investigator"] == investigator_filter
                ].copy()


            # Dashboard metrics
            total_assigned = int(summary_df["Assigned Cases"].sum())
            total_pending = int(summary_df["Pending Cases"].sum())
            total_resolved = int(summary_df["Resolved Cases"].sum())

            p1, p2, p3 = st.columns(3)
            p1.metric("Assigned Cases", total_assigned)
            p2.metric("Pending Cases", total_pending)
            p3.metric("Resolved Cases", total_resolved)

            # Team-wise performance table
            st.dataframe(
                summary_df,
                use_container_width=True,
                hide_index=True,
            )

            # Comparison chart
            chart_data = summary_df.set_index("Investigator")[
                ["Assigned Cases", "Pending Cases", "Resolved Cases"]
            ]

            st.bar_chart(chart_data)

            # Overdue Review Alerts
            st.subheader("Overdue Review Alerts")

            today = pd.Timestamp.now().date()

            overdue_cases = cases[
                cases["review_deadline"].notna()
                & (cases["review_deadline"].astype(str).str.strip() != "")
                & (cases["review_deadline"].astype(str) < str(today))
                & cases["status"].isin(["Open", "Under Review"])
            ].copy()

            if overdue_cases.empty:
                st.success("No overdue investigation cases.")
            else:
                st.warning(
                    f"{len(overdue_cases)} investigation case(s) "
                    "have passed their review deadline."
                )

                st.dataframe(
                    overdue_cases[
                        [
                            "case_id",
                            "priority",
                            "status",
                            "assigned_investigator",
                            "review_deadline",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )


            st.subheader("Case Register")

            status_filter = st.selectbox(
                "Filter cases by status",
                ["All", "Open", "Under Review", "Resolved"],
            )

            visible = cases.copy()

            if status_filter != "All":
                visible = visible[visible["status"] == status_filter]

            st.dataframe(
                visible[
                    [
                        "case_id",
                        "priority",
                        "risk_score",
                        "status",
                        "assigned_investigator",
                        "review_deadline",
                        "updated_at",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            selected_case = st.selectbox(
                "Select a case to update",
                cases["case_id"].tolist(),
            )

            case_row = cases[cases["case_id"] == selected_case].iloc[0]

        
            st.subheader("Export Investigation Evidence")

            pdf_data = create_evidence_report(case_row)

            safe_case_id = "".join(
                ch if ch.isalnum() or ch in "-_" else "_"
                for ch in str(selected_case)
            )

            st.download_button(
                "Download Evidence Report (PDF)",
                data=pdf_data,
                file_name=f"FraudShield_AI_Evidence_{safe_case_id}.pdf",
                mime="application/pdf",
                key="download_case_evidence_pdf",
            )


            st.write(f"**Alert reason:** {case_row['reason']}")
            st.write(f"**Related accounts:** {case_row['related_accounts']}")
            st.write(f"**Related transactions:** {case_row['transaction_ids']}")

            st.subheader("Update Investigation Case")

            current_investigator = case_row["assigned_investigator"]
            if current_investigator not in TEAM_MEMBERS:
                current_investigator = TEAM_MEMBERS[0]

            with st.form("update_case_form"):
                new_status = st.selectbox(
                    "Case status",
                    ["Open", "Under Review", "Resolved"],
                    index=[
                        "Open",
                        "Under Review",
                        "Resolved",
                    ].index(case_row["status"]),
                )

                investigator = st.selectbox(
                    "Assigned investigator",
                    TEAM_MEMBERS,
                    index=TEAM_MEMBERS.index(current_investigator),
                )

                deadline_value = case_row["review_deadline"]
                try:
                    import datetime

                    default_deadline = (
                        datetime.date.fromisoformat(deadline_value)
                        if deadline_value
                        else datetime.date.today()
                    )
                except (ValueError, TypeError):
                    default_deadline = datetime.date.today()

                deadline = st.date_input(
                    "Review deadline",
                    value=default_deadline,
                )

                notes = st.text_area(
                    "Investigation notes",
                    value=case_row["investigator_notes"] or "",
                    placeholder="Record review steps and next actions...",
                )

                evidence = st.text_area(
                    "Evidence summary",
                    value=case_row["evidence_summary"] or "",
                    placeholder=(
                        "Record supporting transaction IDs, observed patterns, "
                        "verification findings, and pending checks..."
                    ),
                )

                submitted = st.form_submit_button("Save Case Update")

                if submitted:
                    try:
                        update_case(
                            selected_case,
                            new_status,
                            notes,
                            assigned_investigator=investigator,
                            review_deadline=deadline,
                            evidence_summary=evidence,
                        )
                        st.success("Case update saved successfully.")
                        st.rerun()

                    except (ValueError, sqlite3.Error) as error:
                        st.error(f"Case update failed: {error}")

            st.download_button(
                "Download Case Register",
                data=cases.to_csv(index=False).encode("utf-8"),
                file_name="FraudShield_AI_case_register.csv",
                mime="text/csv",
            )

    except (ValueError, KeyError, sqlite3.Error) as error:
        st.error(f"Case management error: {error}")
