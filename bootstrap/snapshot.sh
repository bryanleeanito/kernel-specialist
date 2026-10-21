#!/usr/bin/env bash
# snapshot.sh — ambil state aktual mesin ini sebagai JSON (parity reference).
#   - untuk membuat expected.json (state yang dianggap "benar")
#   - untuk membandingkan saat verifikasi
# Output: JSON ke stdout.
set -uo pipefail

LAB="${LAB:-/root/kernel-lab}"
KIT="${KIT:-$LAB/kernel-specialist}"
API_URL="${API_URL:-}"
API_PW="${API_PW:-}"

api() {
  if [ -n "$API_URL" ]; then
    OPENCODE_PASSWORD="$API_PW" opencode api get "$1" --server "$API_URL" 2>/dev/null
  else
    opencode api get "$1" 2>/dev/null
  fi
}

py() { python3 -c "$1" 2>/dev/null; }

echo "{"
SEP=""
emit() { printf '%s  "%s": %s' "$SEP" "$1" "$2"; SEP=","; }

# --- packages -------------------------------------------------------------
pkgs=$(py '
import subprocess, json
want = ["build-essential","bc","bison","flex","libssl-dev","libelf-dev","dwarves","ccache","lld",
        "rustc","rust-src","bindgen","mok-util","nodejs","jq","cpio","zstd","rsync","kmod",
        "python3-dev","libncurses-dev","linux-headers-" + subprocess.run(["uname","-r"],capture_output=True,text=True).stdout.strip()]
out = {}
for p in want:
    r = subprocess.run(["dpkg-query","-W","-f=${Status}",p], capture_output=True, text=True)
    out[p] = "ok" if "installed" in r.stdout else "MISSING"
print(json.dumps(out))
')
emit "packages" "${pkgs-}"

# --- plugins --------------------------------------------------------------
pl=$(api /api/plugin | py '
import sys,json
try: d=json.load(sys.stdin)
except Exception: print("[]"); raise SystemExit
n=[p.get("id") for p in d.get("data",[]) if p.get("source",{}).get("type")!="builtin"]
print(json.dumps(sorted([x for x in n if x])))
')
emit "plugins" "${pl-[]}"

# --- agents / commands ----------------------------------------------------
ag=$(api /api/agent | py '
import sys,json
try: d=json.load(sys.stdin)
except Exception: print("[]"); raise SystemExit
keep={"kernel","kernel-reviewer","oops-analyst","driver-dev","goal","goal-verify","recon-analyst","vuln-analyst"}
print(json.dumps(sorted(a.get("name") for a in d.get("data",[]) if a.get("name") in keep)))
')
emit "agents" "${ag-[]}"
cm=$(api /api/command | py '
import sys,json
try: d=json.load(sys.stdin)
except Exception: print("[]"); raise SystemExit
print(json.dumps(sorted(c.get("name") for c in d.get("data",[]) if c.get("name"))))
')
emit "commands" "${cm-[]}"

# --- skills ---------------------------------------------------------------
sk=$(py '
import os, json
d=[]
for base in (os.path.expanduser("~/.agents/skills"), os.path.expanduser("~/.config/opencode/skills")):
    if os.path.isdir(base):
        d += [x for x in os.listdir(base) if not x.startswith(".")]
print(json.dumps(sorted(set(d))))
')
emit "skills" "${sk-[]}"

# --- tuning (M2) ---------------------------------------------------------
tu=$(py '
import subprocess, json
keys=["net.ipv4.tcp_congestion_control","net.core.default_qdisc","net.core.rmem_max","net.core.wmem_max",
      "net.ipv4.tcp_rmem","net.ipv4.tcp_wmem","vm.swappiness","vm.vfs_cache_pressure"]
out={}
for k in keys:
    r=subprocess.run(["sysctl","-n",k],capture_output=True,text=True)
    out[k]=r.stdout.strip() if r.returncode==0 else "MISSING"
print(json.dumps(out))
')
emit "tuning" "${tu-}"

# --- git ------------------------------------------------------------------
gt=$(py '
import subprocess, json, os
def g(*a): return subprocess.run(["git"]+list(a),capture_output=True,text=True).stdout.strip()
print(json.dumps({
 "user.name": g("config","--global","user.name"),
 "user.email": g("config","--global","user.email"),
 "credential_helper": bool(g("config","--global","credential.helper")),
 "ssh_key_present": os.path.exists(os.path.expanduser("~/.ssh/id_ed25519_github")),
}))
')
emit "git" "${gt-}"

# --- mesh -----------------------------------------------------------------
ms=$(py '
import json, os, glob
out={"mesh_repo":None,"registered":False,"presence":False}
for base in ("/run/media/*/*/CyberSecurity*","/mnt/d/CyberSecurity*","/media/*/CyberSecurity*"):
    hits=glob.glob(os.path.join(base,"07-SISTEM","opencode-mesh-v2"))
    if hits:
        m=hits[0]; out["mesh_repo"]=m
        rp=os.path.join(m,"state","registry.json")
        if os.path.exists(rp):
            try:
                d=json.load(open(rp))
                out["registered"]=any(x.get("name")=="kali-kernel" for x in d.get("machines",[]))
            except Exception: pass
        out["presence"]=os.path.exists(os.path.join(m,"state","presence","kali-kernel.json"))
        break
print(json.dumps(out))
')
emit "mesh" "${ms-}"

# --- file & dir config ----------------------------------------------------
fm=$(py '
import os, json
cfg=os.path.expanduser("~/.config/opencode")
want=["AGENTS.md","MEMORY.md","TRACKER.md","KERNEL-AGENTS.md","MEMORY-KERNEL.md","TRACKER-KERNEL.md","opencode.json"]
out={w:os.path.exists(os.path.join(cfg,w)) for w in want}
for sub in ("agents","commands","skills","plugins"):
    p=os.path.join(cfg,sub)
    out[sub]=sorted(x for x in os.listdir(p) if not x.startswith(".") and ".bak-" not in x) if os.path.isdir(p) else []
print(json.dumps(out))
')
emit "files" "${fm-}"

# --- tests ----------------------------------------------------------------
ts=$(LAB="$LAB" KIT="$KIT" py '
import subprocess, json, os
res={}
kit=os.environ.get("KIT","")
if os.path.isdir(os.path.join(kit,"tests")):
    r=subprocess.run(["python3",os.path.join(kit,"tests","run_all.py")],capture_output=True,text=True)
    line=[l for l in r.stdout.splitlines() if l.startswith("TOTAL")]
    res["kit"]={"rc":r.returncode,"summary":line[0].strip() if line else "?"}
ops=os.path.join(os.environ.get("LAB",""),"kali-ops")
if os.path.isdir(os.path.join(ops,"tests")):
    r=subprocess.run(["node",os.path.join(ops,"tests","test_guardrail_kali.mjs")],capture_output=True,text=True)
    line=[l for l in r.stdout.splitlines() if "assertion lulus" in l]
    res["kali_ops"]={"rc":r.returncode,"summary":line[0].strip() if line else "?"}
print(json.dumps(res))
')
emit "tests" "${ts-}"

echo ""
echo "}"
