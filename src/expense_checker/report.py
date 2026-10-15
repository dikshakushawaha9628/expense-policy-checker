"""Console + CSV reporting. Deterministic failures and AI observations are printed in
SEPARATE sections and exported in separate columns - they are never blended."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


def _table(rows, headers) -> str:
    rows = [[str(c) for c in r] for r in rows]
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h) for i, h in enumerate(headers)]
    line = lambda cells: "  ".join(c.ljust(w) for c, w in zip(cells, widths))  # noqa: E731
    return "\n".join([line(headers), line(["-" * w for w in widths]), *(line(r) for r in rows)])


def build_report(conn: sqlite3.Connection, detail_limit: int = 12) -> str:
    q = lambda sql, *a: conn.execute(sql, a).fetchall()  # noqa: E731
    out: list[str] = []

    out.append("=" * 78 + "\n1. DATA LOAD\n" + "=" * 78)
    out.append(_table([(r["batch_id"], r["source_file"], r["rows_read"], r["rows_new"],
                        r["rows_skipped_existing"], r["rows_rejected"])
                       for r in q("SELECT * FROM ingest_batches ORDER BY batch_id")],
                      ["batch", "file", "read", "new", "skipped(dup)", "rejected"]))
    n = q("SELECT COUNT(*) c FROM expenses")[0]["c"]
    out.append(f"\nCurated expenses: {n}")
    rejects = q("SELECT expense_id, reason FROM rejected_records ORDER BY reject_id")
    if rejects:
        out.append("\nRejected records (never silently dropped):")
        out.append(_table([(r["expense_id"] or "(none)", r["reason"][:60]) for r in rejects],
                          ["expense_id", "reason"]))

    out.append("\n" + "=" * 78 + "\n2. DETERMINISTIC RULE FAILURES  (policy v1.0 - authoritative)\n" + "=" * 78)
    out.append(_table([(r["rule_id"], r["severity"], r["violations"], f"{r['usd_exposed']:.2f}")
                       for r in q("SELECT * FROM v_violations_by_rule")],
                      ["rule", "severity", "failures", "usd_exposed"]))
    c = q("SELECT rule_status, COUNT(*) c FROM v_expense_review GROUP BY rule_status")
    counts = {r["rule_status"]: r["c"] for r in c}
    out.append(f"\nExpenses: PASS={counts.get('PASS', 0)}  FAIL={counts.get('FAIL', 0)}")
    out.append("\nSample of failures:")
    out.append(_table([(r["expense_id"], r["failed_rules"], r["category"], f"{r['amount_usd']:.2f}")
                       for r in q("SELECT * FROM v_expense_review WHERE rule_status='FAIL' "
                                  "ORDER BY expense_id LIMIT ?", detail_limit)],
                      ["expense_id", "failed_rules", "category", "usd"]))

    out.append("\n" + "=" * 78 + "\n3. AI OBSERVATIONS  (advisory only - NOT rule failures)\n" + "=" * 78)
    obs = q("SELECT ai_label, COUNT(*) c FROM v_expense_review WHERE ai_status IS NOT NULL "
            "GROUP BY ai_label ORDER BY c DESC")
    if not obs and not q("SELECT 1 FROM ai_observations LIMIT 1"):
        out.append("(no AI observations yet - run `ai`)")
    else:
        out.append(_table([(r["ai_label"] or "(none)", r["c"]) for r in obs], ["label", "count"]))
        st = q("SELECT status, COUNT(*) c FROM ai_observations GROUP BY status")
        out.append("\nStatus: " + ", ".join(f"{r['status']}={r['c']}" for r in st))
        out.append("\nNon-'consistent' observations on expenses that PASS every rule "
                   "(what only AI noticed):")
        out.append(_table(
            [(r["expense_id"], r["ai_label"] or r["ai_status"], f"{r['ai_confidence']:.2f}" if r["ai_confidence"] is not None else "-",
              "REVIEW" if r["ai_needs_human_review"] else "", r["ai_rationale"][:52])
             for r in q("SELECT * FROM v_expense_review WHERE rule_status='PASS' AND ai_status IS NOT NULL "
                        "AND COALESCE(ai_label,'') <> 'consistent' ORDER BY expense_id LIMIT ?", detail_limit)],
            ["expense_id", "label", "conf", "human?", "rationale"]))
    return "\n".join(out)


def export_csv(conn: sqlite3.Connection, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cur = conn.execute("SELECT * FROM v_expense_review ORDER BY expense_id")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([d[0] for d in cur.description])
        w.writerows(cur.fetchall())
    return path
