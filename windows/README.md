# Windows Run Guide

This project is not meant to run as a native Windows Mininet setup.
The practical Windows route is:

- Windows 10/11
- WSL2
- Ubuntu inside WSL
- Open vSwitch, Mininet, and Ryu inside Ubuntu

If your friends follow this guide, they can run the same project on Windows through WSL2.

## 1. Windows Prerequisites

Open PowerShell as Administrator and run:

```powershell
wsl --install -d Ubuntu-22.04
```

Then restart Windows if asked.

After restart, open Ubuntu from the Start menu and create the Linux username and password.

Check WSL version:

```powershell
wsl --status
```

It should show WSL2 as the default version.

## 2. Copy Or Clone The Project

Inside Ubuntu, move to your home directory:

```bash
cd ~
```

Clone the repo if using git:

```bash
git clone https://github.com/arjunsrikanthh/flow-rule-timeout-manager.git
cd flow-rule-timeout-manager
```

If they already received the project as a zip, extract it and enter the project folder inside Ubuntu.

The top-level `README.md` also has a shorter Ubuntu/WSL quick-start section. This file is the more detailed WSL-specific guide.

Important:
- Keep the project inside the Linux filesystem, such as `/home/<user>/cn_orange`
- Do not run Mininet from `/mnt/c/...`

## 3. First-Time Ubuntu Setup In WSL

From the project root, run:

```bash
chmod +x windows/setup_wsl_ubuntu.sh
./windows/setup_wsl_ubuntu.sh
```

This installs:
- Python venv tools
- Open vSwitch
- Mininet
- iperf3
- tcpdump
- net-tools
- socat
- ethtool
- the Python dependencies in `requirements.txt`

## 4. Start Open vSwitch In WSL

Run:

```bash
sudo service openvswitch-switch start
sudo service openvswitch-switch status
```

If the service shows as started, continue.

## 5. Start The Project

Terminal 1:

```bash
./windows/run_controller_wsl.sh
```

Terminal 2:

```bash
./windows/run_topology_wsl.sh
```

## 6. Validation Commands

Run these from another WSL shell:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile controller/timeout_manager.py topology/timeout_topology.py flow_timeout_manager/config.py flow_timeout_manager/policy.py tests/test_policy.py scripts/ryu_compat.py
```

## 7. Common Issues

### `Unable to contact the remote controller`

Start the controller first, then start Mininet.

### `bash: iperf: command not found`

Use `iperf3`, not `iperf`.

Correct:

```bash
h4 iperf3 -s -p 5001 -D
h2 iperf3 -c 10.0.0.4 -p 5001 -t 5
```

### Open vSwitch not running

Run:

```bash
sudo service openvswitch-switch start
```

### Running from `/mnt/c/...`

Move the project into the Ubuntu home directory and run it there.

## 8. Files Added For Windows Users

- `windows/setup_wsl_ubuntu.sh`
- `windows/run_controller_wsl.sh`
- `windows/run_topology_wsl.sh`

These are WSL-specific helpers. The controller and topology code are the same project code used on Linux.
