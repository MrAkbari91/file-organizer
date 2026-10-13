#!/usr/bin/env sh
# Invoke with: sh build.sh [--gui | --cli]
set -eu
cd -- "$(dirname -- "$0")"
exec "${FILE_ORGANIZER_PYTHON:-python3}" scripts/bootstrap_build.py "$@"
