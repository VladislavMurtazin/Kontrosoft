from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BUILD_BINARY = ROOT_DIR / "build" / "grpc_udp_monitor"
PROTO_PATH = ROOT_DIR / "cpp-application" / "monitor.proto"
GENERATED_DIR = ROOT_DIR / "tests" / "generated"

GRPC_HOST = "127.0.0.1"
GRPC_PORT = 2031
UDP_HOST = "127.0.0.1"
UDP_PORT = 2032

APP_START_TIMEOUT_SEC = 10.0
READINESS_POLL_INTERVAL_SEC = 0.1
STAT_PROPAGATION_TIMEOUT_SEC = 2.0
GRACEFUL_SHUTDOWN_TIMEOUT_SEC = 5.0
