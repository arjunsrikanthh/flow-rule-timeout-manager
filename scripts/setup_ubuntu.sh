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
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Ubuntu setup complete."
echo "Start OVS with: sudo service openvswitch-switch start"
echo "Run controller with: ./scripts/run_controller.sh"
echo "Run topology with: ./scripts/run_topology.sh"
