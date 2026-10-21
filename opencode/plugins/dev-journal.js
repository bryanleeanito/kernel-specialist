// dev-journal.js — catat setiap perintah shell + HASILNYA ke journal (audit sesi).
// Port ke OpenCode V2: hook `tool.execute.after` → ctx.tool.hook("execute.after").
// FORMAT: `[ts] [OK rc=0|FAIL rc=N|RUN] cmd :: pesan`
// Tidak memblokir apa pun (observasi saja).
import fs from "node:fs"
import path from "node:path"
import os from "node:os"

const SHELL_TOOLS = new Set(["bash", "shell", "sh", "exec", "run_command", "run"])

function journalPath() {
  return (
    process.env.OPENCODE_JOURNAL ||
    path.join(os.homedir(), ".config", "opencode", "journal", "commands.log")
  )
}

function log(line) {
  try {
    const base = journalPath()
    fs.mkdirSync(path.dirname(base), { recursive: true })
    fs.appendFileSync(base, line + "\n", "utf8")
  } catch {
    /* journal gagal = bukan masalah */
  }
}

export default {
  id: "dev-journal",
  async setup(ctx) {
    await ctx.tool.hook("execute.after", async (event) => {
      try {
        const tool = String(event?.tool || "")
        if (!SHELL_TOOLS.has(tool.toLowerCase())) return

        const input = event?.input || {}
        const rawCmd = String(input.command ?? input.cmd ?? input.script ?? "").replace(/\s+/g, " ").slice(0, 300)

        const result = event?.result
        const error = event?.error
        let rc = null
        let outText = ""
        if (result && typeof result === "object") {
          outText = String(result.output ?? result.stdout ?? "")
          const cand = result.exitCode ?? result.exitcode ?? result.code ?? result.rc
          if (typeof cand === "number") rc = cand
        }
        if (rc === null && error) rc = 1

        const errTxt = String(error?.message ?? error ?? "").replace(/\s+/g, " ").slice(0, 200)
        const fail = (rc !== null && !Number.isNaN(rc) && rc !== 0) || !!error
        const tag = rc === null || Number.isNaN(rc) ? "RUN" : fail ? `FAIL rc=${rc}` : `OK rc=${rc}`

        log(`[${new Date().toISOString()}] [${tag}] ${rawCmd}${errTxt ? " :: " + errTxt : ""}`)
      } catch {
        /* journal tidak boleh mengganggu agent */
      }
    })
  },
}
