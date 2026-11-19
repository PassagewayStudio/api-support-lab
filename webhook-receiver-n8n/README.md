# Webhook receiver lab (n8n + Postgres)

Simulates a provider that signs webhooks the way Svix / Standard Webhooks does (Gigs delivers webhooks through Svix),
and an n8n receiver that verifies signatures, logs every event, ignores duplicates and rejects bad ones.

## Layout
- `sender/send_webhook.py` - simulated provider with scenarios (ok, duplicate, bad-sig, stale, retry, out-of-order)
- `n8n/verify_signature.js` - verification logic (also pasted into the workflow's Code node)
- `n8n/webhook_receiver.workflow.json` - importable workflow
- `sql/schema.sql` - events table + partial unique index for idempotency
- `test/verify.test.js` - Python-signs / Node-verifies check
- `runbooks/break-it-runbook.md` - failures caused on purpose

## Setup
1. Create a separate lab database (not the support bot's) and run `sql/schema.sql`.
2. Generate a lab secret (see `sender/send_webhook.py` docstring); set `WEBHOOK_SECRET` in the n8n container env and in your shell. Also set `NODE_FUNCTION_ALLOW_BUILTIN=crypto` and allow env access in Code nodes.
3. Import the workflow, attach a Postgres credential, activate it.
4. `WEBHOOK_SECRET=whsec_... python3 sender/send_webhook.py --url http://localhost:5678/webhook/gigs-lab --scenario ok`

## Status (honest)
- Verified here: signature logic (`node test/verify.test.js`, 6 cases pass).
- NOT yet run: the n8n workflow and SQL against a live n8n/Postgres. Treat it as a first draft: import, run each scenario,
  fix what breaks, then fill in "Observed" in the runbook. Not resume-ready until the done-criteria in the plan hold.
- Not built yet: Slack/email alerting node (plan step 6).
