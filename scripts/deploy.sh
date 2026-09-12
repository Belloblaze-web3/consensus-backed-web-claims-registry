#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/deploy.sh localnet
#   ./scripts/deploy.sh studionet
#   ./scripts/deploy.sh studio-dev
#
# The CLI reads fee-profile.json when deploying to fee-charging networks.
NETWORK="${1:-localnet}"
CONTRACT="${CONTRACT_PATH:-contracts/claim_registry.py}"

case "$NETWORK" in
  localnet|studionet|studio-dev|testnet-bradbury) ;;
  *) echo "Unsupported network: $NETWORK" >&2; exit 2 ;;
esac

echo "Selecting GenLayer network: $NETWORK"
genlayer network set "$NETWORK"
genlayer network info

echo "Deploying $CONTRACT"
genlayer deploy --contract "$CONTRACT" | tee deployment-output.txt

echo
cat <<'EOF'
Deployment output was saved to deployment-output.txt.
Record the Contract Address and Transaction Hash before running scripts/interact.py.
EOF
