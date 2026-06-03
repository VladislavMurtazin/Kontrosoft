from __future__ import annotations

import signal
import time

from . import config
from .conftest import get_stats, wait_for_stats_delta, wait_until_ready


def _send_payloads(udp_sender, payloads: list[bytes]) -> int:
    total_a = 0
    for payload in payloads:
        udp_sender.sendto(payload, (config.UDP_HOST, config.UDP_PORT))
        total_a += payload.count(b"A")
    return total_a


def test_process_becomes_ready_and_stays_ready(grpc_client):
    stub, monitor_pb2 = grpc_client
    wait_until_ready(stub, monitor_pb2)

    for _ in range(3):
        response = stub.IsReady(monitor_pb2.Empty())
        assert response.is_ready is True
        time.sleep(config.READINESS_POLL_INTERVAL_SEC)


def test_initial_counters_are_zero(grpc_client):
    stub, monitor_pb2 = grpc_client
    wait_until_ready(stub, monitor_pb2)
    stats = get_stats(stub, monitor_pb2)
    assert stats.packets == 0
    assert stats.aBytes == 0


def test_single_datagram_counts_packets_and_A_bytes(grpc_client, udp_sender):
    stub, monitor_pb2 = grpc_client
    wait_until_ready(stub, monitor_pb2)

    base = get_stats(stub, monitor_pb2)
    payload = b"ABCA"
    expected_a = payload.count(b"A")

    udp_sender.sendto(payload, (config.UDP_HOST, config.UDP_PORT))
    wait_for_stats_delta(
        stub,
        monitor_pb2,
        base_packets=base.packets,
        base_a_bytes=base.aBytes,
        delta_packets=1,
        delta_a_bytes=expected_a,
    )


def test_multiple_datagrams_are_counted_cumulatively(grpc_client, udp_sender):
    stub, monitor_pb2 = grpc_client
    wait_until_ready(stub, monitor_pb2)

    base = get_stats(stub, monitor_pb2)
    payloads = [
        b"",
        b"BBBB",
        b"A",
        b"AAxAA",
        b"aaaAAAzzz",
    ]
    expected_packets = len(payloads)
    expected_a = _send_payloads(udp_sender, payloads)

    wait_for_stats_delta(
        stub,
        monitor_pb2,
        base_packets=base.packets,
        base_a_bytes=base.aBytes,
        delta_packets=expected_packets,
        delta_a_bytes=expected_a,
    )


def test_counter_is_case_sensitive_for_uppercase_A_only(grpc_client, udp_sender):
    stub, monitor_pb2 = grpc_client
    wait_until_ready(stub, monitor_pb2)

    base = get_stats(stub, monitor_pb2)
    payload = b"aAaAaA"
    expected_a = payload.count(b"A")

    udp_sender.sendto(payload, (config.UDP_HOST, config.UDP_PORT))
    wait_for_stats_delta(
        stub,
        monitor_pb2,
        base_packets=base.packets,
        base_a_bytes=base.aBytes,
        delta_packets=1,
        delta_a_bytes=expected_a,
    )


def test_process_terminates_gracefully_with_exit_code_zero(app_process, grpc_client):
    stub, monitor_pb2 = grpc_client
    wait_until_ready(stub, monitor_pb2)

    app_process.send_signal(signal.SIGTERM)
    app_process.wait(timeout=config.GRACEFUL_SHUTDOWN_TIMEOUT_SEC)
    assert app_process.returncode == 0
