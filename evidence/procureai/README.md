# ProcureAI FMCG — public evidence extract (first release, September 2026)

> **Archived extract.** These files come from the project's first release. The project has since been rebuilt end to end
> (PostgreSQL warehouse, Power BI report built in Desktop, retrained models, re-evaluated contract search), and some figures
> changed. The current figures and their limits are on the [case study page](https://davarkk10.github.io/bikashit-portfolio/procureai/).

**Question:** Which procurement exceptions deserve review, and what evidence should the reviewer see before approving an action?

This is an independent portfolio proof of concept built on a deterministic **synthetic** FMCG corpus. It demonstrates a decision chain: source transaction → reconciled warehouse metric → ranked exception → contract context → human review. It does not report savings, fraud findings, production users, or real-company data.

## Inspect in 90 seconds

1. Read [`docs/claims_register.md`](docs/claims_register.md) for the distinction between measured local outputs and native-system work still pending.
2. Read [`database/09_decision_queries.sql`](database/09_decision_queries.sql) for the intended analytical questions. The PostgreSQL scripts are part of the larger build pack; these queries are shown for review, **not** represented as server-run results.
3. Open [`powerbi/measures.dax`](powerbi/measures.dax) for the semantic KPI definitions. Native PBIX assembly and refresh are pending.
4. Read [`reports/final_acceptance.md`](reports/final_acceptance.md) and the [machine-readable gate result](artifacts/final_regression/final_regression.json). These are retained evidence from the source release, not evidence of a native cloud deployment.
5. Open [`src/api.py`](src/api.py) to inspect the FastAPI decision-support layer that exposes validated marts to workflow and application clients.

## Reproduce the public subset

With Python 3.11+ and a virtual environment:

```bash
python -m pip install -r requirements.txt
python src/generate_procureai_data.py
python src/validate_and_document.py
python src/build_release1_reference.py
uvicorn src.api:app --reload
```

Then open `http://127.0.0.1:8000/docs` to use FastAPI's interactive Swagger documentation.

The generator uses seed `20260927`, creates transaction CSVs and 402 synthetic PDFs, and replaces generated outputs. Validation checks keys, relationships, arithmetic, workflows, ground truth, and document extraction. The warehouse reference builder creates conformed CSVs and seven analytical marts, then runs its own checks.

## FastAPI decision layer

The API turns ProcureAI's analytical outputs into integration-ready services that can be called by an approval workflow, ERP prototype, web front end, or n8n flow.

- `GET /health` — verifies that the generated ProcureAI datasets are available.
- `GET /api/v1/exceptions` — returns the highest-priority invoice exceptions from the reconciled three-way-match mart.
- `GET /api/v1/invoices/{invoice_id}/decision-support` — converts deterministic exception flags into a human-review priority, reasons, and recommended next action.
- `GET /api/v1/suppliers/{supplier_id}/performance` — exposes OTIF, rejection rate and supplier performance context.
- `GET /api/v1/contracts/search?q=...` — performs deterministic keyword search over the generated synthetic contract PDFs and returns an evidence snippet.

This API does **not** autonomously approve payments, label fraud, or claim a production deployment. It is a portfolio decision-support integration layer over synthetic data.

## One example decision

An invoice with a missing purchase order and quantity gap should enter a review queue with its amount and reasons visible. A reviewer then checks the cited contract context and chooses an action. The interactive [decision cockpit](https://procureai-fmcg-bikashit.netlify.app/#cockpit) illustrates this path with a synthetic test-window record. The walkthrough is deterministic; it is not a live payment or autonomous approval system.

## Claim boundary

Locally validated: source generator and validation checks; reference warehouse and analytical marts. The public extract now includes a FastAPI integration layer and smoke tests, but a hosted production API is **not** claimed. Pending native evidence still includes production deployment, a live n8n instance, Microsoft tenant approval, and a cross-system enterprise run.
