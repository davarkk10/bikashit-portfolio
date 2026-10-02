#!/usr/bin/env bash
# Runs each "-- Qn." query in 03-05 and writes olist/results/qn_<name>.csv
set -euo pipefail
PGURL=${PGURL:-postgresql://postgres@127.0.0.1/postgres}
cd "$(dirname "$0")"
mkdir -p ../results
python3 - "$PGURL" <<'PY'
import re, subprocess, sys
url = sys.argv[1]
for f in ["03_late_vs_reviews.sql", "04_where_and_who.sql", "05_impact_and_lanes.sql"]:
    text = open(f).read()
    for block in re.split(r"\n(?=-- Q\d+\.)", text)[1:]:
        n, title = re.match(r"-- Q(\d+)\.\s*([^\n:(]+)", block).groups()
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:40]
        out = f"../results/q{int(n):02d}_{slug}.csv"
        sql = "SET search_path = olist;\n" + block
        res = subprocess.run(["psql", url, "-q", "--csv", "-v", "ON_ERROR_STOP=1"], input=sql,
                             capture_output=True, text=True, check=True).stdout
        open(out, "w").write(res.lstrip())
        print(out, len(res.splitlines()) - 1, "rows")
PY
