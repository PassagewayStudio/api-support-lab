# SIM activation failed: first five checks (study runbook)

**Honest scope:** written from Gigs' public developer docs, not from operating their platform.
It shows how I would approach the problem and what I would verify, not prior telecom experience.
Sources are linked at the bottom; anything not stated in the docs is marked *(to verify)*.

## Background in plain words
A **subscription** ties a user to a plan and a SIM so their device gets connectivity. Activation is
**asynchronous**: you create the subscription, and the SIM becomes active later, after the network
provider finishes provisioning (the docs say this can take several minutes, longer for delayed test SIMs).
So "activation failed" usually means one of: the request was wrong, it is still in progress, the
state changed and you did not hear about it, or the provider side needs attention.

## First five checks
1. **The API request and response.** Find the original create-subscription call. Status code, error
   body, and which IDs were sent (plan, user, SIM, device). A 4xx means our request was wrong; a 5xx
   or timeout means retry safely (check whether a subscription was already created before retrying,
   to avoid a duplicate).
2. **Current state of the subscription and SIM.** GET the subscription and the SIM instead of trusting
   what the app showed. Is it `pending`, `active`, or ended? `activatedAt` is null until activation
   completes, so a null there on a recent request may simply be "not done yet".
3. **The event history.** The Gigs dashboard shows events per resource (subscription, SIM, user); each
   API request and scheduled change creates events, and the docs call them valuable for debugging.
   Read the sequence, and which event is missing.
4. **Webhook delivery.** Did our endpoint receive the event? Svix (which Gigs uses) logs each delivery
   attempt and its response; failed messages can be resent from the logs. Check our endpoint returned 2xx,
   verify we are not rejecting valid signatures, and remember ordering is not guaranteed, so an
   "activated" event can arrive before "created".
5. **SIM and device compatibility / provider side.** Is this a SIM type supported by the plan (pSIM vs eSIM),
   is the device compatible, and is the profile installed (eSIM profile events exist for installed/enabled)?
   Provider/network status and anything beyond our logs *(to verify with Gigs support)*.

## Escalating to engineering with a minimal repro
Include, in this order:
- **One-line summary:** "Subscription `sub_...` created at HH:MM UTC, still pending after N minutes; expected active within M."
- **Expected vs actual**, with timestamps.
- **Identifiers:** project, subscription, SIM (ICCID), user, device; event IDs and webhook message IDs.
- **The smallest request that reproduces it** (single curl, secrets redacted) and the exact response.
- **What I already ruled out:** request valid, webhook delivered, not a duplicate, state fetched live.
- **Frequency/impact:** one customer or many; started when; any change on our side.

## Reproducing with Gigs' test tooling (if I get a key)
Gigs documents fake network providers for testing: placeholder test SIM IDs (for example
`sim_test_psim_delayed_up_to_one_min`, `sim_test_esim_delayed_four_hours`) that mimic activation delays,
test phone numbers for porting scenarios (one is always declined first with a last-name decline code,
then succeeds after the info is updated), and a testing endpoint to simulate usage on an active test
subscription. Whether I can get a test API key without being a customer is *(to verify)*; if not, this
runbook stays docs-only and I do not claim hands-on use.

## Sources
- Events and webhooks: https://developers.gigs.com/docs/core/events/events-webhooks
- Testing overview and test SIMs: https://developers.gigs.com/docs/core/testing/overview.md , https://developers.gigs.com/docs/core/testing/test-sims
- SIM concepts: https://developers.gigs.com/docs/concepts/sims
- Subscriptions: https://developers.gigs.com/api/latest/core/subscriptions.md
- Events as debugging aid (help center): https://help.gigs.com/en/articles/2535618
