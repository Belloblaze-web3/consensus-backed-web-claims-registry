# Consensus-Backed Web Claims Registry

A standalone GenLayer Intelligent Contract primitive for registering claims, grounding them in public web sources, and committing a consensus-accepted verdict on-chain.

## Why this primitive matters

Many applications need a durable answer to a question whose evidence lives outside the chain: whether a policy was published, whether a project meets a stated criterion, whether a public announcement occurred, or whether multiple sources support a factual assertion. Traditional contracts can store an answer, but they cannot independently retrieve and interpret the evidence. A centralized oracle can do that, but its answer is a single point of trust.

`ClaimRegistry` provides the reusable middle layer: a caller registers a claim with an explicit source allowlist and evaluation criteria; a GenLayer leader fetches and extracts a structured finding; validators independently repeat the retrieval and extraction; only an accepted result becomes contract state.

## Consensus design

The contract uses `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)`, rather than treating an LLM response as deterministic.

The leader returns four decision-bearing fields:

| Field | Purpose | Equivalence rule |
|---|---|---|
| `verdict` | `supported`, `refuted`, or `uncertain` | Exact match required |
| `confidence` | Integer from 0 to 100 | Absolute difference must be at most 20 |
| `evidence_digest` | Compact label for decisive evidence | Stored for auditability; not trusted as proof |
| `rationale` | Human-readable explanation | Stored but intentionally not compared |

Every validator independently fetches the configured URLs and repeats the extraction task. It does not merely validate JSON shape or inspect the leader's answer. This is important: the validator checks the substance of the claim using independent evidence. Wording can vary, so rationale and evidence labels are not part of equivalence. A mismatch in verdict rejects the proposal; modest confidence drift is tolerated because LLM scoring is subjective.

If the leader's result is rejected by the validator majority, GenLayer's protocol handles rotation or an undetermined transaction. The contract never writes a partially verified result.

## State model

Each claim progresses from `registered` to `resolved`. A claim includes its statement, source URL allowlist, criteria, final verdict, confidence, rationale, evidence digest, and caller-supplied resolution timestamp. URLs are capped at five and source excerpts are capped inside the non-deterministic block to reduce cost and avoid storing raw web pages on-chain.

The contract deliberately stores extracted evidence metadata rather than full source HTML. Builders can use the digest and source allowlist to reproduce or audit the resolution while keeping chain state compact.

## Usage

Deploy `contracts/claim_registry.py`, then call:

```python
registry.register_claim(
    "policy-2026",
    "The organization published a 2026 transparency report.",
    [
        "https://example.org/reports",
        "https://example.org/newsroom",
    ],
    "Mark supported only when an official source clearly identifies a 2026 transparency report. Use uncertain for missing, stale, or contradictory evidence.",
)
registry.resolve_claim("policy-2026", "2026-09-12T23:00:00Z")
registry.get_resolution("policy-2026")
```

Views include `get_claim`, `get_claim_status`, `get_resolution`, and `list_claim_ids`.

## Testing

The tests use the official `genlayer-test` direct-mode fixtures and mock web/LLM responses, so they run without Docker or a live Studio instance:

```bash
python3 -m pip install -r requirements.txt
pytest tests/ -v
```

Before deployment, run the same tests against Studio Mode to exercise real multi-validator behavior. The repository intentionally keeps consensus tests separate from any frontend or product flow so the contract can be reused by governance, compliance, research, and oracle-like applications.

## Safety and limitations

This is an evidence-resolution primitive, not a guarantee of truth. Public sources can be wrong, unavailable, manipulated, or updated after resolution. Callers should choose authoritative sources and criteria, treat `uncertain` as a first-class outcome, and avoid using a single resolution for irreversible high-value actions without an appeal or human review process. The contract does not make financial, legal, medical, or identity determinations.

## License

MIT

## References

- [GenLayer Intelligent Contracts](https://docs.genlayer.com/developers/intelligent-contracts/introduction)
- [The Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle)
- [Testing Intelligent Contracts](https://docs.genlayer.com/developers/intelligent-contracts/testing)
