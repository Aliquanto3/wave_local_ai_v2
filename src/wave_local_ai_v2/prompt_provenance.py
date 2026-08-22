"""Endpoint and prompt-template identity: the constants and the consistency
rule the row-contract writer gate enforces.

`none` is legitimate only for the endpoint that sends a prompt byte-for-byte
with no chat structure applied. Any other endpoint applies some structure to
the prompt it sends, so a row that names that endpoint but claims no template
is inconsistent -- `row_contract.validate_row` refuses it.
"""

from __future__ import annotations

import hashlib

LOCAL_COMPLETION_ENDPOINT = "/completion"
TEMPLATE_ID_NONE = "none"
TEMPLATE_ID_MISTRAL_CHAT_MESSAGE = "mistral-chat-user-message"

# Documents the fixed structural wrapper the Mistral chat endpoint applies
# around the literal prompt text; the prompt text itself is not part of the
# hashed template.
_MISTRAL_CHAT_MESSAGE_TEMPLATE = '{"role": "user", "content": <prompt>}'

PROMPT_CAPTURE_CAPTURED = "captured"
PROMPT_CAPTURE_RECONSTRUCTED = "reconstructed"

# Endpoints that legitimately carry TEMPLATE_ID_NONE: they send the prompt
# byte-for-byte, with no chat structure applied.
RAW_ENDPOINTS = frozenset({LOCAL_COMPLETION_ENDPOINT})


def template_hash(template: str | None) -> str | None:
    """Return a stable content hash for `template`, or None if `template` is None."""
    if template is None:
        return None
    return hashlib.sha256(template.encode("utf-8")).hexdigest()


MISTRAL_CHAT_MESSAGE_HASH = template_hash(_MISTRAL_CHAT_MESSAGE_TEMPLATE)


def is_consistent(endpoint: str, prompt_template_id: str) -> bool:
    """Return False only when a non-raw endpoint claims TEMPLATE_ID_NONE."""
    return not (
        endpoint not in RAW_ENDPOINTS and prompt_template_id == TEMPLATE_ID_NONE
    )
