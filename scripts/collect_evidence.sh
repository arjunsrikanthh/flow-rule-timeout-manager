#!/usr/bin/env bash
set -euo pipefail

STAMP="${1:-$(date +%Y%m%d_%H%M%S)}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR="$ROOT_DIR/artifacts/$STAMP"
mkdir -p "$ARTIFACT_DIR"

sudo ovs-ofctl -O OpenFlow13 dump-flows s1 > "$ARTIFACT_DIR/s1_flows.txt"
sudo ovs-ofctl -O OpenFlow13 dump-flows s2 > "$ARTIFACT_DIR/s2_flows.txt"

printf 'Saved flow table snapshots to %s\n' "$ARTIFACT_DIR"

