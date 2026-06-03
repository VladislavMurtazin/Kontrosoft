from __future__ import annotations

import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import grpc
import pytest
from grpc_tools import protoc

from . import config


def _generate_protos() -> None:
    config.GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    init_file = config.GENERATED_DIR / "__init__.py"
    init_file.touch(exist_ok=True)

    args = [
        "grpc_tools.protoc",
        f"-I{config.PROTO_PATH.parent}",
        f"--python_out={config.GENERATED_DIR}",
        f"--grpc_python_out={config.GENERATED_DIR}",
        str(config.PROTO_PATH),
    ]
    result = protoc.main(args)
    if result != 0:
        raise RuntimeError(f"Failed to generate protobuf files from {config.PROTO_PATH}")


def _wait_for_port(host: str, port: int, timeout_sec: float) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.05)
    raise TimeoutError(f"Port {host}:{port} is not reachable within {timeout_sec}s")


@pytest.fixture(scope="session", autouse=True)
def generate_grpc_stubs() -> None:
    _generate_protos()

    generated_root = str(config.GENERATED_DIR)
    if generated_root not in sys.path:
        sys.path.insert(0, generated_root)


@pytest.fixture
def app_process(generate_grpc_stubs: None):
    if not config.BUILD_BINARY.exists():
        raise FileNotFoundError(
            f"Binary not found: {config.BUILD_BINARY}. Run ./build.sh before ./test.sh."
        )

    process = subprocess.Popen(
        [str(config.BUILD_BINARY)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for_port(config.GRPC_HOST, config.GRPC_PORT, config.APP_START_TIMEOUT_SEC)
        yield process
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=config.GRACEFUL_SHUTDOWN_TIMEOUT_SEC)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


@pytest.fixture
def grpc_client(app_process):
    import monitor_pb2
    import monitor_pb2_grpc

    channel = grpc.insecure_channel(f"{config.GRPC_HOST}:{config.GRPC_PORT}")
    stub = monitor_pb2_grpc.MonitorServiceStub(channel)

    yield stub, monitor_pb2

    channel.close()


@pytest.fixture
def udp_sender():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        yield sock
    finally:
        sock.close()


def wait_until_ready(stub, monitor_pb2) -> None:
    deadline = time.time() + config.APP_START_TIMEOUT_SEC
    while time.time() < deadline:
        response = stub.IsReady(monitor_pb2.Empty())
        if response.is_ready:
            return
        time.sleep(config.READINESS_POLL_INTERVAL_SEC)
    raise TimeoutError("Application did not become ready in time")


def get_stats(stub, monitor_pb2):
    return stub.GetUdpStatistics(monitor_pb2.Empty())


def wait_for_stats_delta(stub, monitor_pb2, base_packets: int, base_a_bytes: int, delta_packets: int, delta_a_bytes: int) -> None:
    deadline = time.time() + config.STAT_PROPAGATION_TIMEOUT_SEC
    while time.time() < deadline:
        current = get_stats(stub, monitor_pb2)
        if (
            current.packets == base_packets + delta_packets
            and current.aBytes == base_a_bytes + delta_a_bytes
        ):
            return
        time.sleep(0.05)
    raise TimeoutError(
        "Expected stats delta not observed in time: "
        f"packets +{delta_packets}, aBytes +{delta_a_bytes}"
    )
