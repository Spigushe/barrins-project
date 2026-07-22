#!/bin/bash
# Fails if any secrets/**/*.env file (excluding *.env.example) is tracked by
# git — staged, committed, or otherwise present in the index. Constitution
# ss34: secrets must never be stored inside a repository. Run before
# committing, or wire up as a git pre-commit hook:
#   ln -s ../../scripts/check_no_secrets_committed.sh .git/hooks/pre-commit
set -euo pipefail

tracked=$(git ls-files 'secrets/**/*.env' | grep -v '\.env\.example$' || true)

if [ -n "$tracked" ]; then
  echo "error: the following files must never be committed (see secrets/README.md):" >&2
  echo "$tracked" >&2
  echo "Run: git rm --cached <file> to untrack it, then verify .gitignore covers it." >&2
  exit 1
fi
