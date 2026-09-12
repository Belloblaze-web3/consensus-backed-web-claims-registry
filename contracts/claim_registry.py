# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Consensus-backed registry for claims grounded in public web evidence."""

from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class Claim:
    claim_id: str
    statement: str
    source_urls: list[str]
    criteria: str
    status: str
    verdict: str
    confidence: int
    rationale: str
    evidence_digest: str
    resolved_at: str


def normalize_result(result: dict) -> dict:
    """Validate and canonicalize the small decision object returned by the LLM."""
    if not isinstance(result, dict):
        raise ValueError("evidence extractor returned a non-object")
    verdict = str(result.get("verdict", "")).lower().strip()
    if verdict not in ("supported", "refuted", "uncertain"):
        raise ValueError("verdict must be supported, refuted, or uncertain")
    confidence = int(result.get("confidence", -1))
    if confidence < 0 or confidence > 100:
        raise ValueError("confidence must be between 0 and 100")
    digest = str(result.get("evidence_digest", "")).strip()
    if len(digest) < 8 or len(digest) > 128:
        raise ValueError("evidence_digest must be a compact stable identifier")
    rationale = str(result.get("rationale", "")).strip()
    if not rationale or len(rationale) > 1000:
        raise ValueError("rationale must be non-empty and at most 1000 characters")
    return {
        "verdict": verdict,
        "confidence": confidence,
        "evidence_digest": digest,
        "rationale": rationale,
    }


class ClaimRegistry(gl.Contract):
    """A reusable primitive for turning web-grounded judgments into state.

    The leader extracts a structured finding from the configured sources. Validators
    independently repeat the retrieval and extraction, then compare only stable
    decision fields. Prose is intentionally not part of equivalence.
    """

    claims: TreeMap[str, Claim]

    def __init__(self):
        pass

    @staticmethod
    def _validate_url(url: str) -> None:
        if not (url.startswith("https://") or url.startswith("http://")):
            raise ValueError("source URL must begin with http:// or https://")

    def _resolve_from_sources(
        self, statement: str, source_urls: list[str], criteria: str
    ) -> dict:
        def leader_fn() -> dict:
            evidence_parts: list[str] = []
            for url in source_urls:
                page = gl.nondet.web.get(url)
                evidence_parts.append("SOURCE: " + url + "\n" + page.body[:12000])
            prompt = f"""
You are an evidence extraction agent. Assess the claim below using ONLY the supplied
source excerpts and the decision criteria. Do not invent facts or use prior knowledge.

CLAIM: {statement}
CRITERIA: {criteria}
SOURCES:
{chr(10).join(evidence_parts)}

Return only JSON with exactly these keys:
- verdict: one of supported, refuted, uncertain
- confidence: integer from 0 to 100
- evidence_digest: a short deterministic digest-like label for the decisive evidence
- rationale: concise explanation, maximum 1000 characters

Use uncertain when the sources are insufficient, contradictory, stale, or ambiguous.
"""
            raw = gl.nondet.exec_prompt(prompt, response_format="json")
            return normalize_result(raw)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                independent = leader_fn()
                proposed = normalize_result(leader_result.calldata)
            except Exception:
                return False

            # Validators verify substance, not merely JSON shape. The verdict must
            # agree exactly and confidence may vary by 20 points across LLMs.
            # A digest mismatch is allowed because models may label the same evidence
            # differently; the independently fetched sources and verdict are decisive.
            return (
                proposed["verdict"] == independent["verdict"]
                and abs(proposed["confidence"] - independent["confidence"]) <= 20
            )

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    @gl.public.write
    def register_claim(
        self, claim_id: str, statement: str, source_urls: list[str], criteria: str
    ) -> None:
        if not claim_id or len(claim_id) > 96:
            raise ValueError("claim_id is required and must be at most 96 characters")
        if not statement or len(statement) > 2000:
            raise ValueError("statement is required and must be at most 2000 characters")
        if len(source_urls) < 1 or len(source_urls) > 5:
            raise ValueError("provide between 1 and 5 independent source URLs")
        if not criteria or len(criteria) > 2000:
            raise ValueError("criteria is required and must be at most 2000 characters")
        for url in source_urls:
            self._validate_url(url)
        if claim_id in self.claims:
            raise ValueError("claim_id already exists")
        self.claims[claim_id] = Claim(
            claim_id=claim_id,
            statement=statement,
            source_urls=source_urls,
            criteria=criteria,
            status="registered",
            verdict="",
            confidence=0,
            rationale="",
            evidence_digest="",
            resolved_at="",
        )

    @gl.public.write
    def resolve_claim(self, claim_id: str, resolved_at: str) -> None:
        if claim_id not in self.claims:
            raise ValueError("unknown claim_id")
        claim = self.claims[claim_id]
        if claim.status == "resolved":
            raise ValueError("claim is already resolved")
        result = self._resolve_from_sources(
            claim.statement, claim.source_urls, claim.criteria
        )
        claim.status = "resolved"
        claim.verdict = result["verdict"]
        claim.confidence = result["confidence"]
        claim.rationale = result["rationale"]
        claim.evidence_digest = result["evidence_digest"]
        claim.resolved_at = resolved_at

    @gl.public.view
    def get_claim(self, claim_id: str) -> Claim:
        if claim_id not in self.claims:
            raise ValueError("unknown claim_id")
        return self.claims[claim_id]

    @gl.public.view
    def get_claim_status(self, claim_id: str) -> str:
        if claim_id not in self.claims:
            raise ValueError("unknown claim_id")
        return self.claims[claim_id].status

    @gl.public.view
    def list_claim_ids(self) -> list[str]:
        return [claim_id for claim_id in self.claims]

    @gl.public.view
    def get_resolution(self, claim_id: str) -> dict:
        claim = self.get_claim(claim_id)
        return {
            "claim_id": claim.claim_id,
            "status": claim.status,
            "verdict": claim.verdict,
            "confidence": claim.confidence,
            "rationale": claim.rationale,
            "evidence_digest": claim.evidence_digest,
            "resolved_at": claim.resolved_at,
        }
