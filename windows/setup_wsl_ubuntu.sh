#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

sudo apt update
sudo apt install -y \
  python3 \
  python3-venv \
  python3-pip \
  build-essential \
  openvswitch-switch \
  mininet \
  iperf3 \
  tcpdump \
  net-tools \
  socat \
  ethtool

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo
echo "WSL setup complete."
echo "Start OVS with: sudo service openvswitch-switch start"
echo "Run controller with: ./windows/run_controller_wsl.sh"
echo "Run topology with: ./windows/run_topology_wsl.sh"
