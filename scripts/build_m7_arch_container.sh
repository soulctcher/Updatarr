#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
output_root=${1:-"$project_root/build/m7-container-package"}
output_root=$(realpath -m "$output_root")
package_release=${2:-$(sed -n 's/^pkgrel=//p' "$project_root/packaging/arch/PKGBUILD")}
image_name=updatarr-m7-arch-builder:local

if [[ ! "$package_release" =~ ^[1-9][0-9]*$ ]]; then
  printf 'Package release must be a positive whole number.\n' >&2
  exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
  printf 'Docker is unavailable; no container build was started.\n' >&2
  exit 2
fi
if [[ -e "$output_root" ]] && find "$output_root" -mindepth 1 -print -quit | grep -q .; then
  printf 'Output directory is not empty: %s\n' "$output_root" >&2
  exit 2
fi
mkdir -p "$output_root"

docker build \
  --memory=2g \
  --tag "$image_name" \
  --file "$project_root/packaging/release/Dockerfile.m7-build" \
  "$project_root/packaging/release"

docker run --rm \
  --network=none \
  --read-only \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --pids-limit=128 \
  --memory=2g \
  --memory-swap=2g \
  --cpus=4 \
  --user=1000:1000 \
  --workdir=/tmp \
  --tmpfs=/tmp:rw,nosuid,nodev,size=1g \
  --mount="type=bind,src=$project_root/packaging/arch,dst=/input,readonly" \
  --mount="type=bind,src=$output_root,dst=/output" \
  --env="UPDATARR_PACKAGE_RELEASE=$package_release" \
  "$image_name" \
  /usr/bin/bash -euo pipefail -c '
    mkdir -p /tmp/build
    cp /input/PKGBUILD /input/updatarr-0.6.0.tar.gz /tmp/build/
    cd /tmp/build
    sed -i "s/^pkgrel=.*/pkgrel=$UPDATARR_PACKAGE_RELEASE/" PKGBUILD
    makepkg --nodeps --noconfirm --cleanbuild
    cp /tmp/build/updatarr-*.pkg.tar.* /output/
    pacman -Q > /output/build-packages.txt
  '

docker image inspect "$image_name" \
  --format 'builder image {{.Id}} created {{.Created}}' \
  > "$output_root/builder-image.txt"
(
  cd "$output_root"
  sha256sum updatarr-*.pkg.tar.* build-packages.txt builder-image.txt \
    > SHA256SUMS
)

printf 'M7 container package evidence written to %s\n' "$output_root"

