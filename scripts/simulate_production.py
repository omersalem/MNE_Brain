#!/usr/bin/env python3
"""Legacy entry point for the offline evidence-flow benchmark.

Despite the historical filename, this script does not simulate production,
connect to Ministry systems, collect telemetry, or execute remediation.
"""

import sys

from run_benchmarks import run_benchmarks


def run_simulation() -> dict:
    print("NOTICE: simulate_production.py is retained as an offline compatibility entry point.")
    return run_benchmarks()


if __name__ == "__main__":
    sys.exit(0 if run_simulation()["success"] else 1)
