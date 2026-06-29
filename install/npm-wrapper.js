#!/usr/bin/env node
"use strict";

const { spawnSync } = require("child_process");
const process = require("process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const REPO = "KalimeroMK/kimi-mcp-hub";
const PYPI_NAME = "kimi-mcp-hub";
const PYTHON_MODULE = "kimi_mcp_hub";
const INSTALL_DIR = path.join(os.homedir(), ".kimi-mcp-hub");
const VENV_DIR = process.env.KIMI_MCP_HUB_VENV || path.join(INSTALL_DIR, ".venv");
const LOCAL_REPO_DIR = path.resolve(path.join(__dirname, ".."));

function log(...args) {
  console.log("[kimi-mcp-hub]", ...args);
}

function error(...args) {
  console.error("[kimi-mcp-hub]", ...args);
}

function getPythonVersion(cmd) {
  const result = spawnSync(cmd, ["--version"], { stdio: "pipe", shell: false });
  if (result.status !== 0) return null;
  const match = String(result.stdout || result.stderr).match(/(\d+)\.(\d+)/);
  if (!match) return null;
  return { major: parseInt(match[1], 10), minor: parseInt(match[2], 10) };
}

function findPython() {
  for (const cmd of ["python3.13", "python3.12", "python3.11", "python3.10", "python3", "python"]) {
    const version = getPythonVersion(cmd);
    if (version && version.major === 3 && version.minor >= 10) return cmd;
  }
  return null;
}

function venvPython() {
  return process.platform === "win32"
    ? path.join(VENV_DIR, "Scripts", "python.exe")
    : path.join(VENV_DIR, "bin", "python");
}

function run(cmd, args, options = {}) {
  const result = spawnSync(cmd, args, {
    stdio: "inherit",
    shell: false,
    ...options,
  });
  return result.status ?? 1;
}

function moduleAvailable(python) {
  const result = spawnSync(
    python,
    ["-c", `import ${PYTHON_MODULE}; print(${PYTHON_MODULE}.__version__)`],
    { stdio: "pipe", shell: false }
  );
  return result.status === 0;
}

function isLocalRepo() {
  return (
    fs.existsSync(path.join(LOCAL_REPO_DIR, "pyproject.toml")) &&
    fs.existsSync(path.join(LOCAL_REPO_DIR, "src", PYTHON_MODULE))
  );
}

function getInstallSpec() {
  if (isLocalRepo()) {
    log("Using local repository at", LOCAL_REPO_DIR);
    return LOCAL_REPO_DIR;
  }
  return `git+https://github.com/${REPO}.git`;
}

function ensureVenv(python) {
  if (fs.existsSync(venvPython())) {
    return;
  }
  log("Creating isolated Python environment...");
  fs.mkdirSync(INSTALL_DIR, { recursive: true });
  const createResult = run(python, ["-m", "venv", VENV_DIR]);
  if (createResult !== 0) {
    error("Failed to create virtual environment.");
    process.exit(1);
  }
}

function installPackage(python) {
  ensureVenv(python);
  const venvPy = venvPython();

  log("Installing Kimi MCP Hub...");

  // Upgrade pip first to avoid build issues.
  run(venvPy, ["-m", "pip", "install", "--upgrade", "pip"]);

  const installSpec = getInstallSpec();

  // Prefer PyPI when the package is published and not running from a local repo.
  let installArgs;
  if (installSpec === LOCAL_REPO_DIR) {
    installArgs = ["-m", "pip", "install", "--no-cache-dir", "--force-reinstall", "--upgrade", installSpec];
  } else {
    const pypiDry = spawnSync(
      venvPy,
      ["-m", "pip", "install", "--dry-run", PYPI_NAME],
      { stdio: "pipe", shell: false }
    );
    installArgs =
      pypiDry.status === 0
        ? ["-m", "pip", "install", "--no-cache-dir", "--force-reinstall", "--upgrade", PYPI_NAME]
        : ["-m", "pip", "install", "--no-cache-dir", "--force-reinstall", "--upgrade", installSpec];
  }

  const installResult = run(venvPy, installArgs);
  if (installResult !== 0) {
    error("Failed to install the Python package.");
    process.exit(1);
  }
  log("Kimi MCP Hub installed.");
}

function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  const python = findPython();
  if (!python) {
    error("Python 3.10+ is required but not found. Install it from https://python.org/downloads");
    process.exit(1);
  }

  const venvPy = venvPython();

  if (command === "install" || command === undefined) {
    installPackage(python);
    log("Running interactive setup...");
    const initResult = run(venvPy, ["-m", PYTHON_MODULE, "init"]);
    process.exit(initResult);
  }

  if (!moduleAvailable(venvPy)) {
    log("Kimi MCP Hub not found. Installing first...");
    installPackage(python);
  }

  const result = run(venvPy, ["-m", PYTHON_MODULE, ...args]);
  process.exit(result);
}

main();
