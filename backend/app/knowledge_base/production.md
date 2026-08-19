# Production — Rules & SOPs

1. **Daily production variance threshold.** Actual vs. planned output variance
   greater than 5% for any single well/facility triggers an automatic anomaly
   flag; variance greater than 10% requires same-shift notification to the
   Production Department Head.
2. **SCADA/Historian data gap handling.** A data gap longer than 15 minutes
   during a reporting window is logged as a data-quality exception, not
   silently interpolated; production figures for that window are marked
   "estimated" until manually confirmed.
3. **Production order confirmation window.** SAP PP production orders must be
   confirmed within 24 hours of shift end; unconfirmed orders past 48 hours are
   escalated to the Production Manager.
4. **Crude oil receipt reconciliation tolerance.** Variance between Terminal
   Management System, Tank Farm measurement, and SAP MM receipt quantity is
   auto-closed if within 0.3% (industry-standard custody transfer tolerance for
   crude oil, accounting for temperature/density correction). Variance beyond
   0.3% but under 0.5% requires Senior Manager sign-off; beyond 0.5% is a hard
   exception requiring a joint measurement review with the terminal operator.
5. **Tank gauging frequency.** Manual tank gauging cross-check is mandatory at
   least once per 24-hour period per active tank, independent of automated
   level sensors, to catch sensor drift.
6. **Well test frequency.** Each producing well must have an allocated well
   test at minimum every 30 days; wells flagged with anomalous GOR (gas-oil
   ratio) trends are tested every 7 days until the trend normalizes.
7. **Shut-in reporting.** Any unplanned well or facility shut-in exceeding 4
   hours must be logged with cause code and estimated deferred production
   volume within the same shift.
8. **Sales order credit gate.** No sales order is created in SAP SD until
   customer credit limit is confirmed available; blocked customer accounts
   route to Finance for release before order creation proceeds.
9. **Material availability check.** Sales orders for refined product require a
   real-time inventory check against the terminal's allocatable stock, not the
   book inventory figure, to avoid over-committing product in transit.
10. **Custody transfer documentation.** Every crude receipt or product dispatch
    requires a signed Bill of Lading / Certificate of Quantity matched against
    the SAP goods movement before financial posting.
11. **Anomaly-detection escalation.** Two consecutive shifts of anomaly-flagged
    output for the same well/facility auto-creates a maintenance inspection
    request rather than waiting for a manual review.
12. **Report distribution SLA.** The daily production report must be
    distributed via Power BI/email no later than 06:00 local time covering the
    prior 24-hour production day.
