# Stubbed 100-item cloud batch: interrupted, resumed, and under 429s

No HTTP call leaves the machine: mistral_client.complete_prompt is stubbed per item.

Command:

    uv run pytest tests/test_quality_cli.py -p no:cacheprovider --no-cov -s -q -k "hundred_item_batch_interrupted or survives_429s"

Output (decisive lines):

    mistral partial: run hundred-fixed failed on item 'hundred-049' after 49 item(s) this invocation: retry budget exhausted after 0 retries; resume with --resume hundred-fixed
    evidence: first invocation 38 call(s), 37 rows; resume 63 call(s), 63 rows; items answered twice: 0; suite_accuracy 0.6600 (uninterrupted 0.6600)
    mistral partial: run hundred-interrupted failed on item 'hundred-037' after 37 item(s) this invocation: Mistral request failed; resume with --resume hundred-interrupted
    2 passed, 92 deselected in 17.17s
