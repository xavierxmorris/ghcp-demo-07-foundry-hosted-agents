# Chargebacks and Disputes

How to respond when a customer disputes a payment with their bank.

## Dispute lifecycle

1. **Opened** — the issuing bank notifies Contoso. The disputed amount plus a
   **15.00 dispute fee** are immediately debited from the merchant balance.
2. **Evidence required** — you have a deadline to submit evidence.
3. **Under review** — the issuer evaluates the evidence.
4. **Won** or **Lost** — on a win, the amount and the dispute fee are returned.
   On a loss, both stay debited.

## Response deadlines

| Card network | Days to submit evidence |
| --- | --- |
| Visa | 20 |
| Mastercard | 21 |
| American Express | 20 |
| Discover | 20 |

The clock starts when the dispute is opened, not when you read the notification.
Contoso submits whatever evidence exists at the deadline, so partial evidence is
better than none. **A missed deadline is an automatic loss.**

## Evidence that wins

Ranked by observed effectiveness:

1. Proof of delivery with a signature or a tracking number matching the
   cardholder's billing address.
2. A signed contract or accepted terms of service showing the customer's
   agreement, with a timestamp and IP address.
3. Records of prior undisputed purchases by the same customer.
4. Communication logs showing the customer received the goods or service.
5. Photographs or screenshots of the delivered digital goods with access logs.

Evidence must be under **4.5 MB** per file and in PDF, PNG, or JPEG format.

## Reason codes

The most common reason codes and their meaning:

- `fraudulent` — the cardholder says they did not authorise the payment.
- `product_not_received` — the customer says nothing arrived.
- `product_unacceptable` — the goods arrived but were damaged or not as
  described.
- `duplicate` — the customer says they were charged twice.
- `subscription_cancelled` — the customer says they cancelled before renewal.

`fraudulent` disputes on payments that passed **3-D Secure** carry a liability
shift: the issuer, not the merchant, bears the loss. Always check whether 3DS
was used before spending time gathering evidence.

## Dispute rate thresholds

Card networks monitor the ratio of disputes to transactions. Above **0.9%** an
account enters a monitoring programme with monthly fines. Above **1.8%** the
account may be terminated. Contoso warns the account owner at **0.65%**.

## Preventing disputes

- Use a clear, recognisable billing descriptor — an unrecognised descriptor is
  the single largest driver of `fraudulent` disputes.
- Enable 3-D Secure for high-risk transactions to obtain the liability shift.
- Refund proactively: a refund issued before the dispute is opened costs the
  processing fee only, with no 15.00 dispute fee and no effect on the ratio.
