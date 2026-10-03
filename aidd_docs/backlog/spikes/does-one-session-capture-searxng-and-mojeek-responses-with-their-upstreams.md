---
type: spike
status: open
source: aidd_docs/backlog/spikes/which-two-search-tools-are-obtainable-archivable-and-what-each-sends-upstream.md
parents:
  - aidd_docs/backlog/stories/a-web-research-score-recomputes-offline-from-its-archived-search-responses.md
  - aidd_docs/backlog/stories/two-search-tools-answer-the-same-queries-and-each-row-names-its-tool.md
---

# Spike: Does one session capture SearXNG and Mojeek responses with their upstreams?

## Question

Run live in one operator session, do a SearXNG instance pinned at commit `783a094` (default engines minus `google cse`, JSON enabled) and the Mojeek Web Search API on its Business plan each return, for one fixed query in EN, FR and DE, a response that can be archived as returned; what error responses does each give when provoked; and which upstream hosts does the SearXNG instance actually contact?

## Decision

Whether the blocked spike `which-two-search-tools-are-obtainable-archivable-and-what-each-sends-upstream.md` resolves with SearXNG and Mojeek confirmed live (its Bounds fully met), so that order 9 and order 10 drop the live-capture part of their `Blocked:` lines; or, if either tool fails live, which shortfall that spike records instead (order 10's out-of-scope trigger).

## Bounds

- Evidence needed: the captures listed under "Stop when", produced by the procedure below. Everything the blocked spike already established at a dated retrieval (pricing, quota and terms pages, engine modules read at `783a094`, what each engine receives) is reused by reference and not re-read.
- Stop when: every capture the blocked spike's Bounds names exists in the capture directory: (1) per tool, one live response per language (EN, FR, DE) saved as returned, plus one no-result response; (2) per tool, its error responses as provoked: SearXNG's refused output format and any `unresponsive_engines` entries observed, Mojeek's invalid-key response and its response to a burst above its 10 queries per second; (3) for SearXNG, the engine list the running instance reports and the upstream request lines of its debug log; (4) for Mojeek, the account outcome (whether a sole individual could buy the Business plan, the price charged, the minimum top-up); (5) a manifest giving each body's SHA-256 and result URLs, and a key scan that finds no API key in the directory. Then hand the blocked spike to `aidd-pm:05-spike` (investigate, then conclude) with these captures.
- Tags: install + paid key + operator.

### Closes

- The blocked spike `aidd_docs/backlog/spikes/which-two-search-tools-are-obtainable-archivable-and-what-each-sends-upstream.md`: all three items of its "Remaining uncertainty" except republication, which Q114 (a) made moot.
- Order 9, `a-web-research-score-recomputes-offline-from-its-archived-search-responses.md`: the spike part of its `Blocked:` line (Follow-up steps 1 and 2, the SearXNG capture). Its `depends_on` on the judge-pair story and Q102 is untouched, so the story stays blocked through that.
- Order 10, `two-search-tools-answer-the-same-queries-and-each-row-names-its-tool.md`: the Mojeek account blocker (met as a prerequisite here) and the spike part of its `Blocked:` line (Follow-up steps 3 and 4). Its `depends_on` on order 9 is untouched.

### Choices and sources

- Runtime: Docker Desktop, already installed on the reference laptop (client `29.7.2`, a `docker-desktop` WSL 2 distro present; engine not running when checked 2026-10-03). The SearXNG docs call the container install "recommended for most users" and publish images at `docker.io/searxng/searxng` with `-p 8888:8080`, config at `/etc/searxng`, cache at `/var/cache/searxng` ([installation-docker](https://docs.searxng.org/admin/installation-docker.html), read 2026-10-03). A container pins the exact build by digest; a uv source install would need WSL (SearXNG targets Linux) and a pinned dependency set the repo does not ship, so it is the fallback only if Docker Desktop cannot run.
- Pinned image: tag `2026.9.23-783a09462`, index digest `sha256:5ea5f6804364e6075a44cb776a291a6ca1715380d653c8a4784ede436d5080cf` (amd64 `sha256:91617f595bec3043e51307647b4cb1342e19fa9544b74760440e3bb0ba2b3074`), pushed `2026-09-23T11:07:32Z` ([Docker Hub tag API](https://hub.docker.com/v2/repositories/searxng/searxng/tags/2026.9.23-783a09462), read 2026-10-03). Commit `783a094625ba29a8e348f4b43f37e460d1ca4cea` was committed `2026-09-23T11:00:51Z` ([GitHub API](https://api.github.com/repos/searxng/searxng/commits/783a094625ba29a8e348f4b43f37e460d1ca4cea), read 2026-10-03). The tag suffix is the commit prefix; the procedure checks the running version through `/config`.
- `settings.yml` keys, all at `783a094` (read 2026-10-03): `use_default_settings` with `engines: remove:` ([settings docs](https://docs.searxng.org/admin/settings/settings.html)); the engine's name is exactly `google cse` (`name: google cse`, `engine: google_cse` in [`searx/settings.yml`](https://raw.githubusercontent.com/searxng/searxng/783a094625ba29a8e348f4b43f37e460d1ca4cea/searx/settings.yml)); default `search.formats` is `[html]` and the webapp answers `flask.abort(403)` for any format not listed ([`searx/webapp.py`](https://raw.githubusercontent.com/searxng/searxng/783a094625ba29a8e348f4b43f37e460d1ca4cea/searx/webapp.py)); `general.debug` maps to `SEARXNG_DEBUG` and `server.secret_key` to `SEARXNG_SECRET`, and an environment variable overrides the file ([`searx/settings_defaults.py`](https://raw.githubusercontent.com/searxng/searxng/783a094625ba29a8e348f4b43f37e460d1ca4cea/searx/settings_defaults.py)). The engine `xprivo`, added by this very commit, ships `disabled: true` and `inactive: true`, so the default general set is still the one the blocked spike lists.
- Upstream-egress capture: the debug log. With `general.debug: true`, `searx/network/network.py` calls `log_response` after each upstream response (`if sxng_debug: await self.log_response(response)`), which logs `HTTP Request: {method} {url} "{http_version} {status}" ({content_type})` at DEBUG; a failed request logs `HTTP Request failed: {method} {url}` at WARNING ([`searx/network/network.py`](https://raw.githubusercontent.com/searxng/searxng/783a094625ba29a8e348f4b43f37e460d1ca4cea/searx/network/network.py), read 2026-10-03). Logging goes to the container's output, read with `docker logs`. The docs warn that debug is "intended for local development server" ([settings_general](https://docs.searxng.org/admin/settings/settings_general.html)), which fits a loopback-only, disposable instance.
- SearXNG JSON body keys: `query`, `results`, `answers`, `corrections`, `infoboxes`, `suggestions`, `unresponsive_engines` (`get_json_response` in [`searx/webutils.py`](https://raw.githubusercontent.com/searxng/searxng/783a094625ba29a8e348f4b43f37e460d1ca4cea/searx/webutils.py)). `/config` returns `version` and every loaded engine with `enabled`; `/healthz` returns `OK` (`searx/webapp.py`). Search parameters `q`, `language`, `format` ([search API](https://docs.searxng.org/dev/search_api.html)).
- Mojeek: request `GET https://www.mojeek.com/search` with `api_key`, `q`, `fmt=json`, `t`, `s` (start), `lb`, `rb` ([request parameters](https://www.mojeek.com/support/api/search/request_parameters.html)); the body is wrapped in `response` with `status` "OK or ERROR AND MESSAGE", the only documented error being `ERROR: Daily Limit Reached`; HTTP status codes are not documented ([JSON response](https://www.mojeek.com/support/api/search/json_response.html)). Business plan: "£3* CPM Pay as you Go", "10 Queries /sec", "400,000 Queries /day", "Up to 40" results, "*Excluding indirect taxes such as VAT"; FAQ: "You can store results on Business plan and optionally on the Enterprise plan" ([web search API](https://www.mojeek.com/services/search/web-search-api/), read 2026-10-03; the plan cards now also print "Storage Rights" on Startup, which the FAQ contradicts, so Business stays the plan to buy).

### Query texts (proposed)

No web-research suite or query item exists yet (order 9 Current state), so these are proposed, the same question in the three languages, the repo's own text, never client material. Percent-encoded as UTF-8 so `curl.exe` sends the bytes unchanged:

| Key | Text | Encoded `q` |
| --- | --- | --- |
| `en` | When did the EU Artificial Intelligence Act enter into force | `When%20did%20the%20EU%20Artificial%20Intelligence%20Act%20enter%20into%20force` |
| `fr` | Quand le règlement européen sur l'intelligence artificielle est-il entré en vigueur | `Quand%20le%20r%C3%A8glement%20europ%C3%A9en%20sur%20l%27intelligence%20artificielle%20est-il%20entr%C3%A9%20en%20vigueur` |
| `de` | Wann ist die KI-Verordnung der Europäischen Union in Kraft getreten | `Wann%20ist%20die%20KI-Verordnung%20der%20Europ%C3%A4ischen%20Union%20in%20Kraft%20getreten` |
| `empty` | zqxjvkwplmrtbnh7341 (no-result probe) | `zqxjvkwplmrtbnh7341` |

### Prerequisites

- Docker Desktop able to start on this Windows 11 Home laptop. Docker's own WSL 2 requirements list "Windows 11 64-bit: Enterprise, Pro, or Education version 23H2", while also stating "Windows Home or Education editions only allow you to run Linux containers" ([Windows install](https://docs.docker.com/desktop/setup/install/windows-install/), read 2026-10-03); the installed `docker-desktop` distro shows it has run here. Licence: Docker Desktop is free for "Small businesses (fewer than 250 employees AND less than $10 million in annual revenue)", "Personal use", "Education", "Non-commercial open source projects", and needs a paid subscription for "Professional use in larger organizations" ([Docker Desktop licence](https://docs.docker.com/subscription/desktop-license/), read 2026-10-03). The owner confirms which case applies before the session.
- Mojeek Business account with prepaid credits: owner act (Q112 (a)). Sign-up is not self-serve: every plan's button is "Contact", leading to `https://www.mojeek.com/about/contact?plan=business`, a form with name, email, subject and message and no company field, prefilled "Please sign me up and send me an API key for the business plan." Payment is "With Stripe on a pay-as-you-go credit system". The owner records the reply: whether an individual was accepted, the price charged, the minimum top-up.
- `MOJEEK_API_KEY`, entered at the prompt in step 5 and held only in the session's environment; never in a file, a command line typed in full, or the shell history.
- Network: the laptop's public IP is what DuckDuckGo, Brave, Wikipedia and Wikidata see (blocked spike, Evidence).

### Procedure

PowerShell 5.1 on Windows 11, run from the repository root. Every command is literal; only the capture date varies.

1. Capture directory. Raw bodies hold third-party titles and snippets; the repository is public, so they stay out of git (`raw/` ignored), consistent with Q114 (a). The manifest, settings, engine list and upstream lines carry no third-party text and are committed.

   ```powershell
   $ts  = { (Get-Date).ToUniversalTime().ToString("yyyyMMdd'T'HHmmss'Z'") }
   $cap = "aidd_docs\tasks\$(Get-Date -Format 'yyyy_MM')\$(Get-Date -Format 'yyyy_MM_dd')_search-tool-captures"
   New-Item -ItemType Directory -Force "$cap\searxng-config", "$cap\raw" | Out-Null
   Set-Content -Encoding ascii "$cap\.gitignore" 'raw/'
   $queries = [ordered]@{
     en    = 'When%20did%20the%20EU%20Artificial%20Intelligence%20Act%20enter%20into%20force'
     fr    = 'Quand%20le%20r%C3%A8glement%20europ%C3%A9en%20sur%20l%27intelligence%20artificielle%20est-il%20entr%C3%A9%20en%20vigueur'
     de    = 'Wann%20ist%20die%20KI-Verordnung%20der%20Europ%C3%A4ischen%20Union%20in%20Kraft%20getreten'
     empty = 'zqxjvkwplmrtbnh7341'
   }
   ```

2. `settings.yml` (complete; everything else comes from the defaults at `783a094`). ASCII, no BOM.

   ```powershell
   Set-Content -Encoding ascii "$cap\searxng-config\settings.yml" -Value @(
     'use_default_settings:',
     '  engines:',
     '    remove:',
     '      - google cse',
     'general:',
     '  debug: true',
     'search:',
     '  formats:',
     '    - html',
     '    - json'
   )
   ```

   The file this writes is the complete `settings.yml`:

   ```yaml
   use_default_settings:
     engines:
       remove:
         - google cse
   general:
     debug: true
   search:
     formats:
       - html
       - json
   ```

   The secret key is passed as `SEARXNG_SECRET` in step 3 so it never lands in the committed file.

3. Start Docker Desktop and the pinned instance, bound to loopback only.

   ```powershell
   Start-Process 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
   do { Start-Sleep 5; docker info --format '{{.ServerVersion}}' 2>$null } until ($LASTEXITCODE -eq 0)
   $img = 'docker.io/searxng/searxng:2026.9.23-783a09462@sha256:5ea5f6804364e6075a44cb776a291a6ca1715380d653c8a4784ede436d5080cf'
   $secret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
   docker run --name searxng-783a094 -d -p 127.0.0.1:8888:8080 -e "SEARXNG_SECRET=$secret" -v "$((Resolve-Path "$cap\searxng-config").Path):/etc/searxng/" $img
   for ($i = 0; $i -lt 30; $i++) { if ((curl.exe -s http://127.0.0.1:8888/healthz) -eq 'OK') { 'ready'; break }; Start-Sleep 2 }
   docker image inspect --format '{{index .RepoDigests 0}}' $img | Set-Content -Encoding ascii "$cap\searxng_image.txt"
   curl.exe -s -o "$cap\searxng_config_$(& $ts).json" http://127.0.0.1:8888/config
   ```

   If `ready` never prints, `docker logs searxng-783a094` shows why. Check the saved `/config`: `version` names `783a094`, and no engine is named `google cse`.

4. SearXNG captures: three languages, the no-result probe, then the refused-format probe; 10 s apart so each query's upstream lines group by timestamp. Then the debug log, its upstream lines and hosts.

   ```powershell
   foreach ($k in $queries.Keys) {
     $lang = if ($k -eq 'empty') { 'en' } else { $k }
     $s = & $ts
     curl.exe -s -D "$cap\raw\searxng_${k}_$s.headers.txt" -o "$cap\raw\searxng_${k}_$s.json" "http://127.0.0.1:8888/search?q=$($queries[$k])&format=json&language=$lang"
     Add-Content -Encoding ascii "$cap\requests.log" "$s searxng $k http://127.0.0.1:8888/search?q=$($queries[$k])&format=json&language=$lang"
     Start-Sleep 10
   }
   $s = & $ts
   curl.exe -s -D "$cap\searxng_format_refused_$s.headers.txt" -o NUL "http://127.0.0.1:8888/search?q=test&format=csv"
   cmd /c "docker logs --timestamps searxng-783a094 > $cap\raw\searxng_debug_$s.log 2>&1"
   Select-String -Path "$cap\raw\searxng_debug_$s.log" -Pattern 'HTTP Request' | ForEach-Object { $_.Line } | Set-Content -Encoding utf8 "$cap\searxng_upstream_requests.txt"
   Select-String -Path "$cap\raw\searxng_debug_$s.log" -Pattern 'HTTP Request(?: failed)?: \S+ (https?://[^/ "]+)' -AllMatches | ForEach-Object { $_.Matches } | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique | Set-Content -Encoding ascii "$cap\searxng_upstream_hosts.txt"
   ```

   The refused-format headers must show `403`. Lines logged before the first query's timestamp are startup traffic, not query egress; keep them, they are part of what the instance sends.

5. Mojeek captures: the key is read masked; the logged request URL carries `REDACTED` in its place.

   ```powershell
   $sec = Read-Host -AsSecureString 'Mojeek API key'
   $env:MOJEEK_API_KEY = [System.Net.NetworkCredential]::new('', $sec).Password
   $mj = [ordered]@{ en = 'lb=en&rb=GB'; fr = 'lb=fr&rb=FR'; de = 'lb=de&rb=DE'; empty = 'lb=en&rb=GB' }
   foreach ($k in $mj.Keys) {
     $s = & $ts
     $p = "q=$($queries[$k])&fmt=json&t=10&$($mj[$k])"
     curl.exe -s -D "$cap\raw\mojeek_${k}_$s.headers.txt" -o "$cap\raw\mojeek_${k}_$s.json" "https://www.mojeek.com/search?$p&api_key=$env:MOJEEK_API_KEY"
     Add-Content -Encoding ascii "$cap\requests.log" "$s mojeek $k https://www.mojeek.com/search?$p&api_key=REDACTED"
   }
   ```

6. Mojeek error probes. The documented `ERROR: Daily Limit Reached` cannot be provoked at a sane cost (400,000 queries a day at £3 per 1,000 is £1,200), so it is recorded as documented, not observed. Instead: an invalid key, and 15 parallel requests against the 10 per second limit (`s=1..15` makes 15 distinct valid requests; `%{urlnum}` is logged instead of the URL so the key is never written).

   ```powershell
   $s = & $ts
   curl.exe -s -D "$cap\raw\mojeek_badkey_$s.headers.txt" -o "$cap\raw\mojeek_badkey_$s.json" "https://www.mojeek.com/search?q=$($queries['en'])&fmt=json&t=10&api_key=INVALID-KEY-PROBE"
   Add-Content -Encoding ascii "$cap\requests.log" "$s mojeek badkey https://www.mojeek.com/search?q=$($queries['en'])&fmt=json&t=10&api_key=INVALID-KEY-PROBE"
   $s = & $ts
   curl.exe -s --parallel --parallel-max 15 -o "$cap\raw\mojeek_burst_${s}_#1.json" -w '%{urlnum} %{http_code} %{time_total}\n' "https://www.mojeek.com/search?q=$($queries['en'])&fmt=json&t=10&lb=en&rb=GB&s=[1-15]&api_key=$env:MOJEEK_API_KEY" | Set-Content -Encoding ascii "$cap\mojeek_burst_${s}_http_codes.txt"
   Add-Content -Encoding ascii "$cap\requests.log" "$s mojeek burst x15 https://www.mojeek.com/search?q=$($queries['en'])&fmt=json&t=10&lb=en&rb=GB&s=[1-15]&api_key=REDACTED"
   ```

   If no burst body carries a non-`OK` status and every code is `200`, that is the result: no rate-limit response at 15 parallel requests.

7. Manifest and key scan. The manifest holds per body its SHA-256, size, status, `unresponsive_engines` (SearXNG) and result URLs, no titles or snippets (Q114 (a)). The key scan must print nothing.

   ```powershell
   $rows = foreach ($f in Get-ChildItem "$cap\raw" -Filter *.json) {
     $body = Get-Content -Raw -Encoding UTF8 $f.FullName
     try { $j = $body | ConvertFrom-Json } catch { $j = $null }
     $r = if ($j -and $j.response) { $j.response } else { $j }
     [pscustomobject]@{
       file                 = $f.Name
       sha256               = (Get-FileHash -Algorithm SHA256 $f.FullName).Hash.ToLower()
       bytes                = $f.Length
       status               = if ($r -and $r.status) { $r.status } elseif ($j) { 'json' } else { 'not-json' }
       unresponsive_engines = @(if ($r -and $r.unresponsive_engines) { $r.unresponsive_engines | ForEach-Object { $_ -join ': ' } })
       result_urls          = @(if ($r -and $r.results) { $r.results | ForEach-Object { $_.url } })
     }
   }
   $rows | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 "$cap\manifest.json"
   Get-ChildItem -Recurse -File $cap | Select-String -SimpleMatch $env:MOJEEK_API_KEY | ForEach-Object { $_.Path }
   ```

8. Teardown.

   ```powershell
   docker rm -f searxng-783a094
   docker image rm $img
   Remove-Item Env:MOJEEK_API_KEY; Remove-Variable sec, secret
   ```

   Quit Docker Desktop from its tray icon if it is not otherwise needed. Record the Mojeek account outcome (prerequisite above) in `$cap\mojeek_account.md`.

### Time and cost

- Time: about 1 hour hands-on, excluding Mojeek's reply to the contact form (turnaround unstated): Docker Desktop start and image pull 5 to 10 min, SearXNG steps 2 to 4 about 10 min, Mojeek steps 5 and 6 about 5 min, manifest, key scan and checks about 10 min, teardown 2 min, then the blocked spike's investigate and conclude pass about 20 to 30 min.
- Cost: SearXNG £0. Mojeek billed queries, at most 4 (step 5) + 1 (invalid key, if billed at all) + 15 (burst) = 20; 20 x £3 / 1,000 = £0.06, excluding VAT (£0.072 at 20% UK VAT). The real outlay is Mojeek's minimum credit purchase, which is not published. Docker Desktop £0 under its free cases; otherwise a paid Docker subscription, price not read.

### Known gaps (left open, not invented)

- Whether a sole individual can buy the Mojeek Business plan, and its minimum credit purchase: no Mojeek page states either; the owner's contact-form exchange answers both.
- Mojeek's rate-limit response and its HTTP status codes are undocumented; step 6 observes what a 15-request burst returns, which may be no error at all. The invalid-key response is undocumented too; step 6 records it as returned.
- What SearXNG sends upstream beyond method and URL: `log_response` logs method, URL, status and content type only, so POST bodies, cookies and headers stay as the blocked spike read them from source. Observing them would need a TLS-intercepting proxy (`outgoing.proxies` and `outgoing.verify` exist in `settings.yml` at `783a094`); this spike does not specify one, since a row's egress field names destinations, not payloads.
- That the image was built from `783a094` rests on the tag suffix and on the push time (seven minutes after the commit); step 3 checks the running `version` through `/config`, but no image label was read.
- A free alternative runtime if Docker Desktop's licence does not cover this use (Docker Engine inside the Ubuntu WSL distro, or a source install): its commands were not sourced here.
