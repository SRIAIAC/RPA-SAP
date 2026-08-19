from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.models import Department, MailAttachment, MailMessage
from app.services.invoice_generator import INVOICES, generate_all_invoices

BASE_TIME = datetime(2026, 8, 15, 8, 0, 0)


def _t(hours: int) -> datetime:
    return BASE_TIME + timedelta(hours=hours)


# 15 emails: 5 real vendor invoice submissions (with attachment, tied to the
# generated PNGs in INVOICES) + 10 non-invoice emails spanning the 9
# departments, several deliberately tricky so the classifier must look past
# a bare "invoice"/"PO" keyword hit.
EMAILS = [
    # --- 5 real invoice submissions (attachment present) ---
    dict(
        sender="accounts@deccanvalves.example.com",
        sender_name="Deccan Valves & Fittings - Accounts",
        subject="Invoice INV-58231 for PO-100482 - Gate Valves & Gaskets",
        body=(
            "Dear Procurement Team,\n\nPlease find attached our invoice INV-58231 against your "
            "PO-100482 for the gate valve and gasket order shipped last week. Total amount due is "
            "INR 98,648.00, payment due Net 30 days from invoice date.\n\nKindly remit payment to "
            "our account on file.\n\nRegards,\nAccounts Team, Deccan Valves & Fittings Pvt Ltd"
        ),
        department=Department.PROCUREMENT,
        received_at=_t(1),
        invoice_filename="invoice_001_deccan_valves.png",
    ),
    dict(
        sender="billing@bharatpumps.example.com",
        sender_name="Bharat Pumps & Compressors - Billing",
        subject="INV-90144 | Pump Overhaul Kit & Seal Assembly - PO-100510",
        body=(
            "Hello,\n\nAttached is invoice INV-90144 covering the centrifugal pump overhaul kit and "
            "mechanical seal assembly delivered against PO-100510. Amount due: INR 4,18,900.00, "
            "Net 45 payment terms apply.\n\nThank you for your business.\n\nBharat Pumps & Compressors Ltd"
        ),
        department=Department.MAINTENANCE,
        received_at=_t(4),
        invoice_filename="invoice_002_bharat_pumps.png",
    ),
    dict(
        sender="invoices@gulfsafety.example.com",
        sender_name="Gulf Safety Equipment Trading - Invoicing",
        subject="Your Invoice INV-2201 - H2S Monitors & Gas Detectors",
        body=(
            "Dear Sir/Madam,\n\nPlease see attached invoice INV-2201 against PO-100455 for the H2S "
            "personal monitors and confined space gas detectors shipped to your site. Total: USD "
            "6,090.00. Payment due within 30 days.\n\nBest regards,\nGulf Safety Equipment Trading LLC"
        ),
        department=Department.HSE,
        received_at=_t(9),
        invoice_filename="invoice_003_gulf_safety.png",
    ),
    dict(
        sender="ap@krishnachemicals.example.com",
        sender_name="Krishna Specialty Chemicals - AP",
        subject="Invoice INV-77390 for chemical drums against PO-100521",
        body=(
            "Dear Team,\n\nAttached please find our invoice INV-77390 for the corrosion inhibitor "
            "and scale inhibitor drums delivered against PO-100521. Total amount payable is INR "
            "4,43,444.00, Net 30 terms.\n\nRegards,\nKrishna Specialty Chemicals Pvt Ltd"
        ),
        department=Department.MATERIAL_MANAGEMENT,
        received_at=_t(13),
        invoice_filename="invoice_004_krishna_chemicals.png",
    ),
    dict(
        sender="accounts@offshorelogistics.example.com",
        sender_name="Offshore Logistics & Freight Solutions - Accounts",
        subject="INV-33021 - Crane Barge Charter & Marine Survey, PO-100560",
        body=(
            "Hi,\n\nPlease find attached our invoice INV-33021 for the crane barge charter and "
            "marine survey/certification services rendered against PO-100560. Total due: INR "
            "11,85,900.00, Net 30 payment terms.\n\nThanks,\nOffshore Logistics & Freight Solutions"
        ),
        department=Department.SUPPLY_CHAIN_MANAGEMENT,
        received_at=_t(18),
        invoice_filename="invoice_005_offshore_logistics.png",
    ),
    # --- 10 non-invoice emails, several deliberately tricky ---
    dict(
        sender="rahul.verma@company-oilgas.example.com",
        sender_name="Rahul Verma",
        subject="Weekly maintenance status update - Unit 3",
        body=(
            "Hi team,\n\nQuick update on Unit 3 preventive maintenance: 8 of 10 scheduled PMs "
            "completed this week, 2 rescheduled due to parts availability. No open safety-critical "
            "work orders. Will follow up Monday.\n\nRahul"
        ),
        department=Department.MAINTENANCE,
        received_at=_t(2),
    ),
    dict(
        sender="farhan.ali@company-oilgas.example.com",
        sender_name="Farhan Ali",
        subject="HSE Alert: Minor chemical spill in Tank Farm B",
        body=(
            "Team,\n\nA minor spill occurred during transfer at Tank Farm B this morning. The "
            "estimated amount of chemical spilled was approximately 40 litres, fully contained "
            "within the bunded area. No injuries. Incident report being filed per SOP within the "
            "1-hour window.\n\nFarhan"
        ),
        department=Department.HSE,
        received_at=_t(3),
    ),
    dict(
        sender="newsletter@oilgasweekly.example.com",
        sender_name="Oil & Gas Weekly Newsletter",
        subject="This Week in Energy: Crude prices, refinery margins, and more",
        body=(
            "Your weekly digest of oil & gas industry news is here! Top stories: crude benchmark "
            "prices, refinery utilization rates, and upcoming industry conferences. Unsubscribe "
            "anytime.\n\n- The Oil & Gas Weekly Team"
        ),
        department=Department.PROCUREMENT,
        received_at=_t(5),
    ),
    dict(
        sender="neha.kapoor@company-oilgas.example.com",
        sender_name="Neha Kapoor",
        subject="Meeting request: Q3 vendor review",
        body=(
            "Hi all,\n\nCan we set up 30 minutes next Tuesday to review vendor performance scores "
            "for Q3? I'd like to cover the two vendors flagged for OTD below 85% before we "
            "schedule the formal review.\n\nThanks,\nNeha"
        ),
        department=Department.PROCUREMENT,
        received_at=_t(6),
    ),
    dict(
        sender="terminal.ops@portterminal.example.com",
        sender_name="Port Terminal Operations",
        subject="Shipment confirmation - Crude receipt vessel MT Horizon",
        body=(
            "This confirms MT Horizon has completed discharge at Berth 4. Shipment quantity per "
            "Bill of Lading: 45,200 BBL. Please confirm against your tank farm measurement and SAP "
            "MM receipt for reconciliation.\n\nPort Terminal Operations"
        ),
        department=Department.PRODUCTION,
        received_at=_t(7),
    ),
    dict(
        sender="vendor.sourcing@steelsupplyco.example.com",
        sender_name="Steel Supply Co - Sourcing",
        subject="Following up on PO #100499 - delivery schedule",
        body=(
            "Hello,\n\nJust checking in on PO #100499 for the structural steel order — can you "
            "confirm the delivery window is still Friday? No invoice yet, we'll send that once the "
            "goods receipt is confirmed on your end.\n\nSteel Supply Co"
        ),
        department=Department.WAREHOUSE_MANAGEMENT,
        received_at=_t(8),
    ),
    dict(
        sender="karan.singh@company-oilgas.example.com",
        sender_name="Karan Singh",
        subject="Reminder: month-end accrual review for open POs",
        body=(
            "Team,\n\nReminder that month-end close requires us to book accruals for all open POs "
            "without a matching invoice yet. Please send your department's list of open PO/GRN "
            "pairs by Thursday EOD.\n\nKaran"
        ),
        department=Department.FINANCE,
        received_at=_t(10),
    ),
    dict(
        sender="sanjay.gupta@company-oilgas.example.com",
        sender_name="Sanjay Gupta",
        subject="Daily production summary - Aug 15",
        body=(
            "Team,\n\nYesterday's production: 12,450 BBL actual vs 12,600 BBL planned (1.2% "
            "variance, within threshold). No anomaly flags. Well W-14 test scheduled for tomorrow "
            "per the 30-day cycle.\n\nSanjay"
        ),
        department=Department.PRODUCTION,
        received_at=_t(11),
    ),
    dict(
        sender="customer.orders@retailcorp.example.com",
        sender_name="RetailCorp Fuel Distribution",
        subject="Purchase order for diesel supply - August allocation",
        body=(
            "Hi,\n\nAttached is our purchase order for the August diesel allocation. Please confirm "
            "credit limit availability and expected delivery window. We'll settle payment per our "
            "standing Net 30 contract once product is received and invoiced by you separately.\n\n"
            "RetailCorp Fuel Distribution"
        ),
        department=Department.SALES_DISTRIBUTION,
        received_at=_t(15),
    ),
    dict(
        sender="deepa.joshi@company-oilgas.example.com",
        sender_name="Deepa Joshi",
        subject="Vendor lead-time SLA review - Q3 supply chain scorecard",
        body=(
            "Hi team,\n\nAttaching the Q3 supply chain scorecard for review (no invoice, this is the "
            "internal SLA tracker). Average vendor lead time improved to 12.4 days against the 14-day "
            "target. Two vendors remain on the watchlist for repeated late deliveries — flagging for "
            "next quarter's sourcing review.\n\nDeepa"
        ),
        department=Department.SUPPLY_CHAIN_MANAGEMENT,
        received_at=_t(17),
    ),
]


def seed_mailroom(session: Session) -> None:
    if session.exec(select(MailMessage)).first() is not None:
        return  # already seeded

    generate_all_invoices()
    spec_by_filename = {spec["filename"]: spec for spec in INVOICES}

    for email in EMAILS:
        has_attachment = "invoice_filename" in email
        msg = MailMessage(
            sender=email["sender"],
            sender_name=email["sender_name"],
            subject=email["subject"],
            body=email["body"],
            department=email["department"],
            received_at=email["received_at"],
            has_attachment=has_attachment,
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)

        if has_attachment:
            filename = email["invoice_filename"]
            spec = spec_by_filename[filename]
            from app.services.invoice_generator import DATA_DIR

            attachment = MailAttachment(
                mail_message_id=msg.id,
                filename=filename,
                content_type="image/png",
                file_path=str(DATA_DIR / filename),
            )
            session.add(attachment)

    session.commit()
