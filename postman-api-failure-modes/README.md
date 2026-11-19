# API failure modes and how I diagnose them

A Postman collection of deliberate API failures, each with a test that proves the failure
reproduces and a note on the symptom, what the response revealed, and the fix.

GitHub's REST API provides the realistic 401/403/400/404 cases. A small local server
(`mock/failure_lab.py`, standard library only) provides the ones that are hard to trigger on
demand against a real API: 409 duplicate create, 429 with `Retry-After`, and a slow response.

## Run it
1. Import `collections/` and `environments/` into Postman, **or** run `GITHUB_TOKEN=<read-only token> ./run.sh` (needs `npm i -g newman`).
2. Create a fine-grained, read-only GitHub token and put it in the `github_token` environment variable (type: secret). Never commit it.
3. In Postman, start the lab first: `python3 mock/failure_lab.py` (port 8099).

## Failure cases
| # | Case | Symptom | What the response revealed | Fix |
|---|------|---------|----------------------------|-----|
| F1 | 401 bad token | Every call fails | `Bad credentials` message | Regenerate token, check auth scheme and that the variable is populated |
| F2 | 403 missing permission | Authenticated call refused | Message names missing permission; 403 means known-but-not-allowed | Grant scope or use the owning account |
| F3 | 400 malformed JSON | POST that looks fine fails | Message about parsing JSON. Note: GitHub's /markdown accepted a truncated body (200), so strictness varies by endpoint | Validate body and Content-Type before blaming the API |
| F4 | 404 nonexistent | Resource "missing" | Same 404 appears for private resources without access | Check identifier, environment, and access |
| F5 | 409 duplicate create | Retry created a second object or errored | `already_exists` | Treat 409 as already done; use idempotency keys |
| F6 | 429 rate limited | Intermittent failures that clear alone | `Retry-After` header | Back off for that long, add jitter, stop bursts |
| F7 | Slow response / timeout | "It hangs" | Response time vs client timeout | Explicit timeouts; retry only idempotent calls |

## Status
- Lab cases (F5-F7 and the lab happy path) verified with newman.
- GitHub cases (F1-F4 and GitHub happy paths) are written against GitHub's documented behavior and
  need their first live run with a real token; adjust assertions to what you actually observe, then
  update this table.

## Troubleshooting (problems I actually hit)

**`Request Error: DNSLookup: EBADNAME {{github_base}}`**
- Symptom: a request fails with a DNS error that shows the literal text `{{github_base}}` instead of a hostname.
- What it revealed: the error looks like a network problem, but the variable was never replaced, so Postman tried to resolve the braces as a hostname. Hovering the variable in the URL bar showed whether it resolved.
- Cause: the environment was not selected when the request tab or collection run was opened. Importing an environment does not activate it.
- Fix: select the environment in the top-right dropdown **first**, then close the old collection/request tab and reopen it (or start a new run). Confirm by hovering the variable: it should show `https://api.github.com` with the source "Environment".

**Token field shows an orange dot / two `github_token` entries**
- Cause: a vault-linked duplicate of the variable existed next to the plain one.
- Fix: keep one `github_token` row (type: secret, full `github_pat_...` value) and delete the duplicate.

**Lab requests (F5-F7, "LAB" happy path) fail with connection refused**
- Cause: the local server is not running. Postman cannot run `.py` files; start it in a terminal with `python3 mock/failure_lab.py` and leave it open.
