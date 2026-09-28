"""Thin wrapper over Hindsight's REST API for persistent incident memory.

Every call degrades gracefully: on timeout, network, or HTTP errors it logs a
warning and returns an empty result, so the agent keeps working without memory.
"""
import logging
from urllib.parse import quote

import requests

from config import HINDSIGHT_API_KEY, HINDSIGHT_BASE_URL

log = logging.getLogger(__name__)

BANK_ID = "sre-blast-radius"

# (connect, read) seconds. Retain runs LLM fact extraction server-side, so reads can be slow.
TIMEOUT = (5, 90)

_session = requests.Session()
_session.headers.update({"Authorization": f"Bearer {HINDSIGHT_API_KEY}"})


def _post(path, body):
    url = f"{HINDSIGHT_BASE_URL}{path}"
    try:
        resp = _session.post(url, json=body, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.Timeout:
        log.warning("Hindsight request timed out after %ss: %s", TIMEOUT, url)
    except requests.ConnectionError as exc:
        log.warning("Hindsight unreachable (%s): %s", url, exc)
    except requests.HTTPError:
        log.warning("Hindsight returned HTTP %s for %s: %s", resp.status_code, url, resp.text[:300])
    except ValueError:
        log.warning("Hindsight returned non-JSON response for %s", url)
    return None


def _bank_path(bank_id):
    return f"/v1/default/banks/{quote(bank_id, safe='')}/memories"


def retain_memory(bank_id, content, metadata=None, document_id=None, timestamp=None):
    """Store one memory (e.g. a postmortem). Returns True on success.

    Passing document_id makes the call idempotent: re-retaining the same id
    replaces the earlier version instead of duplicating it.
    """
    item = {"content": content}
    if metadata:
        item["metadata"] = {k: str(v) for k, v in metadata.items()}  # API requires string values
    if document_id:
        item["document_id"] = document_id
    if timestamp:
        item["timestamp"] = timestamp
    return _post(_bank_path(bank_id), {"items": [item]}) is not None


def recall_memory(bank_id, query_log, max_results=5):
    """Return up to max_results past memories that best match query_log (a raw error log).

    Each result is a dict with at least 'text', plus 'metadata' and 'document_id'
    when they were set at retain time. Returns [] if Hindsight is unavailable.
    """
    data = _post(f"{_bank_path(bank_id)}/recall", {"query": query_log, "budget": "mid"})
    return (data or {}).get("results", [])[:max_results]
