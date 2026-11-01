#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
version=$(python -c 'import pathlib,sys,tomllib; print(tomllib.loads(pathlib.Path(sys.argv[1]).read_text())["project"]["version"])' "$project_root/pyproject.toml")
archive_name="updatarr-${version}.tar.gz"
output_path="$project_root/packaging/arch/$archive_name"
stage_root=$(mktemp -d /tmp/updatarr-source-archive.XXXXXX)
source_root="$stage_root/updatarr-${version}"
trap 'rm -rf -- "$stage_root"' EXIT

mkdir -p "$source_root/packaging"
tar -C "$project_root" \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='*.egg-info' \
  --exclude='.pytest_cache' --exclude='node_modules' --exclude='build' \
  --exclude='docs/research/m6-validation.md' \
  --exclude='docs/research/m6-independent-review.md' \
  --exclude='docs/research/m7-clean-build-validation.md' \
  --exclude='docs/research/m7-independent-review.md' \
  -cf - src scripts tests docs prototypes web | tar -C "$source_root" -xf -
cp -a "$project_root/packaging/systemd" "$source_root/packaging/"
cp -a "$project_root/packaging/desktop" "$source_root/packaging/"
cp -a "$project_root/packaging/config" "$source_root/packaging/"
tar -C "$project_root/packaging" \
  --exclude='__pycache__' --exclude='*.pyc' \
  -cf - release | tar -C "$source_root/packaging" -xf -
cp -a "$project_root/pyproject.toml" "$project_root/uv.lock" \
  "$project_root/README.md" "$project_root/PLAN.md" \
  "$project_root/MILESTONES.md" "$project_root/ARCHITECTURE.md" \
  "$project_root/DATA_MODEL.md" "$project_root/GLOSSARY.md" \
  "$project_root/CAPABILITY_MATRIX.md" "$project_root/TEST_PLAN.md" \
  "$project_root/OPERATIONS.md" "$project_root/SECURITY.md" \
  "$project_root/CHANGELOG.md" "$project_root/LICENSE" \
  "$project_root/NOTICE" "$source_root/"

tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
  -C "$stage_root" -cf - "updatarr-${version}" | gzip -n > "$output_path"
sha256sum "$output_path"
