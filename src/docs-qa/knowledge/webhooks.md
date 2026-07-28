# Webhooks

How Contoso Payments delivers asynchronous event notifications.

## Delivery and retries

Webhooks are delivered as `POST` requests with a JSON body. Your endpoint must
respond with a `2xx` status within **10 seconds**. Anything else — a non-2xx
status, a timeout, or a connection error — counts as a failure.

Failed deliveries are retried with exponential backoff over **72 hours**:

| Attempt | Delay after previous attempt |
| --- | --- |
| 1 | immediate |
| 2 | 5 seconds |
| 3 | 5 minutes |
| 4 | 30 minutes |
| 5 | 2 hours |
| 6 | 6 hours |
| 7 | 12 hours |
| 8 | 24 hours |

After the eighth attempt the event is moved to the dead letter queue and the
endpoint is marked `degraded`. An endpoint that fails every delivery for
**7 consecutive days** is automatically disabled and an email is sent to the
account owner.

## Signature verification

Every request carries a `Contoso-Signature` header:

```
Contoso-Signature: t=1735689600,v1=5257a869e7ecebeda32affa62cdca3fa...
```

Verify it by computing `HMAC-SHA256` over `"{t}.{raw_body}"` using your endpoint
signing secret, then comparing to `v1` with a constant-time comparison. Reject
any request whose timestamp `t` is more than **5 minutes** old — this is what
prevents replay attacks. Always verify against the **raw** request body; parsing
and re-serialising the JSON changes the bytes and breaks the signature.

## Ordering and duplicates

Webhooks are **not ordered**. A `payment.captured` event can arrive before the
`payment.authorized` event for the same payment. Always reconcile against the
object's current state rather than assuming arrival order.

Delivery is **at-least-once**, so your handler must be idempotent. Deduplicate
on the `event_id` field, which is stable across retries.

## Event catalogue

Commonly consumed events:

- `payment.authorized`, `payment.captured`, `payment.failed`
- `refund.created`, `refund.succeeded`, `refund.failed`, `refund.cancelled`
- `dispute.opened`, `dispute.evidence_required`, `dispute.won`, `dispute.lost`
- `payout.paid`, `payout.failed`

## Local testing

Use the Contoso CLI to forward events to a local server:

```bash
contoso listen --forward-to http://localhost:3000/webhooks
```

The CLI prints a temporary signing secret for the session. Test-mode events are
never mixed with live-mode events, and a test key can never receive live events.
