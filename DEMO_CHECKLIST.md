# FraudGraph AI — Hackathon Demo Checklist

## Before the demo
- [ ] Run `python -m py_compile app.py src/fraud_engine.py src/graph_analysis.py src/money_flow.py src/alert_engine.py src/case_manager.py`.
- [ ] Run `python -m streamlit run app.py --browser.gatherUsageStats false`.
- [ ] Confirm the dashboard opens without an error.
- [ ] Confirm the Pre-Payment Risk Checker section is absent.
- [ ] Use demo data first; keep personal PhonePe data private.
- [ ] Confirm the case database and report/export features are available.

## Demo flow (about 5–7 minutes)
1. **Problem (30 sec):** Explain that investigators need to identify suspicious transaction patterns and follow money movement.
2. **Transaction Investigation (60 sec):** Show transactions, risk levels, reasons, filtering, and CSV export.
3. **Account Investigation (60 sec):** Select an account and inspect sent/received activity and related transactions.
4. **Relationship Graph (60 sec):** Explain nodes and edges and show connected accounts.
5. **Money-Flow Tracing (60 sec):** Select a source/destination supported by the data and demonstrate a path if one exists.
6. **Alerts (45 sec):** Show an alert and explain its indicators.
7. **Case Management & Report (60 sec):** Open/update a case and generate an evidence report.
8. **Limitations (30 sec):** State that scores are heuristic, not proof of fraud; the prototype has no live UPI integration.

## Test cases
- [ ] Normal repeated payments are not marked High Risk solely due to repetition.
- [ ] High transaction amount is treated as an indicator, not proof of fraud.
- [ ] Multiple suspicious indicators produce an explainable score.
- [ ] Unknown account identifiers are handled without inventing identities.
- [ ] CSV upload errors are shown clearly.
- [ ] Graph and money-flow views work with the active dataset.
- [ ] Alerts and case-management sections load.
- [ ] PDF and CSV export work.

## Judge-facing claims
**Claim only after verifying live:** transaction investigation, heuristic risk scoring, account relationship visualization, money-flow tracing, alerts, case management, and report export.

**Do not claim unless separately built and measured:** trained ML model, verified fraud-detection accuracy, live UPI verification, real-time payment interception, automatic payment blocking, or access to bank fraud databases.

## Final checklist
- [ ] README and requirements are included in the submitted project.
- [ ] No secrets, credentials, personal statements, or private data are committed.
- [ ] Demo uses fictional/synthetic data unless authorization is confirmed.
- [ ] Repository has a clear project description and screenshots.
