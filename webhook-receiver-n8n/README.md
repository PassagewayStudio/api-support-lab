# Webhook receiver lab (n8n + Postgres)

Simulates a provider that signs webhooks the way Svix / Standard Webhooks does (Gigs delivers webhooks through Svix),
and an n8n receiver that verifies signatures, logs every event, ignores duplicates and rejects bad ones.

## Layout
- `sender/send_webhook.py` - simulated provider with scenarios (ok, duplicate, bad-sig, stale, retry, out-of-order)
- `n8n/verify_signature.js` - verification logic (also pasted into the workflow's Code node)
- `n8n/webhook_receiver.workflow.json` - importable receiver workflow
- `n8n/alerting.workflow.json` - scheduled Slack alerting workflow
- `docker-compose.yml`, `.env.example` - separate lab stack
- `sql/schema.sql` - events table + partial unique index for idempotency
- `test/verify.test.js` - Python-signs / Node-verifies check
- `runbooks/break-it-runbook.md` - failures caused on purpose

## Setup
1. Copy `.env.example` to `.env` and fill in every value (database password, `WEBHOOK_SECRET`, Slack webhook URL). Never commit `.env`.
2. `docker compose up -d` starts a lab n8n (http://localhost:5679) and a lab Postgres. The schema in `sql/schema.sql` loads on first start.
3. In n8n, add a Postgres credential (host `lab-postgres`, port `5432`, values from `.env`), import `n8n/webhook_receiver.workflow.json` and `n8n/alerting.workflow.json`, attach the credential to the Postgres nodes, and activate both.
4. Send events: `set -a; source .env; set +a; python sender/send_webhook.py --url http://localhost:5679/webhook/gigs-lab --scenario ok`

## Alerting (n8n + Slack)
A second workflow, `n8n/alerting.workflow.json`, watches the `webhook_events` log and posts to Slack when deliveries are failing.

How it works:
1. A schedule trigger runs every 5 minutes.
2. A Postgres node counts rejected events (bad signature or stale timestamp) and duplicates from the last 5 minutes, and calculates seconds since the last successfully processed event.
3. If 3 or more events were rejected in that window, an HTTP Request node posts a summary to a Slack incoming webhook. The message includes the rejection count, duplicate count and a pointer to the runbook.
4. An optional "no events for 30+ minutes" alert exists but is off by default (`ALERT_ON_SILENCE=false`) so an idle lab does not send noise.

Design notes:
- The counting window equals the schedule interval, so one burst of failures produces one alert instead of repeating. Trade-off: a slow trickle of failures spread over several windows may stay under the threshold.
- The Slack webhook URL lives only in `.env` (`SLACK_WEBHOOK_URL`) and is passed to n8n as an environment variable. It is never stored in the workflow file or the repo.

Verified: a manual run and a scheduled run both posted to Slack after repeated bad-signature events, and a later scheduled run with no new failures correctly stayed quiet. The silence alert has not been tested.

## Status
Run and verified locally (n8n + Postgres in Docker, lab stack separate from any production system), 2026-11-18:
- Signed event accepted and logged (`processed`).
- Bad signature and stale timestamp rejected with 401 and logged (`rejected_signature`, `rejected_stale`).
- Duplicate and retried deliveries ignored: exactly one `processed` row per event id, later ones logged as `duplicate` and answered 200.
- Out-of-order events handled without assuming sequence.
- Alerting: a scheduled n8n workflow posts to Slack when 3+ events are rejected within 5 minutes (confirmed by a scheduled run, not only a manual one).
- Bug found and fixed during testing: the validity check branch let bad signatures through until failure-path tests exposed it (see runbook).

Not done: the slow-downstream scenario (runbook #5) and the optional "no events for N minutes" alert, which is built but off by default.
