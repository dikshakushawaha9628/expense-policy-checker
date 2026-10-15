"""Command line interface.  `python -m expense_checker --help`"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .ai import get_reviewer
from .ai_review import run_ai_review
from .config import SAMPLE_DIR, Settings
from .db import connect, init_db
from .generate_data import write_samples
from .ingest import SchemaError, ingest_file
from .pipeline import run_pipeline
from .report import build_report, export_csv
from .rules import evaluate_all

DEFAULT_FILES = [SAMPLE_DIR / "expenses_batch1.csv", SAMPLE_DIR / "expenses_batch2.csv"]


def _as_of(value: str | None) -> date:
    return date.fromisoformat(value) if value else date.today()


def _print_ingest(stats) -> None:
    for s in stats:
        print(f"[ingest] {s.source_file}: read={s.rows_read} new={s.rows_new} "
              f"skipped_existing={s.rows_skipped_existing} rejected={s.rows_rejected}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="expense-checker", description=__doc__)
    p.add_argument("--db", help="SQLite path (default: $EXPENSE_DB_PATH or output/expenses.db)")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="regenerate synthetic sample CSVs")
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--out", default=str(SAMPLE_DIR))

    sub.add_parser("init", help="create schema + views + FX rates")

    i = sub.add_parser("ingest", help="load CSV file(s) into raw + curated tables")
    i.add_argument("files", nargs="*", type=Path, default=DEFAULT_FILES)

    c = sub.add_parser("check", help="run deterministic policy rules")
    c.add_argument("--as-of", help="processing date YYYY-MM-DD (default: today)")

    sub.add_parser("ai", help="run advisory AI review (provider from AI_PROVIDER)")

    r = sub.add_parser("report", help="print report and export CSV")
    r.add_argument("--csv", default="output/review_report.csv")

    run = sub.add_parser("run", help="init + ingest + check + ai + report")
    run.add_argument("files", nargs="*", type=Path, default=DEFAULT_FILES)
    run.add_argument("--as-of", help="processing date YYYY-MM-DD (default: today)")
    run.add_argument("--csv", default="output/review_report.csv")

    sub.add_parser("edge-demo", help="demonstrate failure / edge cases on a temp DB")

    args = p.parse_args(argv)
    settings = Settings.from_env()

    if args.cmd == "generate":
        for f in write_samples(Path(args.out), args.seed):
            print(f"wrote {f}")
        return 0
    if args.cmd == "edge-demo":
        from . import edge_demo
        edge_demo.main()
        return 0

    conn = connect(args.db or settings.db_path)
    init_db(conn)
    try:
        if args.cmd == "init":
            print(f"database ready at {args.db or settings.db_path}")
        elif args.cmd == "ingest":
            _print_ingest([ingest_file(conn, f) for f in args.files])
        elif args.cmd == "check":
            print(f"[rules] {evaluate_all(conn, _as_of(args.as_of))} violations recorded")
        elif args.cmd == "ai":
            reviewer = get_reviewer(settings)
            if reviewer is None:
                print("AI_PROVIDER=none: skipping")
            else:
                print(f"[ai] provider={reviewer.name} model={reviewer.model} -> {run_ai_review(conn, reviewer, settings.ai_min_confidence)}")
        elif args.cmd == "report":
            print(build_report(conn))
            print(f"\nCSV written to {export_csv(conn, args.csv)}")
        elif args.cmd == "run":
            reviewer = get_reviewer(settings)
            stats, n, ai = run_pipeline(conn, args.files, _as_of(args.as_of), reviewer, settings.ai_min_confidence)
            _print_ingest(stats)
            print(f"[rules] {n} violations recorded")
            print(f"[ai] {ai if ai else 'skipped (AI_PROVIDER=none)'}\n")
            print(build_report(conn))
            print(f"\nCSV written to {export_csv(conn, args.csv)}")
    except SchemaError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
