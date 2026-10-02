# Licence and language-claim sources

Read on 2026-10-02 over HTTPS from huggingface.co (`/raw/<revision>/<file>` for
the text, `/api/models/<repo>/revision/<revision>` for the resolved sha). No
model file was downloaded. The fetched cards and licence files sit beside this
note, named `<owner>_<repo>.card.txt` (the `README.md` model card, stored as text so no formatter rewrites it) and `<owner>_<repo>.LICENSE`. The flagship card copy keeps lines 1-354 of
its 1072 (front matter, overview and the "Language" benchmark table); the
rest is serving and usage instructions, cut so its sample `OPENAI_API_KEY`
placeholder does not enter the repository.

| Roster entry | Revision read | Licence term and source | Language wording and source |
| --- | --- | --- | --- |
| `qwen3-0.6b-q8` | `23749fefcc72300e3a2ad315e1317431b06b590a` | Card front matter `license: apache-2.0`; repo `LICENSE` is the Apache License 2.0 text. Source: `https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/blob/23749fefcc72300e3a2ad315e1317431b06b590a/LICENSE` | "Support of 100+ languages and dialects with strong capabilities for multilingual instruction following and translation." (card line 21, markdown emphasis removed). No language is named. Source: the card `README.md` at the same revision |
| `qwen3-1.7b-q8` | `90862c4b9d2787eaed51d12237eafdfe7c5f6077` | Same as 0.6B (identical `LICENSE` bytes, md5 `e5ba20110b2e2fa01ab5bcffaa6deb47`). Source: `.../Qwen/Qwen3-1.7B-GGUF/blob/90862c4b.../LICENSE` | Same wording, card line 21 |
| `qwen3-4b-q4km` | `bc640142c66e1fdd12af0bd68f40445458f3869b` | Same as 0.6B (identical `LICENSE` bytes). Source: `.../Qwen/Qwen3-4B-GGUF/blob/bc640142.../LICENSE` | Same wording, card line 21 |
| `qwen3.6-35b-a3b-ud-iq4xs` | `main`, resolved to `a483e9e6cbd595906af30beda3187c2663a1118c` on 2026-10-02, the sha `docs/setup.md` records for the downloaded file | Card front matter `license: apache-2.0`, `license_link` to the upstream `Qwen/Qwen3.6-35B-A3B` LICENSE. The packager repo has no `LICENSE` file (HTTP 404), so the card is the repo's own statement. Upstream LICENSE at `Qwen/Qwen3.6-35B-A3B` `main` (`995ad96eacd98c81ed38be0c5b274b04031597b0`) is the Apache License 2.0 text (`Qwen_Qwen3.6-35B-A3B.LICENSE`). Source: `https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/blob/main/README.md` | Missing: the card states no supported language at all (its "Language" heading is a benchmark table). The entry records `languages: []` and no `statement` |

## What is recorded and why

- Licence id `Apache-2.0` (SPDX spelling of the cards' `apache-2.0`).
  `client_commercial_use: true`: Apache 2.0 grants a perpetual, worldwide,
  royalty-free licence to use and distribute, with no field-of-use or
  commercial restriction (section 2 of each fetched `LICENSE`).
- `languages: []` on all four entries. The dense cards claim "100+ languages
  and dialects" without naming one; the flagship card names none. Listing
  `en`, `fr` or `de` would infer the vendor's claim rather than read it.
  Any other vendor page (a release blog, the base model's card) is not the
  repository's card at its pinned revision, so none was used.
- Every term carries `read_on: 2026-10-02`. The flagship's terms are read at
  `main`; the read date stands in for the missing sha, as the open
  tech-debt row on its `main` pin already records.
