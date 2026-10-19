# FraudGraph AI
## Financial Fraud Detection & Graph Investigation Prototype

FraudGraph AI is a Streamlit-based prototype for investigating transaction data, exploring account relationships, tracing money flows, generating heuristic alerts, and managing investigation cases.

> **Important:** This is a rule-based investigation prototype, not a production fraud-prevention system. Risk scores are heuristic indicators, not probabilities or proof of fraud. Validate all alerts before taking action.

## Features
- Upload and normalize a supported PhonePe transaction statement CSV.
- Analyze transaction-level risk using configurable heuristic rules.
- Review account-level activity and investigation indicators.
- Explore account relationships through a transaction network graph.
- Trace money-flow paths where supported by available transaction data.
- Review automated alerts and manage investigation cases.
- Export transaction/account data and investigation evidence reports.

## Current limitations
- Transaction scoring is rule-based; it is not a trained machine-learning model.
- PhonePe counterparty labels inferred from statement text are **not verified bank-account IDs**.
- A CSV contains historical transactions only. It cannot inspect, approve, block, or intercept a live UPI payment before it is sent.
- High/Medium/Low labels are preliminary risk indicators, not proof of fraud.
- Results depend on the completeness and quality of the uploaded data.

## Requirements
- Python 3.10 or newer recommended.
- Packages listed in `requirements.txt`.
- Windows, macOS, or Linux with a terminal.

## Setup (Windows / VS Code)
1. Open this folder in VS Code.
2. Open **Terminal → New Terminal**.
3. Create a virtual environment if you do not already have one:

   ```powershell
   python -m venv .venv
   ```

4. Activate it in PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use `.venv\Scripts\python.exe` directly.

5. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. Run syntax checks:

   ```powershell
   python -m py_compile app.py src/fraud_engine.py src/graph_analysis.py src/money_flow.py src/alert_engine.py src/case_manager.py
   ```

7. Start the dashboard:

   ```powershell
   python -m streamlit run app.py --browser.gatherUsageStats false
   ```

8. Open the Local URL printed in the terminal if the browser does not open automatically.

## Data
- Demo transactions are expected at `data/transactions.csv`.
- Investigation cases are stored at `data/fraudgraph_cases.db`.
- Upload only a CSV whose column layout matches the format supported by the current parser.
- Back up the case database before manual changes.

## Suggested investigation workflow
1. Start with demo data to confirm the dashboard loads.
2. Review transaction risk scores and reasons.
3. Select an account and inspect related transactions.
4. Explore the relationship graph and money-flow tracing.
5. Review alerts and open/update investigation cases.
6. Export reports only after checking the underlying transaction details.

## Responsible use
Use synthetic or appropriately authorized data for demonstrations. Protect personal financial information. Do not present a risk score as a definitive fraud finding, and do not use this prototype for automated payment-blocking decisions.
