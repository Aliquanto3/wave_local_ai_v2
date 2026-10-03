import json

import requests

url = "http://127.0.0.1:8091/v1/chat/completions"
msg = "Classify the following support message into exactly one of these categories: account, billing, other, technical. Reply with only the single category word, nothing else.\n\nMessage: My app crashes every time I open the settings page."
base = {
    "messages": [{"role": "user", "content": msg}],
    "max_tokens": 16,
    "temperature": 0,
    "chat_template_kwargs": {"enable_thinking": False},
}
out = {}
for name, extra in [
    ("no_grammar", {}),
    (
        "grammar_four_labels",
        {"grammar": 'root ::= "account" | "billing" | "other" | "technical"'},
    ),
    ("grammar_forcing_billing", {"grammar": 'root ::= "billing"'}),
]:
    r = requests.post(url, json={**base, **extra}, timeout=120)
    c = r.json()["choices"][0]
    out[name] = {
        "status": r.status_code,
        "content": c["message"]["content"],
        "finish_reason": c["finish_reason"],
    }
print(json.dumps(out, indent=2))
