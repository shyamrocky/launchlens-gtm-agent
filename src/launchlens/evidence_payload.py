"""Lossless evidence fields for a future Pinecone response; standard library only.

No API client, file access, embedding, retrieval ranking or generation lives here.
"""

import hashlib
import json


class EvidenceError(ValueError):
    """Required evidence is missing, inconsistent or too large."""


def encode_packet(packet: dict) -> str:
    return json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def storage_fields(packet: dict) -> dict[str, str]:
    """Flat string fields, separate from the field chosen for embedding."""
    raw = encode_packet(packet)
    return {
        "chunk_id": packet["chunk_id"], "document_id": packet["document_id"],
        "authority": packet["authority"], "unit_id": packet["unit_id"],
        "product_id": packet["product_id"], "source_version": packet["document_version"],
        "source_sha256": packet["source_sha256"],
        "source_acceptance": packet["source_acceptance"]["status"],
        "chunk_preparation_status": packet["chunk_status"],
        "evidence_sha256": digest(raw), "evidence_json": raw,
    }


def metadata_bytes(fields: dict) -> int:
    # Escaped wire JSON is a conservative, inspectable bound for the flat fields.
    return len(json.dumps(fields, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))


def restore_evidence(fields: dict, *, expected_chunk_id: str, expected_authority: str) -> dict:
    """Decode a response's co-located evidence; fail closed, never read local files.

    expected_chunk_id comes from the hit ID; expected_authority from the caller's
    allowed evidence domain. The digest detects corruption, not malicious rewrites
    of both data and digest. Authorization/release trust remains the app's duty.
    """
    try:
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in fields.items()):
            raise EvidenceError("Evidence transport fields must be flat strings")
        raw = fields["evidence_json"]
        if digest(raw) != fields["evidence_sha256"]:
            raise EvidenceError("Evidence digest mismatch")
        packet = json.loads(raw)
        if encode_packet(packet) != raw:
            raise EvidenceError("Evidence serialization is not canonical")
        expected = storage_fields(packet)
        if fields != expected:
            raise EvidenceError("Evidence metadata and packet disagree")
        if packet["chunk_id"] != expected_chunk_id:
            raise EvidenceError("Retrieved evidence does not match the hit ID")
        if packet["authority"] != expected_authority:
            raise EvidenceError("Evidence authority is not allowed for this request")
        if expected_authority not in {"public_product_facts", "synthetic_product_intent"}:
            raise EvidenceError("Unknown evidence authority")
        return packet
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise EvidenceError("Complete evidence payload is missing or malformed") from error
