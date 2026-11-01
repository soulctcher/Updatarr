#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
output_root=${1:-"$project_root/build/m7-evidence"}
output_root=$(realpath -m "$output_root")
stage_root=$(mktemp -d /tmp/updatarr-m7-evidence.XXXXXX)
trap 'rm -rf -- "$stage_root"' EXIT

if [[ -e "$output_root" ]]; then
  printf 'Evidence output already exists: %s\n' "$output_root" >&2
  exit 2
fi

for required in jq npm sha256sum uv; do
  if ! command -v "$required" >/dev/null 2>&1; then
    printf 'Required evidence tool is unavailable: %s\n' "$required" >&2
    exit 2
  fi
done
if [[ ! -x "$project_root/.venv/bin/python" ]]; then
  printf 'The locked project environment is unavailable; run uv sync --locked first.\n' >&2
  exit 2
fi

mkdir -p "$stage_root/sboms"

(
  cd "$project_root"
  uv export --locked --no-dev --format cyclonedx1.5 \
    > "$stage_root/sboms/python-runtime.cdx.json"
)

npm --prefix "$project_root/web" sbom \
  --package-lock-only \
  --omit=dev \
  --sbom-format=cyclonedx \
  --sbom-type=application \
  > "$stage_root/sboms/web-runtime.cdx.json"

for sbom in "$stage_root"/sboms/*.json; do
  jq -e '
    .bomFormat == "CycloneDX" and
    (.specVersion | type == "string") and
    (.metadata.component.name | type == "string") and
    (.components | type == "array" and length > 0)
  ' "$sbom" >/dev/null
done

(
  cd "$project_root"
  "$project_root/.venv/bin/python" \
    scripts/generate_dependency_license_inventory.py \
    "$stage_root/sboms/python-runtime.cdx.json" \
    "$stage_root/sboms/web-runtime.cdx.json" \
    "$stage_root/dependency-licenses.json"
)
jq -e '
  .format == "updatarr-declared-license-inventory-v1" and
  (.python_runtime | type == "array" and length > 0) and
  (.browser_runtime | type == "array" and length > 0)
' "$stage_root/dependency-licenses.json" >/dev/null

(
  cd "$project_root"
  sha256sum \
    pyproject.toml \
    uv.lock \
    web/package.json \
    web/package-lock.json \
    packaging/arch/PKGBUILD \
    docs/release/ASSET_PROVENANCE.md \
    web/src/assets/updatarr-loop.png \
    > "$stage_root/reviewed-inputs.sha256"
)

(
  cd "$stage_root"
  sha256sum dependency-licenses.json sboms/*.json > sboms.sha256
)

mkdir -p "$(dirname "$output_root")"
mv "$stage_root" "$output_root"
trap - EXIT

printf 'M7 evidence generated at %s\n' "$output_root"
printf 'Python runtime components: %s\n' \
  "$(jq '.components | length' "$output_root/sboms/python-runtime.cdx.json")"
printf 'Browser runtime components: %s\n' \
  "$(jq '.components | length' "$output_root/sboms/web-runtime.cdx.json")"

