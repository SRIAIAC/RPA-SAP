# Procurement — Rules & SOPs

1. **3-way match tolerance.** Invoice quantity must match GRN quantity exactly for
   items under hazard classification; for general MRO items a variance of up to
   2% (or 5 units, whichever is smaller) is auto-approved. Price variance is
   tolerated up to 3% or INR 5,000 per line, whichever is lower; anything beyond
   goes to the Invoice 3-Way Matching exception queue.
2. **PO approval limits.** Manager: up to INR 2,00,000. Senior Manager: up to
   INR 10,00,000. Department Head: up to INR 50,00,000. Anything above requires
   Admin/CFO sign-off outside the system.
3. **Vendor onboarding — KYC checklist.** GST certificate, PAN, cancelled cheque
   or bank letter, and a signed W-9/equivalent are mandatory before a vendor
   master can be created in SAP. Vendors supplying hazardous materials must also
   submit a current MSDS library reference.
4. **Insurance requirements.** Vendors performing on-site work (contractors,
   equipment rental) must carry General Liability cover of at least USD 1M and
   Workmen's Compensation as per local statute. Certificates expiring within 30
   days trigger an automatic renewal request; expired certificates block PO
   issuance until renewed.
5. **Duplicate vendor check.** Run on GSTIN + bank account number pair before
   creating any new vendor master; a match on either field alone is flagged for
   manual review, not auto-rejected (legitimate vendors sometimes share a
   holding-company GSTIN across entities).
6. **Blocked vendor handling.** A vendor blocked in SAP cannot receive a new PO
   even if a purchase requisition references them; the workflow must re-route to
   Procurement Manager for an alternate-vendor decision within 2 business days.
7. **Invoice submission channel.** Invoices must be submitted as PDF or a single
   scanned image attachment to procurement-invoices@company-oilgas.example (or
   the vendor portal). Invoices embedded only as email body text without an
   attached document are not accepted for OCR processing and must be
   re-submitted.
8. **Duplicate invoice detection.** An invoice is treated as a duplicate if the
   (vendor, invoice number) pair already exists in SAP FI, regardless of amount
   — vendors sometimes resend with corrected line items but keep the same
   invoice number by mistake, which itself is a compliance flag.
9. **Payment terms default.** Net 30 unless a vendor contract specifies
   otherwise; early-payment discount terms (e.g. 2/10 Net 30) are honored only
   if captured in the vendor master, not from invoice text alone.
10. **Purchase requisition budget check.** Every requisition is checked against
    the requesting cost center's remaining budget for the fiscal quarter before
    a PO is created; requisitions that would exceed budget are routed to the
    cost center owner for an override request.
11. **Supplier lead-time SLA.** Standard materials: 7 business days. Critical
    spares (rotating equipment, safety valves): expedited path with supplier
    portal escalation if lead time quoted exceeds 3 business days.
12. **Emergency/sole-source procurement.** Permitted only for safety-critical or
    production-stoppage situations, capped at INR 5,00,000, and requires a
    retroactive PO and Department Head justification memo within 48 hours.
13. **Contract renewal window.** Contracts are flagged for renewal review 30
    days before expiry; a contract with no assigned owner on file is escalated
    to the Department Head immediately rather than waiting for the 30-day
    trigger.
