"""ProcureAI contract assistant v2: cite the page, or say nothing.

1. Index      every PDF is split into sentence-level units, each carrying its clause heading,
              file and page number.
2. Route      a document ID in the question (CTR#####, INV#######, QUOTE####) restricts the
              search to that document. An ID with no matching document -> abstain.
3. Rank       BM25 over heading + sentence, with a small procurement thesaurus that maps
              everyday wording ("hike", "get out of", "roll over") to contract terms.
4. Answer     the best sentence is returned verbatim with a [file, page N] citation.
              Nothing is generated, so nothing can be invented.
5. Abstain    if the question's key terms are not covered by the best sentence, or it asks
              about something the documents never mention.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

STOP = set("""a an the of for to in on at by is are was be do does did we our us you your i it its this that
what whats which who whom how many much when where why can could should would will shall has have had
any there their than then from with as or and if into out about per each under over up down
me my so just need needed owe get apply applies answer period allowed allow required require""".split())
PHRASES = {"end date": "ends", "start date": "starts", "expiry date": "ends"}
VALUE_CUES = {"much", "many", "when", "date", "amount", "value", "total", "percent", "days", "worth", "owe", "rfq", "po", "order"}

# Everyday wording -> words the documents use. One line per concept.
THESAURUS = {
    "escalation": "hike hikes increase increases raise rise rises go up price escalation adjustment ceiling cap max maximum yearly annual",
    "terminate": "terminate termination end exit cancel get out warning notice quit leave",
    "ends": "expire expires expiry expiration last valid until ends end date",
    "starts": "start starts begin begins effective commence commences kicks from",
    "renewal": "renew renews renewal roll over rollover auto automatic automatically itself extend",
    "value": "worth value size indicative amount roughly",
    "governing": "jurisdiction courts court governing law legal state",
    "payment": "pay payment terms term paid",
    "parties": "vendor supplier party parties counterparty between",
    "quotation": "quote quotes quotation quotations competing bids comparable three",
    "tolerance": "drift difference differences variance tolerance deviate differ",
    "approval": "senior sign off signoff approve approval approver",
    "duplicate": "duplicate twice same repeated again resubmitted",
    "automated": "ai automated automation recommendation bot",
    "gross": "total owe gross amount payable",
    "purchase": "po purchase order billed against reference",
    "due": "due falls payable deadline",
    "rfq": "rfq request submitted quotation",
}
EXPAND = {}
for canon, words in THESAURUS.items():
    for w in words.split():
        EXPAND.setdefault(w, set()).update(words.split())

ID_RE = re.compile(r"\b(CTR\d{5}|INV\d{7}|QUOTE\d{4})\b", re.I)


def split_sentences(text):
    t = text.replace("Pvt.", "Pvt\u2024").replace("Ltd.", "Ltd\u2024")
    return [x.replace("\u2024", ".") for x in re.split(r"(?<=[.])\s+(?=[A-Z])", t) if x.strip()]


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


class Assistant:
    def __init__(self, docs: Path, k1=1.4, b=0.6, min_cover=0.5):
        self.k1, self.b, self.min_cover = k1, b, min_cover
        self.units = []
        for pdf in sorted(docs.rglob("*.pdf")):
            prose = pdf.parent.name in ("contracts", "policies")   # clause documents vs tabular invoices/quotes
            for pno, page in enumerate(PdfReader(str(pdf)).pages, 1):
                heading, para = "", []

                def add(text, heading=None):
                    if re.search(r"[A-Za-z]", text):
                        h = heading or ""
                        self.units.append({"file": pdf.name, "page": pno, "heading": h, "text": text.strip(),
                                           "toks": tokens(h + " " + text)})

                def flush():
                    if para:
                        for sent in split_sentences(" ".join(para)):
                            add(sent, heading)
                        para.clear()
                for raw in (page.extract_text() or "").split("\n"):
                    line = raw.strip()
                    if not line or line.startswith("Synthetic portfolio document") or re.fullmatch(r"Page \d+", line):
                        continue
                    if prose and re.match(r"^\d{1,2} [A-Z][a-z]", line) and len(line) < 40:
                        flush(); heading = line; continue
                    if prose:
                        para.append(line)
                    else:
                        for seg in line.split(" | "):
                            add(seg)
                flush()
        self.N = len(self.units)
        self.avgdl = sum(len(u["toks"]) for u in self.units) / self.N
        df = Counter(t for u in self.units for t in set(u["toks"]))
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        self.vocab = set(df)
        self.files = {u["file"] for u in self.units}

    def _score(self, u, qterms):
        tf = Counter(u["toks"]); dl = len(u["toks"]); s = 0.0
        for t, w in qterms.items():
            if t in tf:
                s += w * self.idf.get(t, 0) * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return s

    def ask(self, question: str):
        ids = [m.upper() for m in ID_RE.findall(question)]
        pool = self.units
        if ids:
            want = {f"{i}.pdf" for i in ids}
            if not want & self.files:
                return {"abstain": True, "reason": f"No document found for {', '.join(ids)}"}
            pool = [u for u in self.units if u["file"] in want]
        q = ID_RE.sub(" ", question).lower()
        for a, b in PHRASES.items():
            q = q.replace(a, b)
        base = tokens(q)
        wants_value = bool(VALUE_CUES & set(re.findall(r"[a-z]+", q))) or "%" in q
        if not base:
            return {"abstain": True, "reason": "No question terms"}
        # key terms the documents never use and the thesaurus does not explain -> the answer cannot be in them
        unknown = [t for t in base if t not in self.vocab and t not in EXPAND and not t.isdigit()]
        qterms = Counter()
        for t in base:
            qterms[t] += 1.0
            for e in EXPAND.get(t, ()):
                if e != t:
                    qterms[e] += 0.5
        def score(u):
            s = self._score(u, qterms)
            return s * (1.3 if wants_value and re.search(r"\d", u["text"]) else 1.0)
        ranked = sorted(pool, key=score, reverse=True)
        best = ranked[0]
        concept_hit = [t for t in base if t in best["toks"] or (EXPAND.get(t, set()) & set(best["toks"]))]
        cover = len(concept_hit) / len(base)
        if unknown and len(unknown) / len(base) >= 0.34:
            return {"abstain": True, "reason": f"The documents never mention: {', '.join(unknown)}"}
        if cover < self.min_cover or self._score(best, qterms) <= 0:
            return {"abstain": True, "reason": "No sentence in the documents answers this"}
        return {"abstain": False, "answer": best["text"], "heading": best["heading"],
                "citation": f"[{best['file']}, page {best['page']}]", "file": best["file"], "page": best["page"]}
