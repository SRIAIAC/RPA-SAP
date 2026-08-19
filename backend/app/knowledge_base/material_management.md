# Material Management — Rules & SOPs

1. **Minimum stock threshold monitoring.** Every critical spare and MRO
   material has a defined minimum stock level in SAP MM; a scheduled check
   compares current stock against this threshold every 4 hours for critical
   rotating-equipment spares and daily for general MRO stock.
2. **Reorder point calculation.** Reorder point = (average daily consumption x
   supplier lead-time days) + safety stock. Safety stock for single-source
   critical spares is set at 1.5x normal buffer given limited substitution
   options.
3. **Material master data quality.** A material referenced in a maintenance
   notification but not found in the SAP material master blocks automated
   work-order material reservation; it is routed to Material Management for
   manual master-data creation within 2 business days.
4. **Cycle count frequency.** ABC classification governs count cadence: A-class
   (high value/criticality) items counted monthly, B-class quarterly, C-class
   semi-annually. Cycle count variance beyond 2% of book quantity for A-class
   items triggers an investigation before adjustment posting.
5. **Goods receipt matching.** Goods receipt quantity is matched against the PO
   line item; over-receipt beyond 5% requires supervisor approval before
   posting, under-receipt is accepted as partial and leaves the PO line open.
6. **Quarantine/hold stock.** Materials failing incoming inspection are moved
   to a quarantine storage location in SAP, not physically co-mingled with
   released stock, pending disposition (return to vendor, rework, scrap).
7. **Shelf-life / expiry tracking.** Batch-managed materials with shelf life
   (chemicals, seals, certain elastomers) are tracked with FEFO (first-expiry,
   first-out) issue logic; stock within 90 days of expiry is flagged for
   priority consumption or return.
8. **Purchase requisition auto-generation.** Auto-generated requisitions from
   the replenishment monitor require an approved supplier already on the
   material's source list; if none exists, the requisition routes to
   Procurement for sourcing rather than auto-creating a PO.
9. **Inter-plant stock transfer.** Transfers between plants require both a
   goods issue at source and confirmed goods receipt at destination within 5
   business days; transfers open beyond that window are flagged as in-transit
   exceptions.
10. **Consignment stock rules.** Vendor-owned consignment stock is tracked
    separately in SAP and only converted to company-owned stock at the moment
    of consumption (goods issue), which is also the trigger for vendor
    invoicing.
11. **Scrap and write-off approval.** Material write-offs under INR 50,000
    require Warehouse Supervisor approval; above that threshold require
    Department Head approval and a documented disposition reason.
12. **Serial/batch traceability.** All safety-critical spares (pressure relief
    valves, gaskets rated for sour service) must retain full batch/serial
    traceability from goods receipt through installation, recorded against the
    equipment's SAP PM object.
