"""Grade the assistant on a question set.

Correct  answerable: the answer string appears in the returned sentence and the cited file is right
         unanswerable: the assistant abstains
Usage: python evaluate.py <documents dir> <questions.jsonl> [out.json]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

from assistant import Assistant

docs, qfile = Path(sys.argv[1]), Path(sys.argv[2])
bot = Assistant(docs)
rows, by = [], defaultdict(lambda: [0, 0])
for line in qfile.read_text().splitlines():
    it = json.loads(line); r = bot.ask(it["q"])
    if it["answerable"]:
        ok = (not r["abstain"]) and it["answer"].lower() in r["answer"].lower() and r["file"] == it["file"]
    else:
        ok = r["abstain"]
    grp = it["type"].split(":")[0]
    by[grp][0] += ok; by[grp][1] += 1
    rows.append({**it, "ok": ok, "response": r})
n_ok = sum(r["ok"] for r in rows)
ans = [r for r in rows if r["answerable"]]
summary = {"set": qfile.name, "n": len(rows), "correct": n_ok, "accuracy": n_ok / len(rows),
           "answerable_correct": sum(r["ok"] for r in ans), "answerable_n": len(ans),
           "wrong_answers_given": sum((not r["ok"]) and (not r["response"]["abstain"]) for r in rows),
           "abstained_when_answerable": sum(r["answerable"] and r["response"]["abstain"] for r in rows),
           "by_type": {k: f"{a}/{b}" for k, (a, b) in by.items()}}
print(json.dumps(summary, indent=2))
for r in rows:
    if not r["ok"]:
        print("MISS", r["type"], "|", r["q"], "|", r["response"].get("answer", r["response"].get("reason")))
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
