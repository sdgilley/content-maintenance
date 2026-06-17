#!/usr/bin/env bash

set -euo pipefail

for rc_file in "$HOME/.bashrc" "$HOME/.zshrc"; do
  mkdir -p "$(dirname "$rc_file")"
  touch "$rc_file"

  if ! grep -Fq 'unset GITHUB_TOKEN' "$rc_file" || ! grep -Fq 'unset GH_TOKEN' "$rc_file"; then
    cat >> "$rc_file" <<'EOF'

# Ensure gh CLI uses stored credentials instead of inherited Codespaces tokens.
unset GITHUB_TOKEN 2>/dev/null || true
unset GH_TOKEN 2>/dev/null || true
EOF
  fi
done

echo "GitHub CLI startup cleanup is configured."
