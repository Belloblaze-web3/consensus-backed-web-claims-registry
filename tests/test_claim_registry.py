"""Direct-mode tests; run with: pytest tests/ -v"""


def test_register_and_read(direct_deploy):
    contract = direct_deploy("contracts/claim_registry.py")
    contract.register_claim(
        "genlayer",
        "GenLayer uses validator consensus for non-deterministic outputs.",
        ["https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy"],
        "The source must explicitly describe leader proposals, validator checks, and majority acceptance.",
    )
    claim = contract.get_claim("genlayer")
    assert claim.status == "registered"
    assert contract.list_claim_ids() == ["genlayer"]


def test_resolution_stores_only_accepted_decision(direct_vm, direct_deploy):
    direct_vm.mock_web(
        r"docs\.genlayer\.com/understand-genlayer-protocol",
        {"status": 200, "body": "Leader proposes. Validators independently check. Majority accepts."},
    )
    direct_vm.mock_llm(
        r"GenLayer uses validator consensus",
        '{"verdict":"supported","confidence":88,"evidence_digest":"consensus-docs-v1","rationale":"The source describes leader proposals and validator majority checks."}',
    )
    contract = direct_deploy("contracts/claim_registry.py")
    contract.register_claim(
        "genlayer",
        "GenLayer uses validator consensus for non-deterministic outputs.",
        ["https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy"],
        "The source must describe validator consensus.",
    )
    contract.resolve_claim("genlayer", "2026-09-12T23:00:00Z")
    resolution = contract.get_resolution("genlayer")
    assert resolution["status"] == "resolved"
    assert resolution["verdict"] == "supported"
    assert resolution["confidence"] == 88
    assert resolution["evidence_digest"] == "consensus-docs-v1"


def test_bad_verdict_is_rejected_by_validator(direct_vm, direct_deploy):
    direct_vm.mock_web(r"example\.com/claim", {"status": 200, "body": "Evidence"})
    direct_vm.mock_llm(
        r"A claim with insufficient evidence",
        '{"verdict":"supported","confidence":90,"evidence_digest":"leader-answer","rationale":"leader"}',
    )
    contract = direct_deploy("contracts/claim_registry.py")
    contract.register_claim(
        "ambiguous",
        "A claim with insufficient evidence",
        ["https://example.com/claim"],
        "Use uncertain when the source is insufficient.",
    )
    contract.resolve_claim("ambiguous", "2026-09-12T23:00:00Z")
    # The test harness can swap the validator mock and inspect the actual EP vote.
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"example\.com/claim", {"status": 200, "body": "Evidence"})
    direct_vm.mock_llm(
        r"A claim with insufficient evidence",
        '{"verdict":"uncertain","confidence":20,"evidence_digest":"validator-answer","rationale":"validator"}',
    )
    assert direct_vm.run_validator() is False
