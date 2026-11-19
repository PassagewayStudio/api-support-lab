// n8n "Code" node (Run Once for All Items). Verifies a Standard Webhooks / Svix signature.
// Requires on the n8n container:  NODE_FUNCTION_ALLOW_BUILTIN=crypto
// Requires the Webhook node option "Raw Body" = ON, so we sign the exact bytes received.
// Secret comes from the n8n env var WEBHOOK_SECRET ($env access must be allowed) - never paste it here.
const crypto = require('crypto');

function verify({ rawBody, headers, secret, nowSec, toleranceSec = 300 }) {
  const id = headers['webhook-id'];
  const ts = headers['webhook-timestamp'];
  const sigHeader = headers['webhook-signature'];
  if (!id || !ts || !sigHeader) return { ok: false, reason: 'missing_headers' };
  if (Math.abs(nowSec - Number(ts)) > toleranceSec) return { ok: false, reason: 'stale_timestamp' };
  const key = Buffer.from(secret.split('_')[1], 'base64');
  const expected = crypto.createHmac('sha256', key).update(`${id}.${ts}.${rawBody}`).digest();
  for (const part of sigHeader.split(' ')) {
    const [version, sig] = part.split(',');
    if (version !== 'v1' || !sig) continue;
    const got = Buffer.from(sig, 'base64');
    if (got.length === expected.length && crypto.timingSafeEqual(got, expected)) return { ok: true };
  }
  return { ok: false, reason: 'bad_signature' };
}

// ---- n8n entry point (skipped when this file is loaded by the test harness) ----
if (typeof $input !== 'undefined') {
  const item = $input.first();
  const raw = item.binary && item.binary.data
    ? Buffer.from(item.binary.data.data, 'base64').toString('utf8')
    : item.json.rawBody;
  const result = verify({
    rawBody: raw,
    headers: item.json.headers,
    secret: $env.WEBHOOK_SECRET,
    nowSec: Math.floor(Date.now() / 1000),
  });
  const h = item.json.headers;
  return [{ json: {
    valid: result.ok, reason: result.reason || null,
    event_id: h['webhook-id'] || null,
    request_id: h['x-request-id'] || h['webhook-id'] || null,
    payload_hash: crypto.createHash('sha256').update(raw || '').digest('hex'),
    event_type: (() => { try { return JSON.parse(raw).type; } catch (e) { return null; } })(),
    raw,
  } }];
}
module.exports = { verify };
