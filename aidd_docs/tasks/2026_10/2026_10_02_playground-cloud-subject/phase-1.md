---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: The setting and the cloud path behind the chat interface

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/settings.py      ✏️ PlaygroundCloudSubject; PLAYGROUND_CLOUD_SUBJECT parsed, key read only when set
├── src/wave_local_ai_v2/demo_console.py  ✏️ CloudPlaygroundHolder in the Holder union; busy message names it
├── src/wave_local_ai_v2/playground.py    ✏️ start_cloud; cloud prepare/stream through the provider client with pacing and retry
├── src/wave_local_ai_v2/service.py       ✏️ session route accepts cloud_subject; options carry the subject (provider, model)
└── tests/test_settings.py                ✏️ setting unset by default, parsed, refused on a wrong model or a missing key
```

## Validation

- `uv run pytest tests/test_settings.py tests/test_playground.py`
