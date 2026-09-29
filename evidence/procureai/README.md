# ProcureAI FMCG — public evidence extract

**Question:** Which procurement exceptions deserve review, and what evidence should the reviewer see before approving an action?

This is an independent portfolio proof of concept built on a deterministic **synthetic** FMCG corpus. It demonstrates a decision chain: source transaction → reconciled warehouse metric → ranked exception → contract context → human review. It does not report savings, fraud findings, production users, or real-company data.

## Inspect in 90 seconds

1. Read [`docs/claims_register.md`](docs/claims_register.md) for the distinction between measured local outputs and native-system work still pending.
2. Read [`database/09_decision_queries.sql`](database/09_decision_queries.sql) for the intended analytical questions. The PostgreSQL scripts are part of the larger build pack; these queries are shown for review, **not** represented as server-run results.
3. Open [`powerbi/measures.dax`](powerbi/measures.dax) for the semantic KPI definitions. Native PBIX assembly and refresh are pending.
4. Read [`reports/final_acceptance.md`](reports/final_acceptance.md) and the [machine-readable gate result](artifacts/final_regression/final_regression.json). These are retained evidence from the source release, not evidence of a native cloud deployment.

## Reproduce the public subset

With Python 3.11+ and a virtual environment:

```bash
python -m pip install -r requirements.txt
python src/generate_procureai_data.py
python src/validate_and_document.py
python src/build_release1_reference.py
```

The generator uses seed `20260927`, creates transaction CSVs and 402 synthetic PDFs, and replaces generated outputs. Validation checks keys, relationships, arithmetic, workflows, ground truth, and document extraction. The warehouse reference builder creates conformed CSVs and seven analytical marts, then runs its own checks. This public extract supports the above three-command reproduction; the 11-gate local regression cited in the case study was run on the larger source release, which also contains ML, RAG, API and workflow modules.

The generated corpus is intentionally omitted from Git to keep this review path small. Generation may take a few minutes and needs disk space for roughly 300 MB of outputs. The original source release is a synthetic project pack; no private operational records are needed.

## One example decision

An invoice with a missing purchase order and quantity gap should enter a review queue with its amount and reasons visible. A reviewer then checks the cited contract context and chooses an action. The interactive [decision cockpit](https://procureai-fmcg-bikashit.netlify.app/#cockpit) illustrates this path with a synthetic test-window record. The walkthrough is deterministic; it is not a live payment or autonomous approval system.

## Claim boundary

Locally validated: source generator and 46 validation checks; reference warehouse and seven marts; ML, RAG, API and fixture-driven workflows in the larger release. Pending native evidence: PostgreSQL 16 server execution, PBIX refresh, a live n8n instance, Microsoft tenant approval, and a cross-system run. The public extract does **not** claim to reproduce all 11 downstream gates by itself.
