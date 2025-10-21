#!/usr/bin/env python3
"""
envsubst.py — strict environment substitution tool.

Features:
- Replaces ${VAR} with environment variable values.
- Loads .env first (if provided), then system environment.
- Fails safely if any variable is missing (no file changes).
- Accepts only files (no directories).
- Supports --dry-run mode to show planned substitutions.
- Docker-style colored logs (uses 'rich' if available).
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# --- Logging setup ---
try:
    from rich.console import Console

    console = Console()

    def log(level, msg):
        styles = {
            "INFO": "bold blue",
            "WARN": "bold yellow",
            "ERROR": "bold red",
            "FATAL": "bold white on red",
            "OK": "bold green",
        }
        console.print(f"[{level}] {msg}", style=styles.get(level, "white"))
except ImportError:
    console = None

    def log(level, msg):
        colors = {
            "INFO": "\033[1;34m",
            "WARN": "\033[1;33m",
            "ERROR": "\033[1;31m",
            "FATAL": "\033[1;41m",
            "OK": "\033[1;32m",
        }
        color = colors.get(level, "")
        reset = "\033[0m"
        print(f"{color}[{level}]{reset} {msg}")


# --- Helper functions ---
def load_env_file(path: Path) -> Dict[str, str]:
    """Load variables from a .env file."""
    env_vars = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def find_variables(content: str) -> List[str]:
    """Find all ${VAR} placeholders in file content."""
    return sorted(set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", content)))


def substitute_variables(content: str, env: Dict[str, str]) -> Tuple[str, List[str]]:
    """Substitute ${VAR} with env values; return (new_content, missing_vars)."""
    vars_found = find_variables(content)
    missing = [v for v in vars_found if v not in env]
    if missing:
        return content, missing
    return (
        re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", lambda m: env[m.group(1)], content),
        [],
    )


# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Strict envsubst replacement tool.")
    parser.add_argument(
        "-e", "--env-file", dest="env_file", help="Path to .env file (optional)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what substitutions would be made, without modifying files.",
    )
    parser.add_argument("files", nargs="+", help="One or more files to process.")
    args = parser.parse_args()

    # --- Validate file inputs ---
    file_paths = [Path(f) for f in args.files]
    invalid = [f for f in file_paths if not f.is_file()]
    if invalid:
        for f in invalid:
            log("ERROR", f"Path '{f}' is not a valid file.")
        sys.exit(1)

    # --- Load environment ---
    env_vars = dict(os.environ)
    if args.env_file:
        env_path = Path(args.env_file)
        if env_path.exists():
            log("INFO", f"Loading environment variables from '{env_path}'...")
            file_env = load_env_file(env_path)
            env_vars = {**env_vars, **file_env}  # .env overrides system
        else:
            log("WARN", f".env file '{env_path}' not found — using environment only.")
    else:
        log("INFO", "No .env file provided — using current environment only.")

    # --- Check for missing variables ---
    missing_by_file: Dict[Path, List[str]] = {}
    for file_path in file_paths:
        text = file_path.read_text(encoding="utf-8")
        _, missing = substitute_variables(text, env_vars)
        if missing:
            missing_by_file[file_path] = missing

    if missing_by_file:
        log("ERROR", "Missing required environment variables:")
        for file_path, vars_missing in missing_by_file.items():
            vars_joined = ", ".join(vars_missing)
            log("ERROR", f"  {file_path}: {vars_joined}")
        log("FATAL", "Aborting substitution — undefined variables present.")
        sys.exit(1)

    # --- Perform substitution or dry run ---
    for file_path in file_paths:
        text = file_path.read_text(encoding="utf-8")
        vars_found = find_variables(text)

        if args.dry_run:
            if not vars_found:
                log("INFO", f"No variables found in '{file_path}'.")
                continue
            log("INFO", f"Dry run for '{file_path}':")
            for var in vars_found:
                value = env_vars.get(var, "(undefined)")
                log("INFO", f"  ${var} → {value}")
        else:
            new_text, _ = substitute_variables(text, env_vars)
            file_path.write_text(new_text, encoding="utf-8")
            log("OK", f"Substitution complete: '{file_path}'")

    if args.dry_run:
        log("OK", f"Dry run completed for {len(file_paths)} file(s).")
    else:
        log("OK", f"All files processed successfully ({len(file_paths)} total).")


if __name__ == "__main__":
    main()
