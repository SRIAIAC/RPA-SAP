# Warehouse Management — Rules & SOPs

1. **Putaway rules.** Hazardous materials are putaway only to designated
   hazmat-rated storage locations, segregated by compatibility class (e.g.
   oxidizers separated from flammables per SDS compatibility chart); the
   warehouse system rejects a putaway confirmation to an incompatible bin.
2. **Pick priority.** Work orders tagged "safety-critical" or "production
   down" outrank standard replenishment picks regardless of queue order;
   picking staff are alerted to priority picks via the handheld scanner.
3. **Bin capacity and weight limits.** Each storage bin has a maximum weight
   and volume defined in the warehouse system; a putaway exceeding either
   limit is blocked and rerouted to the next available compatible bin.
4. **Cross-docking eligibility.** Only non-hazardous, non-batch-managed
   materials with a confirmed outbound demand within 24 hours are eligible for
   cross-dock; everything else is putaway to standard storage first.
5. **Cycle count discrepancy escalation.** A bin-level discrepancy found during
   cycle count is recounted once by a different operator before any system
   adjustment is posted, to rule out a scanning error.
6. **Outbound shipment staging.** Shipments are staged a minimum of 2 hours
   before scheduled dispatch; staging area occupancy beyond 24 hours without
   dispatch triggers a review of the shipment's release status.
7. **Returns processing.** Returned materials are inspected within 1 business
   day of receipt and disposed to either released stock, quarantine, or scrap
   — they may not sit in the generic "returns" bin beyond 3 business days.
8. **Damaged goods handling.** Any damage identified during receiving is
   photographed, logged against the PO/ASN, and the carrier is notified within
   4 hours per the freight claim SLA.
9. **Warehouse lead-time SLA to Maintenance/Production.** Standard parts
   picked and staged within 4 business hours of a work-order material request;
   critical/emergency requests within 30 minutes during operating hours.
10. **Physical vs. system inventory reconciliation.** A full physical
    inventory is conducted annually; interim discrepancies greater than 1% of
    total SKU value trigger an unscheduled reconciliation for that storage
    section.
11. **Access control.** Hazmat and high-value storage areas require badge-
    logged access; the system flags any access event outside a scheduled pick
    or putaway task for security review.
12. **Equipment (forklift, crane) pre-use inspection.** Daily pre-use
    inspection checklist is mandatory before first use per shift; equipment
    failing inspection is tagged out and removed from the active pool
    immediately.
