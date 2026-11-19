#!/usr/bin/env python3
"""Simulated webhook provider, signing like Svix / Standard Webhooks (what Gigs uses).

Headers: webhook-id, webhook-timestamp, webhook-signature ("v1,<base64 hmac-sha256>")
Signed content: "<id>.<timestamp>.<raw body>"; key = base64-decoded part of "whsec_..." secret.

Secret is read from WEBHOOK_SECRET (never hardcode). Generate a lab secret with:
  python3 -c "import os,base64;print('whsec_'+base64.b64encode(os.urandom(24)).decode())"

Scenarios:
  ok            valid event
  duplicate     same webhook-id sent twice (second must be ignored)
  bad-sig       signature made with the wrong secret (must get 401)
  stale         timestamp 10 minutes old (must get 401)
  retry         resend same id N times, like a provider retrying after a 5xx
  out-of-order  sends "activated" before "created" for the same subscription
"""
import argparse, base64, hashlib, hmac, json, os, sys, time, urllib.request, urllib.error, uuid


def sign(secret, msg_id, ts, body):
    key = base64.b64decode(secret.split("_", 1)[1])
    mac = hmac.new(key, f"{msg_id}.{ts}.{body}".encode(), hashlib.sha256).digest()
    return "v1," + base64.b64encode(mac).decode()


def post(url, secret, event_type, msg_id=None, ts=None, data=None, sub="sub_lab_001"):
    msg_id = msg_id or f"msg_{uuid.uuid4().hex[:16]}"
    ts = str(ts if ts is not None else int(time.time()))
    body = json.dumps({"type": event_type, "data": data or {"subscription": sub}}, separators=(",", ":"))
    headers = {"Content-Type": "application/json", "webhook-id": msg_id,
               "webhook-timestamp": ts, "webhook-signature": sign(secret, msg_id, ts, body)}
    req = urllib.request.Request(url, data=body.encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            status, text = r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode()
    print(f"{event_type:34} id={msg_id} -> {status} {text[:120]}")
    return status


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--scenario", default="ok",
                   choices=["ok", "duplicate", "bad-sig", "stale", "retry", "out-of-order"])
    p.add_argument("--retries", type=int, default=3)
    a = p.parse_args()
    secret = os.environ.get("WEBHOOK_SECRET")
    if not secret or not secret.startswith("whsec_"):
        sys.exit("Set WEBHOOK_SECRET=whsec_... (see docstring)")
    if a.scenario == "ok":
        post(a.url, secret, "com.gigs.sim.activated")
    elif a.scenario == "duplicate":
        mid = f"msg_{uuid.uuid4().hex[:16]}"
        post(a.url, secret, "com.gigs.sim.activated", msg_id=mid)
        post(a.url, secret, "com.gigs.sim.activated", msg_id=mid)
    elif a.scenario == "bad-sig":
        wrong = "whsec_" + base64.b64encode(b"not-the-real-secret-0123456789ab").decode()
        post(a.url, wrong, "com.gigs.sim.activated")
    elif a.scenario == "stale":
        post(a.url, secret, "com.gigs.sim.activated", ts=int(time.time()) - 600)
    elif a.scenario == "retry":
        mid = f"msg_{uuid.uuid4().hex[:16]}"
        for i in range(a.retries):
            post(a.url, secret, "com.gigs.sim.activated", msg_id=mid)
            time.sleep(1 + i)
    elif a.scenario == "out-of-order":
        post(a.url, secret, "com.gigs.subscription.activated")
        post(a.url, secret, "com.gigs.subscription.created")


if __name__ == "__main__":
    main()
