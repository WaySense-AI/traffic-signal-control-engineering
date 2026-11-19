#!/usr/bin/env python3
"""Run the full SignalLab test suite and every example."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXAMPLES = [
    "end_to_end_demo",
    "corridor_case",
    "experiment_cycle",
    "experiment_quality",
    "experiment_coordination",
    "queue_lab",
    "timeline_lab",
    "resilience_lab",
]


def run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def show(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests-only", action="store_true", help="run only the unit tests")
    parser.add_argument("--examples-only", action="store_true", help="run only the examples")
    args = parser.parse_args()
    if args.tests_only and args.examples_only:
        parser.error("--tests-only and --examples-only are mutually exclusive")

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    print(f"SignalLab verification on Python {sys.version.split()[0]}")
    print(f"Repository: {ROOT}")

    test_count = 0
    if not args.examples_only:
        print("\n== unit tests ==")
        result = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], env)
        show(result)
        if result.returncode != 0:
            print("FAILED: unit tests", file=sys.stderr)
            return result.returncode
        match = re.search(r"Ran (\d+) tests?", result.stderr + result.stdout)
        if match:
            test_count = int(match.group(1))

    if not args.tests_only:
        print("\n== examples ==")
        for index, module in enumerate(EXAMPLES, start=1):
            print(f"[{index}/{len(EXAMPLES)}] examples.{module}")
            result = run([sys.executable, "-m", f"examples.{module}"], env)
            show(result)
            if result.returncode != 0:
                print(f"FAILED: examples.{module}", file=sys.stderr)
                return result.returncode

    if args.tests_only:
        print(f"\nSignalLab: {test_count} tests passed")
    elif args.examples_only:
        print(f"\nSignalLab: {len(EXAMPLES)} examples passed")
    else:
        print(f"\nSignalLab: {test_count} tests, {len(EXAMPLES)} examples passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
