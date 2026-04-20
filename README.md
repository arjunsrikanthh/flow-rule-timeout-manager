# Flow Rule Timeout Manager

This project is a Mininet and Ryu based SDN implementation of a flow rule timeout manager. The controller behaves like a small learning switch, but it also manages flow rule lifecycles with explicit `idle_timeout` and `hard_timeout` values. Normal traffic gets short-lived forwarding rules, while a blocked TCP service gets a higher-priority drop rule that also expires and can be reinstalled when the forbidden traffic appears again.

## Problem Statement

The goal is to implement controller-driven SDN behavior instead of relying only on Mininet CLI commands. The controller reacts to `packet_in` events, decides what to do with traffic, and installs OpenFlow rules with explicit lifecycles.

The chosen scenario is a `Flow Rule Timeout Manager` with four hosts and two OpenFlow switches:

- `h1` is blocked from reaching `h4` on TCP port `5001`
- `h2` is allowed to reach `h4` on TCP port `5001`
- `h1` and `h3` are used to show normal forwarding and timeout expiry

This gives two clear validation cases:

- allowed forwarding vs blocked access control
- active rule present vs expired rule reinstalled after timeout

## Topology and Design Choice

The topology has two switches connected back-to-back:

- `s1` connects `h1` and `h2`
- `s2` connects `h3` and `h4`
- `s1 <-> s2` is the inter-switch link

The topology is intentionally small. It is large enough to exercise controller-switch interaction across multiple switches without adding unnecessary routing complexity.

Static IP and MAC addresses are used so the flow matches stay predictable:

| Host | IP | MAC | Role |
| --- | --- | --- | --- |
| h1 | 10.0.0.1 | 00:00:00:00:00:01 | blocked client for `tcp/5001` to `h4` |
| h2 | 10.0.0.2 | 00:00:00:00:00:02 | allowed client for `tcp/5001` to `h4` |
| h3 | 10.0.0.3 | 00:00:00:00:00:03 | normal forwarding peer |
| h4 | 10.0.0.4 | 00:00:00:00:00:04 | protected iperf3 server |

## Controller Logic

The Ryu app is in `controller/timeout_manager.py`.

What it does:

- installs a table-miss rule so unknown traffic triggers `packet_in`
- learns source MAC to ingress port mappings like a learning switch
- floods only when the destination MAC is not known yet
- installs forwarding flows with:
  - `priority=100`
  - `idle_timeout=10`
  - `hard_timeout=40`
- installs a drop rule for `h1 -> h4 tcp/5001` with:
  - `priority=200`
  - `idle_timeout=0`
  - `hard_timeout=25`
- listens for `flow_removed` events to log when rules expire
- polls flow stats every 10 seconds for basic monitoring

The policy helper functions are isolated in `flow_timeout_manager/policy.py`. That keeps the rule decisions testable without Mininet or Ryu.

## Files

- `controller/timeout_manager.py`: Ryu controller with learning, blocking, timeouts, and stats logging
- `topology/timeout_topology.py`: Mininet topology
- `flow_timeout_manager/config.py`: host identities and timeout configuration
- `flow_timeout_manager/policy.py`: pure decision logic for match fields and timeouts
- `tests/test_policy.py`: regression tests for the pure policy layer
- `scripts/run_controller.sh`: starts the Ryu app
- `scripts/run_topology.sh`: starts Mininet with the custom topology
- `scripts/collect_evidence.sh`: dumps switch flow tables into `artifacts/`

## Setup

This repo runs from a local `.venv` in the project root. The controller start script uses `scripts/ryu_compat.py` because `ryu==4.34` still expects `eventlet.wsgi.ALREADY_HANDLED`, which is missing in newer `eventlet` releases.

Supported ways to run the project:

- Ubuntu or another Linux distribution with Mininet and Open vSwitch available
- Windows 10/11 through WSL2 with Ubuntu inside WSL
- native Windows is not supported for Mininet/Open vSwitch execution

Validated during development:

- Arch Linux
- Python 3.11
- Open vSwitch 3.7.0
- Mininet 2.3.0.dev6
- `iperf3`

## Ubuntu Quick Start

Clone the repository and enter it:

```bash
git clone https://github.com/arjunsrikanthh/flow-rule-timeout-manager.git
cd flow-rule-timeout-manager
```

Run the Ubuntu setup helper:

```bash
chmod +x scripts/setup_ubuntu.sh
./scripts/setup_ubuntu.sh
```

Start Open vSwitch:

```bash
sudo service openvswitch-switch start
sudo service openvswitch-switch status
```

Start the controller in one terminal:

```bash
./scripts/run_controller.sh
```

Start the topology in another terminal:

```bash
./scripts/run_topology.sh
```

## Windows WSL Quick Start

Install WSL2 with Ubuntu from an elevated PowerShell prompt:

```powershell
wsl --install -d Ubuntu-22.04
```

Inside the Ubuntu shell, clone the repo into the Linux filesystem, not `/mnt/c/...`:

```bash
git clone https://github.com/arjunsrikanthh/flow-rule-timeout-manager.git
cd flow-rule-timeout-manager
```

Run the WSL setup helper:

```bash
chmod +x windows/setup_wsl_ubuntu.sh
./windows/setup_wsl_ubuntu.sh
```

Start Open vSwitch inside WSL:

```bash
sudo service openvswitch-switch start
sudo service openvswitch-switch status
```

Start the controller in one WSL terminal:

```bash
./windows/run_controller_wsl.sh
```

Start the topology in another WSL terminal:

```bash
./windows/run_topology_wsl.sh
```

The WSL-specific scripts are thin wrappers around the same controller and topology used on Linux. The detailed WSL guide is in `windows/README.md`.

## Manual Setup

If you are not using the helper scripts, install these system packages first:

- `python3`
- `python3-venv`
- `python3-pip`
- `build-essential`
- `openvswitch-switch`
- `mininet`
- `iperf3`
- `tcpdump`
- `net-tools`
- `socat`
- `ethtool`

Then create the virtual environment and install Python dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt
```

## How To Run

Use the Linux scripts on Ubuntu:

```bash
./scripts/run_controller.sh
./scripts/run_topology.sh
```

Use the WSL wrappers on Windows+WSL:

```bash
./windows/run_controller_wsl.sh
./windows/run_topology_wsl.sh
```

If you want flow-table snapshots, run `./scripts/collect_evidence.sh` from another terminal while Mininet is still active.

## Platform Notes

- start the controller before starting Mininet, otherwise the switches will fail to connect to the remote controller
- keep the repository inside the Linux filesystem when using WSL, for example `/home/<user>/flow-rule-timeout-manager`
- if `mn` or Open vSwitch commands fail, confirm the Open vSwitch service is running before retrying
- use `iperf3`, not `iperf`, when testing TCP throughput

## Validation and Regression

The pure policy layer has unit tests:

```bash
python3 -m unittest discover -s tests -v
```

These tests check:

- the blocked traffic condition
- the timeout profile used for blocked and allowed traffic
- the match fields generated for flow installation
- the expected host inventory for the topology

## Syntax Verification

Python files can be checked directly from the local environment:

```bash
.venv/bin/python -m py_compile controller/timeout_manager.py topology/timeout_topology.py flow_timeout_manager/config.py flow_timeout_manager/policy.py tests/test_policy.py
```

## References

- Orange project guideline PDF shared for the assignment
- Ryu SDN Framework documentation
- Mininet documentation
- Open vSwitch `ovs-ofctl` manual
