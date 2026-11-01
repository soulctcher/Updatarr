#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
echo "build_m5_source_archive.sh is retained for M5 evidence; building the current archive." >&2
exec "$project_root/scripts/build_source_archive.sh"
