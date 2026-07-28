# Refunds Policy

How Contoso Payments handles full refunds, partial refunds, and refund failures.

## Refund windows

A captured payment can be refunded for **180 days** from the capture date. After
180 days the original authorisation is expired and the refund must be issued as
a **payout** to the customer's bank account instead, which requires the customer
to supply bank details.

Authorised-but-not-captured payments are **voided**, not refunded. A void is
free and settles immediately. A refund of a captured payment carries the
original processing fee, which is **not** returned to the merchant.

## Partial refunds

A payment may be partially refunded up to **20 times**, and the sum of all
partial refunds may not exceed the captured amount. Each partial refund is a
separate object with its own `refund_id` and its own settlement timeline.

Partial refunds against a payment that used **split settlement** are deducted
proportionally from each recipient unless you pass an explicit
`allocation` array on the refund request.

## Timing and settlement

| Payment method | Funds return to customer |
| --- | --- |
| Card (Visa, Mastercard, Amex) | 5-10 business days |
| SEPA Direct Debit | 3-5 business days |
| ACH | 3-7 business days |
| Digital wallet | 1-3 business days |
| Bank transfer / payout | 1-2 business days |

The refund leaves the Contoso balance immediately, on the day it is created.
The delay above is the issuing bank's posting time, which Contoso cannot
accelerate.

## Refund failures

A refund can fail after being accepted. The most common causes are a closed
customer card account and a rejected SEPA mandate. When a refund fails the
funds are returned to the merchant balance and a `refund.failed` webhook fires.
Failed refunds must be reissued as a payout; retrying the same refund will fail
again for the same reason.

## Insufficient balance

If the merchant balance is lower than the refund amount, the refund is queued
with status `pending_funds` for up to **7 days**. Contoso retries automatically
each day. If the balance is still insufficient after 7 days the refund is
cancelled and a `refund.cancelled` webhook fires.
