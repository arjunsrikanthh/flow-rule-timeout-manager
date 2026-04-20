#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

sudo env PATH="$ROOT_DIR/.venv/bin:$PATH" PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}" "$ROOT_DIR/.venv/bin/mn" \
  --custom topology/timeout_topology.py \
  --topo flowtimeout \
  --controller remote,ip=127.0.0.1,port=6633 \
  --switch ovsk,protocols=OpenFlow13 \
  --link tc
