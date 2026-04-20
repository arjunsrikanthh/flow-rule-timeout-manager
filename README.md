# Flow Rule Timeout Manager

This project is a Mininet and Ryu based SDN demo for the Orange assignment. The controller behaves like a small learning switch, but it also manages flow rule lifecycles with explicit `idle_timeout` and `hard_timeout` values. I used that timeout behavior to make the demo easy to explain: normal traffic gets short-lived forwarding rules, while a blocked TCP service gets a higher-priority drop rule that also expires and can be reinstalled when the forbidden traffic appears again.

## Problem Statement

The goal is to show controller-driven SDN behavior instead of relying only on Mininet CLI commands. The controller must react to `packet_in` events, decide what to do with traffic, install OpenFlow rules, and make the rule lifecycle visible during the demo.

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

I kept the topology small on purpose. It is large enough to show controller-switch interaction across multiple switches, but still simple enough to explain in a viva without getting lost in unnecessary routing logic.

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
- `scripts/demo_commands.txt`: quick demo script for the lab

## Setup

This repo is configured to run from the local `.venv` in the project root. The controller start script uses a small compatibility wrapper because `ryu==4.34` still expects `eventlet.wsgi.ALREADY_HANDLED`, which is missing in newer `eventlet` releases.

Validated environment for this repo:

- Arch Linux
- Python 3.11
- Open vSwitch 3.7.0
- Mininet 2.3.0.dev6
- `iperf3`

Project bootstrap:

```bash
~/.local/bin/uv venv --python 3.11 .venv
.venv/bin/python -m ensurepip --upgrade
.venv/bin/python -m pip install "setuptools<58" wheel
.venv/bin/python -m pip install --no-build-isolation -r requirements.txt
```

System packages needed for the live demo:

- `openvswitch`
- `iperf3`
- `tcpdump`
- `net-tools`
- `socat`
- `ethtool`

Before starting Mininet, make sure the Open vSwitch service is running:

```bash
sudo systemctl start openvswitch.service
sudo systemctl is-active openvswitch.service
```

## How To Run

Start the controller first:

```bash
./scripts/run_controller.sh
```

Start the topology in another terminal:

```bash
./scripts/run_topology.sh
```

You can also follow the ready-made command list in `scripts/demo_commands.txt`. If you want flow-table snapshots, run `./scripts/collect_evidence.sh` from another terminal while Mininet is still active.

## Demo Scenarios

### Scenario 1: Normal forwarding and timeout expiry

Commands:

```bash
mininet> h1 ping -c 3 h3
mininet> sh sudo ovs-ofctl -O OpenFlow13 dump-flows s1
mininet> sh sudo ovs-ofctl -O OpenFlow13 dump-flows s2
mininet> sh sleep 12
mininet> sh sudo ovs-ofctl -O OpenFlow13 dump-flows s1
mininet> h1 ping -c 1 h3
```

Expected behavior:

- the first ping triggers `packet_in` events and flow installation
- forwarding rules appear with idle and hard timeouts
- after 12 seconds of inactivity, the learned forwarding rule is removed by `idle_timeout`
- the next ping causes the controller to install the forwarding rule again

What to say in the demo:

- the switch is not acting alone
- the controller decides the match and the action
- timeout-based cleanup prevents stale learned entries from staying forever

### Scenario 2: Blocked vs allowed TCP service

Commands:

```bash
mininet> h4 iperf3 -s -p 5001 -D
mininet> h1 iperf3 -c 10.0.0.4 -p 5001 -t 5
mininet> h2 iperf3 -c 10.0.0.4 -p 5001 -t 5
mininet> sh sudo ovs-ofctl -O OpenFlow13 dump-flows s2
```

Expected behavior:

- `h1 -> h4 tcp/5001` fails because the controller installs a higher-priority drop rule
- `h2 -> h4 tcp/5001` succeeds and gets normal forwarding rules
- the flow table shows the blocked rule separately from forwarding entries

What to say in the demo:

- this is explicit SDN logic, not a hardcoded output
- the controller examines packet metadata and installs a targeted drop rule
- the block rule also has a hard timeout, so its lifecycle is visible too

## Performance Observation and Analysis

The project covers the rubric's basic observation section with ping, iperf3, flow tables, and controller logs.

### Latency

Use:

```bash
mininet> h1 ping -c 5 h3
```

Observation to record:

- first packet may take slightly longer because the controller has to process `packet_in` and install a rule
- later packets usually stabilize once the forwarding entry exists

### Throughput

Use:

```bash
mininet> h4 iperf3 -s -p 5001 -D
mininet> h2 iperf3 -c 10.0.0.4 -p 5001 -t 5
```

Observation to record:

- allowed traffic shows measurable throughput
- blocked traffic from `h1` shows failure instead of throughput

### Flow-table changes

Use:

```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
sudo ovs-ofctl -O OpenFlow13 dump-flows s2
```

Observation to record:

- forwarding entries carry timeout values and packet counters
- drop entries have higher priority than forwarding entries
- entries disappear after timeout and reappear when traffic returns

### Packet counts and statistics

The controller periodically requests flow stats and prints packet and byte counts. Those logs help explain which rules were actually used.

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

## Expected Output Summary

In a successful live run, you should see:

- controller logs showing switch connection, `packet_in`, flow installation, and `flow_removed`
- `ping` success between allowed hosts
- `iperf3` failure for `h1 -> h4 -p 5001`
- `iperf3` success for `h2 -> h4 -p 5001`
- `ovs-ofctl dump-flows` entries with timeouts, priorities, and counters

## Quick Validation Commands

These are the checks I use for a short re-test:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile controller/timeout_manager.py topology/timeout_topology.py flow_timeout_manager/config.py flow_timeout_manager/policy.py tests/test_policy.py
```

## Viva Notes

Questions you are likely to get:

1. Why use both `idle_timeout` and `hard_timeout`?
   `idle_timeout` removes inactive learned rules. `hard_timeout` guarantees cleanup even if a rule keeps matching traffic for too long.
2. Why is the block rule priority higher than the forwarding rule?
   The switch must match the access-control rule before the generic learned forwarding rule.
3. Why not do this only in Mininet CLI?
   The assignment asks for controller logic with packet handling and explicit OpenFlow flow installation.
4. What shows that the rule really expired?
   The controller receives `flow_removed`, and the flow-table dump changes after the timeout window.

## References

- Orange project guideline PDF shared for the assignment
- Ryu SDN Framework documentation
- Mininet documentation
- Open vSwitch `ovs-ofctl` manual
