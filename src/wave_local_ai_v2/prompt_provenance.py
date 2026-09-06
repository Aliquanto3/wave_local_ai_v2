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
LOCAL_CHAT_ENDPOINT = "/v1/chat/completions"
LOCAL_APPLY_TEMPLATE_ENDPOINT = "/apply-template"
TEMPLATE_ID_NONE = "none"
TEMPLATE_ID_MISTRAL_CHAT_MESSAGE = "mistral-chat-user-message"
TEMPLATE_ID_GOOGLE_CHAT_MESSAGE = "google-generatecontent-user-part"

# The local chat path's template id. Fixed, while its hash is not: unlike the
# two cloud ids above -- which name a wrapper this project spells out and
# hashes as a literal -- the local template is the model's own Jinja source,
# read from the server's `/props` at run time. So the id names the mechanism
# ("llama.cpp rendered this through the loaded model's chat template") and the
# per-row `prompt_template_hash` names which model's template it was. A
# per-entry id would restate `roster_entry_id`, which every row already
# carries.
TEMPLATE_ID_LLAMACPP_MODEL_CHAT = "llamacpp-model-chat-template"

# Documents the fixed structural wrapper the Mistral chat endpoint applies
# around the literal prompt text; the prompt text itself is not part of the
# hashed template.
_MISTRAL_CHAT_MESSAGE_TEMPLATE = '{"role": "user", "content": <prompt>}'

# Documents the fixed structural wrapper generateContent applies around the
# literal prompt text: {"role": "user", "parts": [{"text": <prompt>}]}, one
# entry in the "contents" list.
_GOOGLE_CHAT_MESSAGE_TEMPLATE = '{"role": "user", "parts": [{"text": <prompt>}]}'

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
GOOGLE_CHAT_MESSAGE_HASH = template_hash(_GOOGLE_CHAT_MESSAGE_TEMPLATE)


def is_consistent(endpoint: str, prompt_template_id: str) -> bool:
    """Return False only when a non-raw endpoint claims TEMPLATE_ID_NONE."""
    return not (
        endpoint not in RAW_ENDPOINTS and prompt_template_id == TEMPLATE_ID_NONE
    )
