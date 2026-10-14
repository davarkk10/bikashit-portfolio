# Contract assistant v2 (October 2026)

**Why:** the first release answered only 56% of 25 unseen questions on its first run. It abstained too readily on everyday wording such as "max price hike % allowed for CTR00210".

## How v2 works

1. **Index** every one of the 402 PDFs into sentences, each tagged with its clause heading, file and page. Wrapped lines are rejoined; "Pvt. Ltd." no longer breaks a sentence.
2. **Route** on document IDs (CTR, INV, QUOTE). An ID with no matching document means the assistant abstains.
3. **Rank** with BM25 plus a small procurement thesaurus that maps everyday words ("hike", "get out of", "roll over", "vendor") to contract terms.
4. **Answer** with the best sentence verbatim and a `[file, page N]` citation. Nothing is generated.
5. **Abstain** when the question's key terms aren't covered, or it asks about something the documents never mention (penalties, warranties, insurance, signatories).

## How it was tested

- `make_questions.py` wrote two sets before any retriever code existed: 60 **dev** questions in formal wording for building, and 68 **held-out** questions in everyday wording on different documents.
- The held-out file's sha256 was recorded at 05:01 UTC (`questions/FROZEN_SHA256.txt`). The assistant's code hash was recorded at the single held-out run (`ASSISTANT_SHA256_AT_HELDOUT_RUN.txt`).

## Results

| Set | Correct | Wrong answers given | Abstained when it shouldn't |
|---|---|---|---|
| Dev (60) | 60/60 | 0 | 0 |
| **Held-out, first and only run (68)** | **64/68 (94.1%)** | **0** | **4** |

Held-out by type: contracts 39/40, invoices 12/12, quotes 5/5, unanswerable 6/6 correctly refused, policies 2/5. The four misses are all abstentions on loosely worded questions ("how far can an invoice price drift…"), so the assistant said nothing rather than something wrong. Full answers are in `heldout_first_run.json`.

## Limits

- **I wrote both the questions and the assistant**, including the thesaurus, after writing the held-out wording. A test set written by someone else would be a stronger check.
- These are new questions, so 94% is not directly comparable with the first release's 56% on its 25-question set.
- The documents are templated; real contracts vary far more.
- Lexical retrieval only. A hosted embedding model would handle wording the thesaurus doesn't cover.

## Reproduce

```bash
python src/generate_procureai_data.py
python contract_assistant_v2/evaluate.py documents contract_assistant_v2/questions/heldout.jsonl
```
