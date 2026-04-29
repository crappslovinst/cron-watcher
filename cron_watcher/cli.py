"""CLI entry point for cron-watcher."""

from __future__ import annotations

import argparse
import json
import sys

from cron_watcher.config import load_config
from cron_watcher.log_parser import filter_failures, parse_log_file
from cron_watcher.reporter import build_report, format_text_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cron-watcher",
        description="Monitor cron job execution and report failures.",
    )
    parser.add_argument(
        "--config",
        default="cron_watcher.toml",
        metavar="FILE",
        help="Path to config file (default: cron_watcher.toml)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    report_cmd = sub.add_parser("report", help="Generate a failure report")
    report_cmd.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="fmt",
        help="Output format (default: text)",
    )
    report_cmd.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="Number of top failing jobs to show (default: 5)",
    )
    report_cmd.add_argument(
        "--log",
        metavar="FILE",
        help="Override log file path from config",
    )

    sub.add_parser("check-config", help="Validate the config file and exit")

    return parser


def cmd_report(args: argparse.Namespace, cfg) -> int:
    log_path = args.log or cfg.log_path
    events = parse_log_file(log_path)
    failures = filter_failures(events)
    report = build_report(failures, top_n=args.top)

    if args.fmt == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_text_report(report))
    return 0


def cmd_check_config(cfg) -> int:
    print(f"Config OK — log_path={cfg.log_path}")
    if cfg.alert:
        print(f"  alert type : {cfg.alert.type}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.command == "report":
        return cmd_report(args, cfg)
    if args.command == "check-config":
        return cmd_check_config(cfg)

    return 0


if __name__ == "__main__":
    sys.exit(main())
