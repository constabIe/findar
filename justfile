#!/usr/bin/env just --justfile

# default recipe to display help information
default:
  @just --list


# Initialize environment variables
env:
  cp .env.example .env
  cd ./src/static/admiral && cp .env.example .env

# Confirm auto lint action
confirm-lint:
  git add .
  git commit -m "chore: linting"

# Delete files ignored by git
clean:
  git clean -Xdf

