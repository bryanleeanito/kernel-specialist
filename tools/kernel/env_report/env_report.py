#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""env_report.py — snapshot environment kernel development (Kali).

Read-only. Tidak mengubah apa pun di sistem.

Usage:
    python3 env_report.py
    python3 env_report.py --json
    python3 env_report.py --tree /root/kernel-lab/src/linux-7.1.5
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time

DEFAULT_TREE = os.environ.get("KERNEL_TREE", "/root/kernel-lab/src/linux-7.1.5")
DEFAULT_BUILD = os.environ.get("KERNEL_BUILD", "/root/kernel-lab/build")


def run(cmd, timeout=20):
    """Jalankan perintah, kembalikan (rc, stdout+stderr)."""
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 127, f"error: {e}"


def out1(cmd, timeout=20):
    rc, o = run(cmd, timeout)
    return o.strip().splitlines()[0].strip() if o.strip() else ""


def tool_version(binary, args=("--version",)):
    path = shutil.which(binary)
    if not path:
        return None
    rc, o = run([path, *args])
    return o.strip().splitlines()[0].strip() if o.strip() else path


def collect_system():
    data = {}
    data["hostname"] = platform.node()
    data["kernel_running"] = platform.release()
    data["kernel_full"] = platform.version()
    data["arch"] = platform.machine()
    data["user"] = os.environ.get("USER") or os.getuid()
    try:
        with open("/etc/os-release") as f:
            data["os_release"] = {k.strip(): v.strip().strip('"')
                                  for k, _, v in (ln.partition("=") for ln in f)
                                  if k.strip()}
    except OSError:
        data["os_release"] = {}
    data["cpu_model"] = out1("lscpu | grep -m1 'Model name' | cut -d: -f2-")
    data["cpu_cores"] = os.cpu_count()
    data["mem_total"] = out1("free -h | awk '/^Mem:/ {print $2}'")
    data["root_free"] = out1("df -h / | awk 'NR==2 {print $4\" (\"$5\" used)\"}'")
    data["boot_free"] = out1("df -h /boot 2>/dev/null | awk 'NR==2 {print $4\" (\"$5\" used)\"}'")
    return data


def collect_toolchain():
    tools = {}
    for name in ("gcc", "clang", "ld", "ld.lld", "make", "bc", "bison", "flex",
                 "ccache", "rustc", "pahole", "cpio", "xz", "zstd", "git",
                 "python3", "rsync", "kmod"):
        v = tool_version(name)
        if v:
            tools[name] = v
    return tools


def collect_secureboot():
    """State Secure Boot.

    `mokutil` tidak tersedia di Kali (paket tidak ada di repo) → baca langsung
    dari efivars kernel: SecureBoot-8be4df61-... (1=aktif, 0=nonaktif) dan
    SetupMode-... (1=setup mode, artinya key tidak terpasang).
    """
    out = {"available": True, "source": None, "secure_boot": None, "setup_mode": None}
    if shutil.which("mokutil"):
        rc, o = run(["mokutil", "--sb-state"])
        out["source"] = "mokutil"
        out["output"] = o.strip()
        return out
    base = "/sys/firmware/efi/efivars"
    if os.path.isdir(base):
        for name, key in (("SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c", "secure_boot"),
                          ("SetupMode-8be4df61-93ca-11d2-aa0d-00e098032b8c", "setup_mode")):
            p = os.path.join(base, name)
            if not os.path.exists(p):
                continue
            try:
                # efivarfs tidak bisa di-seek → baca seluruh file, byte ke-5 = nilai
                with open(p, "rb") as f:
                    data = f.read()
                if len(data) >= 5:
                    out[key] = data[4]
            except OSError:
                pass
        out["source"] = "efivars"
        if out["secure_boot"] is not None:
            out["output"] = ("SecureBoot disabled (efivars: 0) — kernel custom boleh boot "
                             "tanpa MOK" if out["secure_boot"] == 0 else
                             "SecureBoot ENABLED (efivars: 1) — kernel custom butuh MOK/enroll")
        else:
            out["output"] = "efivars tidak bisa dibaca"
        return out
    out["available"] = False
    out["note"] = ("Secure Boot tidak bisa dicek: mokutil tidak terpasang dan "
                   "/sys/firmware/efi/efivars tidak ada (mode BIOS legacy?)")
    return out


