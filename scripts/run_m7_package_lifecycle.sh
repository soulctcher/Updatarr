#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
release_one=${1:-"$project_root/build/m7-lifecycle-release-1"}
release_two=${2:-"$project_root/build/m7-lifecycle-release-2"}
evidence_root=${3:-"$project_root/build/m7-lifecycle"}
release_one=$(realpath -m "$release_one")
release_two=$(realpath -m "$release_two")
evidence_root=$(realpath -m "$evidence_root")

for command in docker sha256sum; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf '%s is unavailable; no lifecycle drill was started.\n' "$command" >&2
    exit 2
  fi
done
mapfile -t packages_one < <(find "$release_one" -maxdepth 1 -type f -name 'updatarr-*.pkg.tar.zst' -print)
mapfile -t packages_two < <(find "$release_two" -maxdepth 1 -type f -name 'updatarr-*.pkg.tar.zst' -print)
for package_count in "${#packages_one[@]}" "${#packages_two[@]}"; do
  if [[ "$package_count" -ne 1 ]]; then
    printf 'Each lifecycle input directory must contain exactly one package; found %s.\n' "$package_count" >&2
    exit 2
  fi
done
package_one=${packages_one[0]}
package_two=${packages_two[0]}
version_one=$(pacman -Qp "$package_one" | awk '{print $2}')
version_two=$(pacman -Qp "$package_two" | awk '{print $2}')
if [[ -e "$evidence_root" ]] && find "$evidence_root" -mindepth 1 -print -quit | grep -q .; then
  printf 'Evidence directory is not empty: %s\n' "$evidence_root" >&2
  exit 2
fi
mkdir -p "$evidence_root/context"
cp "$project_root/packaging/release/Dockerfile.m7-lifecycle" \
  "$evidence_root/context/Dockerfile"
cp "$project_root/packaging/release/m7_lifecycle_state.py" \
  "$evidence_root/context/"
cp "$package_one" "$evidence_root/context/release-1.pkg.tar.zst"
cp "$package_two" "$evidence_root/context/release-2.pkg.tar.zst"

docker build \
  --memory=2g \
  --tag updatarr-m7-runtime-base:local \
  --file "$project_root/packaging/release/Dockerfile.m7-runtime-base" \
  "$project_root/packaging/release"

run_id=$(date -u +%Y%m%dT%H%M%SZ)
docker build \
  --network=none \
  --memory=2g \
  --build-arg="EVIDENCE_RUN=$run_id" \
  --build-arg="VERSION_ONE=$version_one" \
  --build-arg="VERSION_TWO=$version_two" \
  --tag updatarr-m7-lifecycle:local \
  "$evidence_root/context" 2>&1 | tee "$evidence_root/lifecycle.log"

sha256sum \
  "$package_one" \
  "$package_two" \
  > "$evidence_root/packages.sha256"
docker image inspect updatarr-m7-runtime-base:local updatarr-m7-lifecycle:local \
  --format '{{.RepoTags}} {{.Id}} {{.Created}}' \
  > "$evidence_root/images.txt"
printf 'M7 disposable lifecycle evidence written to %s\n' "$evidence_root"
