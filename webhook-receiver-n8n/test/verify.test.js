// Cross-language check: Python sender signs, Node verifier verifies.
const { execFileSync } = require('child_process');
const { verify } = require('../n8n/verify_signature.js');
const crypto = require('crypto');
const secret = 'whsec_' + crypto.randomBytes(24).toString('base64');
const py = `
import sys,json,time
sys.path.insert(0,'sender'); import send_webhook as s
sec,mid,ts,body=sys.argv[1:5]
print(s.sign(sec,mid,ts,body))`;
const now = Math.floor(Date.now() / 1000);
const body = '{"type":"com.gigs.sim.activated","data":{"subscription":"sub_1"}}';
const sig = execFileSync('python3', ['-c', py, secret, 'msg_1', String(now), body]).toString().trim();
const h = (o = {}) => ({ 'webhook-id': 'msg_1', 'webhook-timestamp': String(now), 'webhook-signature': sig, ...o });
const cases = [
  ['valid', verify({ rawBody: body, headers: h(), secret, nowSec: now }), true],
  ['tampered body', verify({ rawBody: body + ' ', headers: h(), secret, nowSec: now }), false],
  ['wrong secret', verify({ rawBody: body, headers: h(), secret: 'whsec_' + Buffer.from('x'.repeat(24)).toString('base64'), nowSec: now }), false],
  ['stale timestamp', verify({ rawBody: body, headers: h(), secret, nowSec: now + 600 }), false],
  ['missing header', verify({ rawBody: body, headers: h({ 'webhook-signature': undefined }), secret, nowSec: now }), false],
  ['multi-sig header', verify({ rawBody: body, headers: h({ 'webhook-signature': 'v1,AAAA ' + sig }), secret, nowSec: now }), true],
];
let fail = 0;
for (const [n, r, want] of cases) { const ok = r.ok === want; if (!ok) fail++; console.log(ok ? 'PASS' : 'FAIL', n, r.reason || ''); }
process.exit(fail ? 1 : 0);
