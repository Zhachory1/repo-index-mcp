#!/usr/bin/env node
import { spawnSync } from "node:child_process";

const uvx = process.env.CODESCRY_UVX || "uvx";
const args = ["codescry", ...process.argv.slice(2)];
const result = spawnSync(uvx, args, { stdio: "inherit" });

if (result.error) {
  if (result.error.code === "ENOENT") {
    console.error([
      "CodeScry npm wrapper requires uv, but uvx was not found on PATH.",
      "Install uv: https://docs.astral.sh/uv/getting-started/installation/",
      "Then retry: npx codescry doctor"
    ].join("\n"));
    process.exit(127);
  }

  console.error(`CodeScry npm wrapper failed: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
