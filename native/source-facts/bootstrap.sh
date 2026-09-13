#!/usr/bin/env bash
set -euo pipefail
worker_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
upstream_rev=80790b348b5188e7fc253665540f442c6ec7dd05
if [[ "${1:---plan}" == --plan ]]; then
  printf '%s\n' "Acquire astral-sh/ruff $upstream_rev into $worker_dir/upstream; verify and apply upstream.patch; retain upstream Cargo.lock."
  exit 0
fi
if [[ "${1:-}" != --apply ]]; then
  printf '%s\n' 'Expected --plan or --apply' >&2
  exit 2
fi
if [[ ! -d "$worker_dir/upstream" ]]; then
  git clone --depth 1 --branch 0.16.1 https://github.com/astral-sh/ruff "$worker_dir/upstream"
fi
actual_rev="$(git -C "$worker_dir/upstream" rev-parse HEAD)"
[[ "$actual_rev" == "$upstream_rev" ]] || { printf '%s\n' 'Unexpected upstream revision' >&2; exit 1; }
if git -C "$worker_dir/upstream" apply --reverse --check "$worker_dir/upstream.patch"; then
  printf '%s\n' 'Verified patch already present'
else
  [[ -z "$(git -C "$worker_dir/upstream" status --porcelain --untracked-files=normal)" ]] || { printf '%s\n' 'Unexpected dirty upstream checkout' >&2; exit 1; }
  git -C "$worker_dir/upstream" apply --check "$worker_dir/upstream.patch"
  git -C "$worker_dir/upstream" apply "$worker_dir/upstream.patch"
fi
patch_check_dir="$(mktemp -d)"
trap 'rm -rf -- "$patch_check_dir"' EXIT
GIT_INDEX_FILE="$patch_check_dir/index" git -C "$worker_dir/upstream" read-tree HEAD
GIT_INDEX_FILE="$patch_check_dir/index" git -C "$worker_dir/upstream" apply --cached "$worker_dir/upstream.patch"
GIT_INDEX_FILE="$patch_check_dir/index" git -C "$worker_dir/upstream" diff --cached HEAD --binary > "$patch_check_dir/expected"
git -C "$worker_dir/upstream" diff HEAD --binary > "$patch_check_dir/actual"
cmp "$patch_check_dir/expected" "$patch_check_dir/actual" || { printf '%s\n' 'Unexpected edits beyond the owned upstream patch' >&2; exit 1; }
[[ -z "$(git -C "$worker_dir/upstream" ls-files --others --exclude-standard)" ]] || { printf '%s\n' 'Unexpected untracked upstream source files' >&2; exit 1; }
sha256sum "$worker_dir/upstream/Cargo.lock" "$worker_dir/upstream.patch"
