# API Authentication

How to authenticate against the Contoso Payments API.

## Key types

Contoso issues three credential types:

- **Secret API keys** (`sk_live_*`, `sk_test_*`) — full server-side access.
  Never expose one in a browser, mobile app, or public repository.
- **Publishable keys** (`pk_live_*`, `pk_test_*`) — safe to embed client-side.
  They can only tokenise payment details; they cannot move money.
- **Restricted keys** (`rk_live_*`) — scoped secret keys with an explicit
  allow-list of permissions. Use these for third-party integrations and for any
  service that only needs to read.

## Making an authenticated request

Pass the secret key as a bearer token:

```http
POST /v2/payments HTTP/1.1
Host: api.contoso-payments.example
Authorization: Bearer sk_live_...
Idempotency-Key: 8f14e45f-ea0d-4b1e-9c1a-2d3f4b5a6c7d
Content-Type: application/json
```

Requests without an `Authorization` header return `401 unauthorized`. Requests
with a valid key that lacks the required scope return `403 insufficient_scope`.

## Idempotency

Every mutating request accepts an `Idempotency-Key` header. Contoso stores the
result for **24 hours** and replays it for repeat requests with the same key.
This is how you safely retry after a network timeout without double-charging.
Idempotency keys are scoped per API key; reusing a key with a different request
body returns `409 idempotency_key_reuse`.

## Key rotation

Rotate secret keys from the dashboard or via the API. Rotation creates the new
key immediately and puts the old key into a grace period you choose, from
**0 to 72 hours**. Both keys work during the grace period, which lets you roll
a deployment without downtime. A key that is compromised should be revoked with
a **0 hour** grace period.

## Rate limits

The default limit is **100 requests per second** per API key, burstable to 300
for up to 10 seconds. Exceeding it returns `429 rate_limited` with a
`Retry-After` header in seconds. Read endpoints and write endpoints have
separate buckets. Rate limit increases are approved per account by support.

## IP allow-listing

Restricted keys support an optional IP allow-list of up to 20 CIDR ranges. A
request from outside the list returns `403 ip_not_allowed`. Allow-listing is not
available for publishable keys, because they are designed to run in browsers.
