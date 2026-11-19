-- Lab database for the webhook receiver. Keep separate from the production support-bot DB.
CREATE TABLE IF NOT EXISTS webhook_events (
  id            BIGSERIAL PRIMARY KEY,
  event_id      TEXT        NOT NULL,           -- webhook-id header
  request_id    TEXT        NOT NULL,           -- for tracing (Project 3)
  event_type    TEXT,
  received_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  status        TEXT        NOT NULL,           -- processed | rejected_signature | rejected_stale | duplicate | error
  reason        TEXT,
  payload_hash  TEXT        NOT NULL,
  payload       JSONB
);
-- Idempotency: only ONE successful processing per event id.
CREATE UNIQUE INDEX IF NOT EXISTS uq_webhook_events_processed
  ON webhook_events (event_id) WHERE status = 'processed';
CREATE INDEX IF NOT EXISTS ix_webhook_events_received ON webhook_events (received_at DESC);

-- Handy checks
-- Duplicates that were ignored:        SELECT event_id, count(*) FROM webhook_events GROUP BY 1 HAVING count(*) > 1;
-- Rejections in the last hour:         SELECT status, reason, count(*) FROM webhook_events WHERE received_at > now() - interval '1 hour' AND status <> 'processed' GROUP BY 1,2;
-- Silence alert (no events 15 min):    SELECT now() - max(received_at) > interval '15 minutes' FROM webhook_events WHERE status = 'processed';
