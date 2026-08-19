# Sales & Distribution — Rules & SOPs

1. **Credit hold rules.** A sales order is automatically credit-blocked in SAP
   SD if the customer's outstanding balance plus the new order value exceeds
   their approved credit limit, or if any invoice is more than 60 days past
   due. Credit holds require Finance release before delivery creation.
2. **Order entry SLA.** Customer purchase orders received via email/portal are
   entered into SAP SD within 4 business hours during normal operations; rush
   orders (marked urgent by the customer) within 1 hour.
3. **Material availability check (ATP).** Available-to-Promise check is run
   against allocatable terminal/warehouse stock, not total book inventory, so
   in-transit or quality-hold stock is excluded from the promise.
4. **Pricing and contract precedence.** Contract pricing on file always
   overrides the standard price list; if a customer PO price disagrees with
   contract pricing by more than 1%, the order is flagged for commercial
   review before order creation.
5. **Delivery document requirements.** Every dispatch requires a Bill of
   Lading (crude/bulk product) or delivery note (packaged goods) matched to
   the SAP outbound delivery before the goods issue is posted.
6. **Customer master blocking.** A blocked customer master (compliance hold,
   sanctions screening flag, or unresolved dispute) prevents any new order
   creation regardless of credit status; blocks can only be lifted by Finance
   or Legal, not by Sales.
7. **Partial shipment policy.** Partial shipments are permitted only if the
   customer contract explicitly allows them; otherwise a short-pick on
   available stock holds the full order until complete availability.
8. **Return Material Authorization (RMA).** No returned product is accepted
   into inventory without a pre-issued RMA number referenced on the incoming
   shipment; unauthorized returns are held in a dock quarantine area.
9. **Export/regulatory documentation.** Cross-border shipments require
   customs documentation and, for regulated products, an end-user certificate
   on file before dispatch is scheduled.
10. **Order change cutoff.** Order changes (quantity, delivery date) are
    accepted up to 24 hours before scheduled dispatch; changes requested after
    cutoff require Distribution Manager approval due to staging impact.
11. **Claims and short-shipment disputes.** Customer-reported short shipments
    are investigated against the signed proof-of-delivery within 5 business
    days before any credit note is issued.
12. **Sales order confirmation notification.** Customer is notified of order
    confirmation and expected delivery window within 1 business hour of
    successful SAP SD order creation.
