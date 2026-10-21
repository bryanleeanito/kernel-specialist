// shell-env-dev.js — environment untuk setiap perintah shell:
// UTF-8 (anti error Indonesia) + hemat bytecode + path journal.
// Port ke OpenCode V2: hook `shell.env` → ctx.shell.hook("create.before").
import path from "node:path"
import os from "node:os"

export default {
  id: "shell-env-dev",
  async setup(ctx) {
    await ctx.shell.hook("create.before", (event) => {
      const env = event.env || (event.env = {})
      env.PYTHONUTF8 = "1"
      env.PYTHONDONTWRITEBYTECODE = "1"
      env.LANG = env.LANG || "C.UTF-8"
      env.LC_ALL = env.LC_ALL || "C.UTF-8"
      env.OPENCODE_JOURNAL =
        env.OPENCODE_JOURNAL || path.join(os.homedir(), ".config", "opencode", "journal", "commands.log")
    })
  },
}
