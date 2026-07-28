# Settlement and Payouts

When money actually reaches the merchant bank account.

## Settlement timeline

Funds move through three states:

1. **Authorised** — the customer's bank has reserved the amount. No money has
   moved. Authorisations expire after **7 days** for cards.
2. **Captured** — the amount is claimed and enters the Contoso balance as
   `pending`.
3. **Available** — the funds have cleared and can be paid out.

Default clearing time is **T+2 business days** from capture for card payments,
where T is the capture date. New accounts start on a **T+7** rolling reserve for
their first 90 days.

## Payout schedules

Three schedules are supported:

- **Daily** — a payout is created every business day for the full available
  balance.
- **Weekly** — a payout on a chosen weekday.
- **Manual** — you create payouts yourself via the API.

Payouts are only created on business days in the account's bank country.
A payout scheduled for a bank holiday is created on the next business day.
The minimum payout amount is **10.00** in the account's settlement currency;
balances below that roll into the next payout.

## Split settlement

A single payment can be split across up to **50 recipients**. Each split leg
settles on its own schedule and is visible as a separate balance transaction.
Platform fees are taken from the platform's leg, never from a recipient leg,
unless `fee_payer` is set explicitly on the split.

## Multi-currency

Contoso settles in **31 currencies**. If a payment currency differs from the
settlement currency, conversion happens at capture time using the Contoso FX
rate for that day, plus a **1.5%** conversion spread. Holding a balance in the
payment currency avoids the spread but requires a bank account in that currency.

## Failed payouts

A payout fails when the bank rejects it — a closed account, an incorrect IBAN,
or a name mismatch. Failed payouts return to the available balance within
**2 business days** and a `payout.failed` webhook fires with a `failure_code`.
Contoso does not retry a failed payout automatically; correct the bank details
and create a new payout.

## Reserves

Contoso may place a **rolling reserve** (a percentage of each payment held for a
fixed period) or a **fixed reserve** (a flat amount held indefinitely) on an
account with elevated dispute rates. Reserve terms are communicated by email at
least **14 days** before taking effect, except where fraud is suspected.
