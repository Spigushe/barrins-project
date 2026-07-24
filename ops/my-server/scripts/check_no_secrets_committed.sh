#!/bin/bash
# Fails if any file under secrets/ is tracked by git — staged, committed, or
# otherwise present in the index — except *.example templates and README.md.
# Constitution ss34: secrets must never be stored inside a repository, so
# this deliberately allow-lists rather than blocklists specific filenames
# (any new secret file, whatever it's named, is caught by default). Run
# before committing, or wire up as a git pre-commit hook:
#   ln -s ../../scripts/check_no_secrets_committed.sh .git/hooks/pre-commit
set -euo pipefail

tracked=$(git ls-files 'secrets/**' | grep -v -E '(\.example$|/README\.md$)' || true)

if [ -n "$tracked" ]; then
  echo "error: the following files must never be committed (see secrets/README.md):" >&2
  echo "$tracked" >&2
  echo "Run: git rm --cached <file> to untrack it, then verify .gitignore covers it." >&2
  exit 1
fi
