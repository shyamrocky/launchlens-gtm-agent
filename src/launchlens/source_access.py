"""Bounded anonymous checks for the two approved Drive PDFs. No retained file bytes."""
from datetime import datetime, timezone
import hashlib
import ssl
import urllib.error
import urllib.request

from launchlens.notion_tools import NoRedirect

# Same frozen identities as retrieval's verified indexed corpus. No Pinecone request.
from launchlens.retrieval import SOURCES
DRIVE_AUTHORITIES = {
    "1pJhRHdp5Oe6sk6aG5D_aP2MQY7gdHT3x": "public_product_facts",
    "1ThKUJxAmUn2Qf-rVmyVbDu2M5ZSqyCgS": "synthetic_product_intent",
}
APPROVED_PDFS = {file_id: SOURCES[authority][2] for file_id, authority in DRIVE_AUTHORITIES.items()}
MAX_PDF_BYTES = 1_000_000


def access_result(status="not_checked", *, detail=None, **facts):
    return {"status": status, "checked_at": None if status == "not_checked" else
            datetime.now(timezone.utc).isoformat(), "detail": detail, **facts}


def check_drive_pdf(file_id):
    """One GET, no cookies, OAuth, proxies, redirects or retry; exact approved digest."""
    expected = APPROVED_PDFS.get(file_id)
    if expected is None:
        return access_result("unavailable", detail="unapproved_file")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    request = urllib.request.Request(
        "https://drive.usercontent.google.com/download?id=" + file_id + "&export=download",
        headers={"Accept": "application/pdf, application/octet-stream"}, method="GET")
    try:
        with opener.open(request, timeout=20) as response:
            status = response.status
            raw = response.read(MAX_PDF_BYTES + 1)
        if status != 200:
            return access_result("unavailable", detail="http_rejected", http_status=status)
        if len(raw) > MAX_PDF_BYTES:
            return access_result("unavailable", detail="size_limit", http_status=status)
        digest = hashlib.sha256(raw).hexdigest()
        # Viewer/login HTML with HTTP200 is not a successful PDF read.
        if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-1024:]:
            return access_result("unavailable", detail="not_pdf", http_status=status)
        if digest != expected:
            return access_result("changed", detail="content_mismatch", http_status=status,
                sha256=digest, indexed_sha256=expected, bytes=len(raw))
        return access_result("accessible", detail="approved_pdf_sha256_match",
            http_status=status, sha256=digest, indexed_sha256=expected, bytes=len(raw))
    except urllib.error.HTTPError as error:
        return access_result("unavailable", detail="http_rejected", http_status=error.code)
    except (urllib.error.URLError, OSError, ValueError):
        return access_result("unavailable", detail="transport_failure")
