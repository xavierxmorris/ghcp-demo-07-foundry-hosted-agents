# Payment Methods

Which payment methods Contoso Payments supports and how they behave.

## Cards

Visa, Mastercard, American Express, Discover, and JCB. Cards support
authorisation and capture as separate steps, partial capture, and incremental
authorisation for hospitality and car rental.

Card authorisations expire after **7 days** if not captured. An expired
authorisation cannot be captured; create a new payment instead.

## 3-D Secure

3-D Secure (3DS2) adds a cardholder verification step. Contoso supports three
modes:

- `automatic` — 3DS is applied only when the issuer requires it or when Contoso
  risk scoring recommends it. This is the default.
- `any` — request 3DS on every transaction.
- `challenge` — force an interactive challenge, skipping frictionless flow.

A successful 3DS authentication shifts fraud liability to the issuer for
`fraudulent` disputes.

## Bank debits

- **SEPA Direct Debit** — euro only. Requires a signed mandate. Funds are not
  guaranteed: a customer can reclaim an authorised debit for **8 weeks** with no
  reason given, and up to **13 months** for an unauthorised debit.
- **ACH** — US dollars only. Returns can arrive up to **60 days** after
  settlement for unauthorised debits.
- **BACS** — pounds sterling only. Three business day clearing.

Because bank debits can be reversed long after settlement, do not ship
high-value goods until the debit has cleared its reversal window.

## Digital wallets

Apple Pay, Google Pay, and PayPal. Wallets carry a network token rather than a
raw card number, which lowers the fraud rate. Apple Pay and Google Pay
transactions are treated as authenticated and receive the same liability shift
as 3-D Secure.

Wallet payments cannot be partially captured. Capture the full amount or void.

## Buy now, pay later

Klarna, Afterpay, and Affirm. The provider pays the merchant in full at capture
and assumes the credit risk. BNPL payments **cannot be partially refunded** —
refund the full amount and create a new payment if needed.

## Method availability by country

| Method | Availability |
| --- | --- |
| Cards | All 46 supported countries |
| SEPA Direct Debit | Eurozone |
| ACH | United States |
| BACS | United Kingdom |
| Apple Pay / Google Pay | All supported countries |
| BNPL | 14 countries, varies by provider |

Availability is enforced at payment creation. Requesting an unavailable method
returns `400 payment_method_not_available_in_country`.
