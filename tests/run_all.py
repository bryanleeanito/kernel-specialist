#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_all.py — gate semua tes kernel-specialist.

Jalankan: python3 tests/run_all.py
Exit 0 hanya kalau SEMUA tes lulus.
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
TOOLS_DIR = os.path.join(KIT, "tools")


def find_tests():
    found = []
    for root, dirs, files in os.walk(TOOLS_DIR):
        dirs[:] = [d for d in dirs if not d.startswith("__")]
        if "tests.py" in files:
            found.append(os.path.join(root, "tests.py"))
    # tes guardrail plugin (node)
    guard = os.path.join(KIT, "tests", "test_guardrail.mjs")
    if os.path.exists(guard):
        found.append(guard)
    return sorted(found)


def main():
    tests = find_tests()
    if not tests:
        print("[!] tidak ada tests.py ditemukan")
        return 1
    print("=" * 66)
    print("KERNEL-SPECIALIST — TEST GATE")
    print(f"kit    : {KIT}")
    print(f"jumlah : {len(tests)} berkas tes")
    print("=" * 66)
    total = passed = 0
    failed = []
    for t in tests:
        name = os.path.relpath(t, KIT)
        t0 = time.time()
        if t.endswith(".mjs"):
            p = subprocess.run(["node", t], capture_output=True, text=True, timeout=300)
        else:
            p = subprocess.run([sys.executable, t], capture_output=True, text=True, timeout=600)
        dt = time.time() - t0
        for line in (p.stdout or "").splitlines():
            if "lulus" in line and "/" in line:
                frac = line.strip().split()[0]
                try:
                    ok, tot = frac.split("/")
                    total += int(tot)
                    passed += int(ok)
                except ValueError:
                    pass
        status = "LULUS" if p.returncode == 0 else "GAGAL"
        print(f"  [{status}] {name}  ({dt:.1f}s)")
        if p.returncode != 0:
            failed.append(name)
            print("-" * 66)
            print((p.stdout or "")[-2500:])
            print((p.stderr or "")[-1500:])
            print("-" * 66)
    print("=" * 66)
    if total:
        print(f"TOTAL: {passed}/{total} assertion lulus")
    print(f"FILES: {len(tests) - len(failed)}/{len(tests)} berkas tes lulus")
    if failed:
        print("GAGAL: " + ", ".join(failed))
    print("=" * 66)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
