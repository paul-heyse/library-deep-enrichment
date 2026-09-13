#!/usr/bin/env bash
# Acquire the pinned upstream clone a worker crate builds against, verify the exact revision,
# apply the crate's owned upstream.patch, and refuse any other edit.
#
#   scripts/bootstrap-upstream.sh <ruff|pyrefly> [--plan|--apply]
#
# The clones are gitignored and re-acquired from github.com; they are never committed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
which="${1:?expected ruff or pyrefly}"; mode="${2:---plan}"
case "$which" in
  ruff)    worker_dir="$ROOT/crates/source-facts";     repo=https://github.com/astral-sh/ruff; tag=0.16.1; upstream_rev=80790b348b5188e7fc253665540f442c6ec7dd05 ;;
  pyrefly) worker_dir="$ROOT/crates/python-semantics"; repo=https://github.com/facebook/pyrefly; tag=1.2.0; upstream_rev=1933169ad8ee9e4d4114112eb56ef0811fb0a094 ;;
  *) echo "unknown upstream: $which" >&2; exit 2 ;;
esac
if [[ "$mode" == --plan ]]; then
  printf '%s\n' "Acquire $repo@$tag ($upstream_rev) into $worker_dir/upstream; verify and apply upstream.patch; retain upstream Cargo.lock."
  exit 0
fi
[[ "$mode" == --apply ]] || { printf '%s\n' 'Expected --plan or --apply' >&2; exit 2; }
if [[ ! -d "$worker_dir/upstream" ]]; then
  git clone --depth 1 --branch "$tag" "$repo" "$worker_dir/upstream"
fi
actual_rev="$(git -C "$worker_dir/upstream" rev-parse HEAD)"
[[ "$actual_rev" == "$upstream_rev" ]] || { printf '%s\n' "Unexpected upstream revision $actual_rev (want $upstream_rev)" >&2; exit 1; }
if git -C "$worker_dir/upstream" apply --reverse --check "$worker_dir/upstream.patch" 2>/dev/null; then
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
