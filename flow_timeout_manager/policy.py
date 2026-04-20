"""Pure policy helpers used by the controller and unit tests."""

from dataclasses import dataclass
from typing import Optional

from .config import (
    ALLOWED_CLIENT_IP,
    ALLOWED_CLIENT_MAC,
    BLOCKED_CLIENT_IP,
    BLOCKED_CLIENT_MAC,
    BLOCKED_TCP_PORT,
    BLOCK_TIMEOUT,
    FORWARDING_TIMEOUT,
    PROTECTED_SERVER_IP,
    PROTECTED_SERVER_MAC,
    SERVER_A_IP,
    SERVER_A_MAC,
    TimeoutProfile,
)

ETH_TYPE_IP = 0x0800
IPPROTO_TCP = 6


@dataclass(frozen=True)
class PacketFacts:
    """Minimal packet facts needed for controller decisions."""

    src_mac: str
    dst_mac: str
    in_port: int
    eth_type: Optional[int] = None
    ipv4_src: Optional[str] = None
    ipv4_dst: Optional[str] = None
    ip_proto: Optional[int] = None
    tcp_dst: Optional[int] = None


def should_block_service_flow(packet: PacketFacts) -> bool:
    """Return True when the demo firewall policy should install a drop rule."""

    return (
        packet.eth_type == ETH_TYPE_IP
        and packet.ipv4_src == BLOCKED_CLIENT_IP
        and packet.ipv4_dst == PROTECTED_SERVER_IP
        and packet.ip_proto == IPPROTO_TCP
        and packet.tcp_dst == BLOCKED_TCP_PORT
    )


def timeout_profile_for(packet: PacketFacts) -> TimeoutProfile:
    """Choose which timeout profile applies to the packet."""

    if should_block_service_flow(packet):
        return BLOCK_TIMEOUT
    return FORWARDING_TIMEOUT


def blocked_match_fields(packet: PacketFacts) -> dict[str, object]:
    """Return the OpenFlow match fields for the blocked TCP service."""

    return {
        "in_port": packet.in_port,
        "eth_type": packet.eth_type,
        "ipv4_src": packet.ipv4_src,
        "ipv4_dst": packet.ipv4_dst,
        "ip_proto": packet.ip_proto,
        "tcp_dst": packet.tcp_dst,
    }


def forwarding_match_fields(packet: PacketFacts) -> dict[str, object]:
    """Return the OpenFlow match fields used for learned forwarding."""

    return {
        "in_port": packet.in_port,
        "eth_src": packet.src_mac,
        "eth_dst": packet.dst_mac,
    }


def demo_host_inventory() -> list[dict[str, str]]:
    """Static inventory used in documentation and sanity checks."""

    return [
        {
            "name": "h1",
            "ip": BLOCKED_CLIENT_IP,
            "mac": BLOCKED_CLIENT_MAC,
            "role": "blocked client for TCP/5001 to h4",
        },
        {
            "name": "h2",
            "ip": ALLOWED_CLIENT_IP,
            "mac": ALLOWED_CLIENT_MAC,
            "role": "allowed client for TCP/5001 to h4",
        },
        {
            "name": "h3",
            "ip": SERVER_A_IP,
            "mac": SERVER_A_MAC,
            "role": "general reachability and timeout demo peer",
        },
        {
            "name": "h4",
            "ip": PROTECTED_SERVER_IP,
            "mac": PROTECTED_SERVER_MAC,
            "role": "protected iperf server",
        },
    ]
