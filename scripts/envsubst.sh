#!/usr/bin/env bash
###############################################################################
# envsubst.sh - Substitute environment variables in .template files
#
# Purpose:
#   This script processes one or more `.template` files (or directories containing them),
#   substituting environment variables with their values as defined in a specified `.env` file.
#   It generates rendered output files in a target directory.
#
# Input:
#   - A `.env` file containing variable definitions (default: `.env`)
#   - One or more `.template` files, or directories to scan for `.template` files
#
# Output:
#   - Rendered files with variables substituted, written to an output directory
#     (default: `.localfiles`), preserving relative paths.
#
# Key Features:
#   - Validates that all variables used in templates are defined in the environment.
#   - Recursively scans directories for `.template` files.
#   - Safely loads variables from the `.env` file.
#   - Uses colored output for errors, status, and help messages.
#
# Usage:
#   ./scripts/envsubst.sh [options] <file(s)> | <directory>
#   Options:
#     -e, --env-file <path>   Path to .env file (default: .env)
#     -o, --output <path>     Output directory (default: .localfiles)
#     -h, --help              Show help message and usage examples
#
# Example:
#   ./scripts/envsubst.sh -e .env.dev -o .localfiles docker/confs/nginx
###############################################################################
set -e

# Define colors for pretty output
BOLD="\033[1m"
BLUE="\033[34m"
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
RESET="\033[0m"

# Function to display usage information
usage() {
  echo -e "${BOLD}Usage:${RESET} ./scripts/envsubst.sh [options] <file(s)> | <directory>"
  echo
  echo "Options:"
  echo "  -e, --env-file <path>   Path to .env file (default: .env)"
  echo "  -o, --output <path>     Output directory (default: .localfiles)"
  echo "  -h, --help              Show this help message"
  echo
  echo "Examples:"
  echo "  ./scripts/envsubst.sh docker/confs/nginx"
  echo "  ./scripts/envsubst.sh -e .env.dev -o .localfiles docker/confs/nginx"
  echo
  exit 0
}

# Parse command line arguments
ENV_FILE=".env"
OUTPUT_DIR=".localfiles"
FILES=()
DIRS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    -o|--output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    -*)
      echo -e "${RED}[ERROR]${RESET} Unknown option: $1"
      usage
      ;;
    *)
      if [ -d "$1" ]; then
        DIRS+=("$1")
      elif [ -f "$1" ]; then
        FILES+=("$1")
      else
        echo -e "${RED}[ERROR]${RESET} Path not found: $1"
        exit 1
      fi
      shift
      ;;
  esac
done

if [ ${#FILES[@]} -eq 0 ] && [ ${#DIRS[@]} -eq 0 ]; then
  echo -e "${RED}[ERROR]${RESET} No files or directories specified."
  usage
fi

# Load environment variables from the .env file safely
if [ ! -f "$ENV_FILE" ]; then
  echo -e "${RED}[ERROR]${RESET} .env file not found at $ENV_FILE"
  exit 1
fi

set -a
while IFS='=' read -r key value; do
  # ignore empty lines and comments
  if [[ -z "$key" || "$key" == \#* ]]; then
    continue
  fi
  # remove quotes from the value
  value="${value%\"}"
  value="${value#\"}"
  export "$key"="$value"
done < "$ENV_FILE"
set +a

# Collect all template files from specified files and directories
TEMPLATES=("${FILES[@]}")
for dir in "${DIRS[@]}"; do
  while IFS= read -r file; do
    TEMPLATES+=("$file")
  done < <(find "$dir" -type f -name "*.template")
done

if [ ${#TEMPLATES[@]} -eq 0 ]; then
  echo -e "${RED}[ERROR]${RESET} No .template files found."
  exit 1
fi

# Verify that all variables used in templates are defined and build the substitution list
ROOT_DIR="$(pwd)"
ALL_VARS=()

for template in "${TEMPLATES[@]}"; do
  vars=$(grep -o '\${[A-Za-z0-9_]\+}' "$template" | sort -u | tr -d '${}')
  for var in $vars; do
    # add variable to list if not already present
    if [[ ! " ${ALL_VARS[*]} " =~ " ${var} " ]]; then
      ALL_VARS+=("$var")
    fi
    # check if variable is defined in environment
    if [ -z "${!var+x}" ]; then
      echo -e "${RED}[ERROR]${RESET} Missing variable: ${BOLD}$var${RESET} (used in ${template#$ROOT_DIR/})"
      exit 1
    fi
  done
done

# Create a list of variables for envsubst in the format ${VAR1} ${VAR2} ...
SUBST_LIST=""
for v in "${ALL_VARS[@]}"; do
  SUBST_LIST+='$'"{$v} "
done

# Generate output files by substituting variables in templates
for template in "${TEMPLATES[@]}"; do
  rel_path="${template#$ROOT_DIR/}"
  rel_path_no_ext="${rel_path%.template}"
  output_path="$OUTPUT_DIR/$rel_path_no_ext"
  mkdir -p "$(dirname "$output_path")"

  echo -e "${BLUE}[BUILD]${RESET} $output_path"
  envsubst "$SUBST_LIST" < "$template" > "$output_path"
done

echo -e "${GREEN}[OK]${RESET}    Templates rendered successfully → $OUTPUT_DIR"
