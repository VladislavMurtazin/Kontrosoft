#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
TESTS_DIR="${ROOT_DIR}/tests"

if [[ ! -x "${BUILD_DIR}/grpc_udp_monitor" ]]; then
  echo "Binary not found: ${BUILD_DIR}/grpc_udp_monitor"
  echo "Run ./build.sh first."
  exit 1
fi

python3 -m pytest -q "${TESTS_DIR}"
