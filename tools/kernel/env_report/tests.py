#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests.py — env_report (kernel lab). Jalankan: python3 tests.py"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "env_report.py")
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def run(args):
    p = subprocess.run([sys.executable, TOOL] + args, capture_output=True, text=True,
                       timeout=180)
    return p.returncode, p.stdout, p.stderr


def main():
    rc, out, err = run(["--json"])
    check("exit code 0", rc == 0, f"rc={rc} err={err[:200]}")
    try:
        data = json.loads(out)
    except Exception as e:  # noqa: BLE001
        check("output JSON valid", False, str(e))
        data = {}
    check("ada key 'system'", "system" in data)
    check("ada key 'toolchain'", "toolchain" in data)
    check("ada key 'source_tree'", "source_tree" in data)
    check("running kernel terdeteksi",
          bool(data.get("system", {}).get("kernel_running")),
          str(data.get("system", {}).get("kernel_running")))
    check("toolchain punya 'gcc' atau 'cc'",
          any(k in data.get("toolchain", {}) for k in ("gcc", "cc")))

    rc2, out2, _ = run([])
    check("mode text exit 0", rc2 == 0)
    check("mode text punya header", "KERNEL LAB" in out2, out2[:80])

    rc3, out3, _ = run(["--tree", "/nonexistent/path", "--json"])
    check("tree tak ada → tetap exit 0 (report read-only)", rc3 == 0)
    d3 = json.loads(out3)
    check("tree tak ada → exists=False", d3["source_tree"]["exists"] is False)

    failed = [r for r in results if not r[1]]
    print("=" * 60)
    print("env_report — TESTS")
    for name, ok, detail in results:
        print(f"  [{'OK' if ok else 'XX'}] {name}" + (f"  ({detail})" if not ok and detail else ""))
    print(f"  {len(results) - len(failed)}/{len(results)} lulus")
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
