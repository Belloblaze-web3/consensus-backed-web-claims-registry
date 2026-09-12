#!/usr/bin/env python3
"""Interact with a deployed ClaimRegistry using genlayer-py.

Install: pip install genlayer-py
Required environment variables:
  GENLAYER_CONTRACT_ADDRESS  deployed contract address
  GENLAYER_PRIVATE_KEY       account private key for writes
Optional:
  GENLAYER_NETWORK            localnet (default), studionet, or studio-dev
  GENLAYER_RPC_URL             override the selected chain RPC

Examples:
  python scripts/interact.py read --claim-id policy-2026
  python scripts/interact.py register --claim-id policy-2026 \
    --statement "The organization published a 2026 report." \
    --source-url https://example.org/reports \
    --criteria "Support only when an official source names the report."
  python scripts/interact.py resolve --claim-id policy-2026
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Any

from genlayer_py import create_account, create_client
from genlayer_py.chains import localnet, studionet


def make_client():
    network = os.getenv("GENLAYER_NETWORK", "localnet")
    chain = {"localnet": localnet, "studionet": studionet}.get(network)
    if chain is None:
        raise SystemExit(
            "Unsupported GENLAYER_NETWORK. Use localnet or studionet; "
            "configure studio-dev with the matching SDK release candidate."
        )

    private_key = os.getenv("GENLAYER_PRIVATE_KEY")
    account = create_account(private_key) if private_key else create_account()
    return create_client(chain=chain, account=account)


def contract_address() -> str:
    address = os.getenv("GENLAYER_CONTRACT_ADDRESS")
    if not address:
        raise SystemExit("GENLAYER_CONTRACT_ADDRESS is required")
    return address


def read_claim(client: Any, claim_id: str) -> None:
    result = client.read_contract(
        address=contract_address(),
        function_name="get_resolution",
        args=[claim_id],
    )
    print(result)


def submit_write(client: Any, function_name: str, args: list[Any]) -> None:
    """Submit a write and wait for the stored decision and finalization.

    For Consensus v0.6 networks, pass a fee profile through the SDK's
    estimate_transaction_fees API before calling this function. Localnet may
    accept a fee-less call depending on its configuration.
    """
    tx_hash = client.write_contract(
        address=contract_address(),
        function_name=function_name,
        args=args,
    )
    decision = client.wait_for_decision(tx_hash)
    print("Decision:", decision)
    finalized = client.wait_for_finalization(tx_hash)
    print("Finalized:", finalized)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register")
    register.add_argument("--claim-id", required=True)
    register.add_argument("--statement", required=True)
    register.add_argument("--source-url", action="append", required=True)
    register.add_argument("--criteria", required=True)

    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("--claim-id", required=True)

    read = subparsers.add_parser("read")
    read.add_argument("--claim-id", required=True)

    args = parser.parse_args()
    client = make_client()

    if args.command == "read":
        read_claim(client, args.claim_id)
    elif args.command == "register":
        submit_write(
            client,
            "register_claim",
            [args.claim_id, args.statement, args.source_url, args.criteria],
        )
    elif args.command == "resolve":
        timestamp = datetime.now(timezone.utc).isoformat()
        submit_write(client, "resolve_claim", [args.claim_id, timestamp])


if __name__ == "__main__":
    main()
