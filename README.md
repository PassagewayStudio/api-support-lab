# API support lab
Hands-on projects for diagnosing API, webhook and provisioning failures. Everything here was built and run locally; the status of each part is stated plainly below.

## Projects
### `postman-api-failure-modes/` - Postman failure collection (verified)
A Postman collection with happy-path tests (status, schema, response time) and deliberate failures: 401 bad token, 403 missing permission, 400 malformed JSON, 404 missing resource, 409 duplicate create, 429 rate limit with Retry-After, and a slow response. Each failure has a note covering the symptom, what the response revealed, and the fix. A small local server produces the failures real APIs cannot create on demand. Includes a troubleshooting section for problems hit while building it.

### `webhook-receiver-n8n/` - Webhook receiver with alerting (verified)
An n8n workflow that receives webhooks signed the way Svix / Standard Webhooks signs them (the scheme Gigs uses), verifies the signature, rejects bad or stale requests with 401, logs every event to Postgres, ignores duplicates and retries so each event takes effect once, and tolerates out-of-order delivery. A second n8n workflow posts Slack alerts when rejections cluster. Runs in a separate Docker stack. A runbook documents each failure I caused on purpose, including a real bug the failure tests caught.

### `gigs-activation-runbook/` - SIM activation runbook (study document)
A "first five checks" runbook and escalation template for a failed SIM activation. Written from public developer documentation, not from operating the platform. Gigs does not offer self-serve test access, so nothing here claims hands-on use of their API.

## Not built
Request tracing with Grafana and Loki.

## Security
No secrets are stored in this repo. Tokens, webhook secrets and the Slack webhook URL come from environment variables and a git-ignored `.env`.
