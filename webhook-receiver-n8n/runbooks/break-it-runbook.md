# Webhook receiver runbook: failures I caused on purpose

Format: symptom -> how to confirm -> cause -> fix. Fill in "Observed" after each real run.

## 1. Bad signature (every event rejected with 401)
- Reproduce: `python3 sender/send_webhook.py --url $URL --scenario bad-sig`
- Confirm: `webhook_events` row with `status='rejected_signature'`; sender sees 401.
- Likely causes in real life: wrong/rotated secret; body modified before verifying (JSON re-serialised, so the bytes differ); Raw Body option off in n8n; proxy altering the body.
- Fix: verify against the raw bytes, re-copy the signing secret, check for middleware that rewrites the body.
- Observed (2026-11-18): sender got `401 {"error":"invalid_signature"}`; DB row `rejected_signature / bad_signature`. Response body is generic on purpose; the specific reason is only in the log.

## 2. Stale timestamp (valid signature, rejected anyway)
- Reproduce: `--scenario stale`. Confirm `reason='stale_timestamp'`.
- Observed (2026-11-18): sender got 401; DB row `rejected_stale / stale_timestamp`.
- Causes: clock drift on the receiver, or a replayed old message. Fix: sync time (NTP); keep the 5-minute tolerance, do not widen it to hide drift.

## 3. Duplicate delivery
- Reproduce: `--scenario duplicate` and `--scenario retry`.
- Confirm: first row `processed`, later rows `duplicate`, the downstream effect happened once.
- Observed (2026-11-18): duplicate and 3x retry gave one `processed` row and the rest `duplicate`, all answered 200.
- Why it happens: the provider retries when it did not see a 2xx in time. Answer duplicates with 200 so retries stop.

## 4. Out-of-order events
- Reproduce: `--scenario out-of-order` (activated arrives before created).
- Observed (2026-11-18): both events accepted as `processed` regardless of order; the receiver does not assume sequence.
- Gigs documents that order is not strictly guaranteed. Fix: do not assume sequence; decide state from the event contents or re-fetch the resource from the API when it matters.

## 5. Slow downstream (receiver times out)
- Reproduce: add a Wait node (e.g. 20 s) before the response, rerun `ok`.
- Symptom: the provider records a failure and retries even though your work finished. Fix: acknowledge fast (respond 200), do heavy work after; rely on idempotency for the retry.

## 6. Provider keeps failing (alerting)
- Repeated 5xx means the provider retries on its schedule and eventually marks messages failed; Gigs/Svix docs say endpoints are disabled after continuous failure over 5 days and alerts go out at most once a day, so add your own check (query in `sql/schema.sql`: no processed events in N minutes).

## Bug found while testing (2026-11-18)
- Symptom: bad-sig and stale events returned `200 processed` instead of 401, even though the Code node was verifying.
- Cause: the IF node ("Valid?") used a condition format its node version did not evaluate, so every event took the "valid" branch.
- How it was caught: the failure-path scenarios. The happy path alone passed and hid the bug.
- Fix: IF node set to a version that supports the condition format; table cleared; scenarios rerun and now return 401.
