# Finance — Rules & SOPs

1. **Invoice posting gate.** No supplier invoice is posted in SAP FI without a
   successful 3-way match (PO, GRN, invoice) or an explicitly approved
   exception override from Procurement/Finance per the tolerance table in the
   Procurement KB.
2. **Expense policy limits.** Meals: up to INR 1,500/day domestic, USD 60/day
   international. Hotel: per the company travel band by grade. Any single
   receipt above INR 25,000 requires an itemized bill, not a card slip alone.
3. **Duplicate expense detection.** An expense claim is flagged duplicate if
   the (employee, amount, date, vendor) tuple matches an existing posted claim
   within a 5-day window, catching both accidental resubmission and
   split-claim abuse.
4. **Receipt requirements.** Missing itemized receipts for claims over INR
   5,000 block auto-approval and require manager attestation before posting.
5. **Fuel/lubricant reconciliation tolerance.** Variance between tank
   monitoring readings and SAP inventory balance is tolerated up to 1.5%
   (accounting for temperature-driven volume expansion); beyond that routes to
   the Finance Controller with the reconciliation report attached.
6. **Contract expiry financial review.** Contracts flagged for expiry within
   30 days are cross-checked for any outstanding accrual or committed spend
   before renewal or lapse is finalized.
7. **Payment run cutoff.** Vendor payment runs execute twice weekly (Tuesday
   and Friday); invoices approved after the Friday cutoff roll to the
   following Tuesday unless marked urgent by Department Head.
8. **Early payment discount capture.** Discount terms (e.g. 2/10 Net 30) are
   only honored if the invoice is both approved and scheduled within the
   discount window; the system does not retroactively apply a missed
   discount.
9. **Segregation of duties.** The person who approves a vendor invoice for
   payment may not also be the person who created that vendor master or
   modified its bank details within the prior 30 days.
10. **Bank detail change control.** Any change to a vendor's bank account
    details requires a callback verification to a phone number on file (not
    one supplied in the change request) before the change is applied, per
    anti-fraud procedure.
11. **Month-end close checklist.** Accruals for open POs/GRNs without a
    matching invoice are booked at month-end; reversed automatically upon
    actual invoice posting in the following period.
12. **Audit trail retention.** All posted financial documents, approval
    chains, and supporting attachments are retained for a minimum of 7 years
    per statutory requirement, with immutable audit logging of any
    post-posting corrections.
13. **Cost center budget enforcement.** Any transaction that would push a cost
    center beyond 100% of its approved quarterly budget requires the cost
    center owner's override before posting, logged in the audit trail.
