"""Static project configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TimeoutProfile:
    """Timeouts applied to OpenFlow rules."""

    idle_timeout: int
    hard_timeout: int


PROJECT_NAME = "Flow Rule Timeout Manager"
OPENFLOW_VERSION = "OpenFlow13"
CONTROLLER_PORT = 6633
MONITOR_INTERVAL = 10

FORWARDING_TIMEOUT = TimeoutProfile(idle_timeout=10, hard_timeout=40)
BLOCK_TIMEOUT = TimeoutProfile(idle_timeout=0, hard_timeout=25)

BLOCKED_CLIENT_IP = "10.0.0.1"
BLOCKED_CLIENT_MAC = "00:00:00:00:00:01"
ALLOWED_CLIENT_IP = "10.0.0.2"
ALLOWED_CLIENT_MAC = "00:00:00:00:00:02"
SERVER_A_IP = "10.0.0.3"
SERVER_A_MAC = "00:00:00:00:00:03"
PROTECTED_SERVER_IP = "10.0.0.4"
PROTECTED_SERVER_MAC = "00:00:00:00:00:04"

BLOCKED_TCP_PORT = 5001

