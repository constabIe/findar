#!/usr/bin/env bash
set -euo pipefail

# === Color definitions ===
RESET="\033[0m"
BOLD="\033[1m"

INFO="\033[1;34m[INFO]\033[0m"    # Blue
WARN="\033[1;33m[WARN]\033[0m"    # Yellow
ERROR="\033[1;31m[ERROR]\033[0m"  # Red
FATAL="\033[1;41m[FATAL]\033[0m"  # White on Red background
OK="\033[1;32m[OK]\033[0m"        # Green

# === Defaults ===
ENV_FILE=""
TARGET_FILE=""

# По дефолту переменные считываются из окружения машины. Если передан файл
# c переменными окружения, то в приоритет ставятся переменные из файла.
# В случае отсутствия переменной рецепт завершается с ошибкой.
usage() {
  echo "Usage: $0 [-e FILE] <target_file>"
  echo ""
  echo "Options:"
  echo "  -e FILE   Path to .env file (optional)"
  echo ""
  echo "Examples:"
  echo "  $0 config.yaml"
  echo "  $0 -e .env config.yaml"
  exit 1
}

# --- Parse arguments ---
while getopts "e:h" opt; do
  case "$opt" in
    e) ENV_FILE="$OPTARG" ;;
    h) usage ;;
    *) usage ;;
  esac
done
shift $((OPTIND-1))

if [ "$#" -ne 1 ]; then usage; fi
TARGET_FILE="$1"

if [ ! -f "$TARGET_FILE" ]; then
  echo -e "${ERROR} Target file '$TARGET_FILE' not found." >&2
  exit 1
fi

# --- Load environment file if provided ---
if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
  echo -e "${INFO} Loading environment variables from '${BOLD}$ENV_FILE${RESET}'..."
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" == \#* ]] && continue
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
    if [ -z "${!key-}" ]; then
      export "$key=$value"
    fi
  done < "$ENV_FILE"
elif [ -n "$ENV_FILE" ]; then
  echo -e "${WARN} .env file '${BOLD}$ENV_FILE${RESET}' not found — using current environment only."
else
  echo -e "${INFO} No .env file provided — using current environment only."
fi

# --- Detect variables in file ---
echo -e "${INFO} Checking for undefined variables in '${BOLD}$TARGET_FILE${RESET}'..."
VARS=$(grep -o '\${[A-Za-z_][A-Za-z0-9_]*}' "$TARGET_FILE" | sort -u | tr -d '${}')
MISSING=()

for var in $VARS; do
  if [ -z "${!var-}" ]; then
    MISSING+=("$var")
  fi
done

# --- Handle missing variables ---
if [ ${#MISSING[@]} -ne 0 ]; then
  echo -e "${ERROR} Missing required environment variables:"
  for v in "${MISSING[@]}"; do
    echo -e "        - ${BOLD}${v}${RESET}"
  done
  echo -e "${FATAL} Aborting substitution — undefined variables detected."
  exit 1
fi

# --- Substitute variables ---
TMP_FILE="${TARGET_FILE}.tmp"
echo -e "${INFO} All required variables are defined. Processing file..."
envsubst < "$TARGET_FILE" > "$TMP_FILE" && mv "$TMP_FILE" "$TARGET_FILE"
echo -e "${OK} Substitution complete: '${BOLD}$TARGET_FILE${RESET}'"