def collect_kernel_config(kernel=None):
    kernel = kernel or platform.release()
    path = f"/boot/config-{kernel}"
    if not os.path.exists(path):
        return {"path": path, "exists": False}
    keys = ("CONFIG_RUST=", "CONFIG_DEBUG_INFO_BTF=", "CONFIG_MODULE_SIG=",
            "CONFIG_MODULE_SIG_FORCE=", "CONFIG_MODULES=", "CONFIG_PREEMPTION=",
            "CONFIG_HZ_250=", "CONFIG_LTO=", "CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE=",
            "CONFIG_SYSTEM_TRUSTED_KEYS=", "CONFIG_SYSTEM_REVOCATION_KEYS=",
            "CONFIG_LOCK_DOWN_KERNEL_FORCE=")
    found = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                for k in keys:
                    if line.startswith(k):
                        found[k.rstrip("=")] = line
    except OSError:
        pass
    return {"path": path, "exists": True, "mtime": time.strftime(
        "%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path))), "settings": found}


def collect_packages():
    rc, o = run("dpkg -l 'linux-image*' 2>/dev/null | awk '$1==\"ii\" {print $2\" \"$3}'")
    return [ln.strip() for ln in o.strip().splitlines() if ln.strip()]


def collect_tree(tree):
    if not tree or not os.path.isdir(tree):
        return {"path": tree, "exists": False}
    info = {"path": tree, "exists": True,
            "is_kernel_tree": os.path.exists(os.path.join(tree, "Kconfig")) and
                              os.path.exists(os.path.join(tree, "Makefile"))}
    ver = os.path.join(tree, "Makefile")
    if info["is_kernel_tree"]:
        try:
            with open(ver) as f:
                for line in f:
                    if line.startswith("VERSION ="):
                        info["version"] = line.split("=", 1)[1].strip()
                    elif line.startswith("PATCHLEVEL ="):
                        info["patchlevel"] = line.split("=", 1)[1].strip()
                    elif line.startswith("SUBLEVEL ="):
                        info["sublevel"] = line.split("=", 1)[1].strip()
                    elif line.startswith("EXTRAVERSION ="):
                        info["extraversion"] = line.split("=", 1)[1].strip()
        except OSError:
            pass
        # versi lengkap: MAJOR.PATCHLEVEL.SUBLEVEL
        info["full_version"] = "{}.{}.{}{}".format(
            info.get("version", "?"),
            info.get("patchlevel", "?"),
            info.get("sublevel", "?"),
            info.get("extraversion", ""),
        )
    if os.path.isdir(os.path.join(tree, ".git")):
        rc, o = run(["git", "-C", tree, "describe", "--always", "--dirty", "--tags"])
        info["git_describe"] = o.strip()
        rc, o = run(["git", "-C", tree, "status", "--porcelain"])
        info["git_dirty_files"] = len([l for l in o.strip().splitlines() if l.strip()])
        rc, o = run(["git", "-C", tree, "log", "-1", "--format=%h %ad %s", "--date=short"])
        info["git_last_commit"] = o.strip()
    else:
        info["git"] = False
    return info


def collect_build(build):
    if not build or not os.path.isdir(build):
        return {"path": build, "exists": False}
    art = {}
    for name, rel in (("bzImage", "arch/x86/boot/bzImage"),
                      ("vmlinux", "vmlinux"),
                      ("System.map", "System.map"),
                      (".config", ".config")):
        p = os.path.join(build, rel)
        art[name] = {"exists": os.path.exists(p)}
        if os.path.exists(p):
            st = os.stat(p)
            art[name]["size"] = st.st_size
            art[name]["mtime"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
    kos = []
    for root, _dirs, files in os.walk(os.path.join(build, "..")):
        for f in files:
            if f.endswith(".ko"):
                kos.append(os.path.join(root, f))
    art["ko_count"] = len(kos)
    return {"path": build, "exists": True, "artifacts": art}


def collect_modules_dir():
    d = f"/lib/modules/{platform.release()}"
    if not os.path.isdir(d):
        return {"path": d, "exists": False}
    ko = sum(1 for _r, _d, files in os.walk(d) for f in files if f.endswith(".ko"))
    return {"path": d, "exists": True, "ko_count": ko}


def build_report(tree=None, build=None, kernel=None):
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "system": collect_system(),
        "toolchain": collect_toolchain(),
        "secure_boot": collect_secureboot(),
        "running_kernel_config": collect_kernel_config(kernel),
        "installed_kernel_packages": collect_packages(),
        "source_tree": collect_tree(tree),
        "build_dir": collect_build(build),
        "modules_dir": collect_modules_dir(),
    }


def render(rep):
    L = []
    s = rep["system"]
    L.append("=" * 68)
    L.append("KERNEL LAB — ENVIRONMENT REPORT")
    L.append(f"generated : {rep['generated_at']}")
    L.append("=" * 68)
    L.append("[SISTEM]")
    L.append(f"  host        : {s['hostname']}  (user {s['user']})")
    L.append(f"  distro      : {s.get('os_release', {}).get('PRETTY_NAME', '?')}")
    L.append(f"  running kern: {s['kernel_running']}  ({s['arch']})")
    L.append(f"  cpu         : {s.get('cpu_model') or '?'} / {s.get('cpu_cores')} core")
    L.append(f"  mem / root  : {s.get('mem_total')} / free {s.get('root_free')}")
    L.append(f"  /boot free  : {s.get('boot_free') or 'n/a'}")
    L.append("")
    L.append("[TOOLCHAIN]")
    for k, v in rep["toolchain"].items():
        L.append(f"  {k:10} : {v}")
    missing = [t for t in ("gcc", "make", "bc", "bison", "flex", "libelf", "pahole",
                           "ccache", "openssl", "rustc") if t not in rep["toolchain"]]
    if missing:
        L.append(f"  [missing]  : {', '.join(missing)}")
    L.append("")
    sb = rep["secure_boot"]
    L.append("[SECURE BOOT]")
    if sb.get("available"):
        L.append(f"  {sb.get('output', '')}")
    else:
        L.append(f"  {sb.get('note')}")
    L.append("")
    L.append("[KERNEL CONFIG running]")
    kc = rep["running_kernel_config"]
    if kc.get("exists"):
        L.append(f"  file : {kc['path']}  ({kc.get('mtime')})")
        for k, v in kc.get("settings", {}).items():
            L.append(f"  {k:42} {v}")
    else:
        L.append(f"  {kc['path']} — tidak ada")
    L.append("")
    L.append("[INSTALLED KERNEL PACKAGES]")
    for p in rep["installed_kernel_packages"]:
        L.append(f"  {p}")
    L.append("")
    t = rep["source_tree"]
    L.append("[SOURCE TREE]")
    if t.get("exists"):
        L.append(f"  path    : {t['path']}")
        L.append(f"  version : {t.get('full_version', '?')}")
        if t.get("is_kernel_tree"):
            L.append("  status  : Kconfig+Makefile OK (kernel tree valid)")
        else:
            L.append("  status  : BUKAN kernel tree (Kconfig/Makefile hilang)")
        if t.get("git_describe"):
            L.append(f"  git     : {t['git_describe']}  dirty={t.get('git_dirty_files', 0)} file")
            L.append(f"  commit  : {t.get('git_last_commit', '')}")
    else:
        L.append(f"  {t['path']} — belum ada (jalankan: apt-get source linux)")
    L.append("")
    b = rep["build_dir"]
    L.append("[BUILD DIR]")
    if b.get("exists"):
        art = b["artifacts"]
        for name in ("bzImage", "vmlinux", "System.map", ".config"):
            a = art.get(name, {})
            if a.get("exists"):
                L.append(f"  {name:12} {a['size']:>12,} bytes  {a.get('mtime', '')}")
            else:
                L.append(f"  {name:12} — belum ada")
        L.append(f"  .ko modules : {art.get('ko_count', 0)}")
    else:
        L.append(f"  {b['path']} — belum ada")
    L.append("")
    md = rep["modules_dir"]
    L.append("[MODULES DIR]")
    L.append(f"  {md['path']} — " + (f"{md.get('ko_count')} modul terpasang" if md.get("exists") else "tidak ada"))
    L.append("=" * 68)
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Snapshot environment kernel development")
    ap.add_argument("--tree", default=DEFAULT_TREE, help="path source tree kernel")
    ap.add_argument("--build", default=DEFAULT_BUILD, help="path build dir (O=)")
    ap.add_argument("--kernel", default=None, help="versi kernel (default: running)")
    ap.add_argument("--json", action="store_true", help="output JSON")
    args = ap.parse_args(argv)

    rep = build_report(args.tree, args.build, args.kernel)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
