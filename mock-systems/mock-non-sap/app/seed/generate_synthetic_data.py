"""Deterministic synthetic data generator for the non-SAP systems layer of
PetroNova Energy Corporation. Fixed random seed (42), matching
mock-sap's generator exactly.

Coupling note: mock-sap and mock-non-sap are genuinely separate services
with separate databases (no shared code, no direct DB access between them —
that's the point of the provider/adapter architecture). Entities here
reference mock-sap records by business key (equipment_id, vendor_code,
material_code, customer_code, po_number) using the SAME numbering
convention and SAME fixed seed as mock-sap/app/seed/generate_synthetic_data.py,
so the business keys line up without either service calling the other at
seed time. If mock-sap's volumes/numbering ever change, this file's
_ID_RANGES below must be updated to match.
"""

import random
from datetime import date, datetime, timedelta

from faker import Faker
from sqlmodel import Session

from app.models import (
    CRMCustomer,
    CRMOrder,
    DocumentRecord,
    EmailMessage,
    LIMSResult,
    SCADAAlarm,
    SCADATelemetry,
    SupplierDocument,
    TankReading,
    TerminalReceipt,
    WMSInventory,
)

SEED = 42
DEPARTMENTS = ["Procurement", "Maintenance", "Finance", "HSE", "Production"]
TERMINALS = ["PetroNova Terminal North (TMN)", "PetroNova Terminal South (TMS)"]
WAREHOUSES = [f"PetroNova Warehouse {i} (WH{i})" for i in range(1, 6)]
TELEMETRY_PARAMETERS = [
    ("vibration", "mm/s", 2.0, 4.5),
    ("temperature", "°C", 40.0, 85.0),
    ("pressure", "bar", 5.0, 45.0),
    ("flow_rate", "m3/h", 50.0, 400.0),
    ("rpm", "rpm", 1200.0, 3600.0),
]

# Must match mock-sap/app/seed/generate_synthetic_data.py's numbering exactly.
_VOLUMES = {
    "full": dict(vendors=520, materials=1050, customers=320, equipment=520),
    "small": dict(vendors=60, materials=120, customers=40, equipment=60),
}

GOLDEN_EQUIPMENT_ID = "EQ-GOLDEN-PUMP-01"
GOLDEN_CRUDE_PO_NUMBER = "PO-GOLDEN-CRUDE"


def _mock_sap_ids(scale: str) -> dict[str, list[str]]:
    v = _VOLUMES.get(scale, _VOLUMES["full"])
    return {
        "vendor_codes": [f"V-{100000 + i}" for i in range(1, v["vendors"] + 1)],
        "material_codes": [f"MAT-{500000 + i}" for i in range(1, v["materials"] + 1)],
        "customer_codes": [f"C-{700000 + i}" for i in range(1, v["customers"] + 1)],
        "equipment_ids": [f"EQ-{100000 + i}" for i in range(1, v["equipment"] + 1)],
    }


def seed_all(session: Session, scale: str = "full") -> None:
    random.seed(SEED)
    fake = Faker()
    Faker.seed(SEED)
    ids = _mock_sap_ids(scale)
    is_full = scale == "full"

    _seed_scada(session, ids["equipment_ids"], n_readings_per_equipment=22 if is_full else 6)
    _seed_terminal(session, fake, n_receipts=220 if is_full else 25)
    _seed_wms(session, ids["material_codes"])
    _seed_crm(session, fake, ids["customer_codes"])
    _seed_supplier_portal(session, fake, ids["vendor_codes"])
    _seed_email(session, fake, n=150 if is_full else 20)
    _seed_lims(session, fake, n=320 if is_full else 30)
    _seed_documents(session, fake, n=220 if is_full else 20)
    _seed_golden_scenarios(session)

    session.commit()


def _seed_scada(session: Session, equipment_ids: list[str], n_readings_per_equipment: int) -> None:
    telemetry = []
    alarms = []
    for eq_id in equipment_ids:
        for _ in range(n_readings_per_equipment):
            parameter, unit, lo, hi = random.choice(TELEMETRY_PARAMETERS)
            value = round(random.uniform(lo, hi), 2)
            recorded_at = datetime.utcnow() - timedelta(hours=random.randint(0, 24 * 30))
            telemetry.append(
                SCADATelemetry(equipment_id=eq_id, parameter=parameter, value=value, unit=unit, recorded_at=recorded_at)
            )
        # ~8% of equipment also has a recent alarm on file.
        if random.random() < 0.08:
            parameter, unit, lo, hi = random.choice(TELEMETRY_PARAMETERS)
            threshold = round(hi * 0.9, 2)
            value = round(threshold * random.uniform(1.05, 1.6), 2)
            severity = random.choices(["critical", "warning", "info"], weights=[20, 50, 30])[0]
            alarms.append(
                SCADAAlarm(
                    equipment_id=eq_id, parameter=parameter, value=value, threshold=threshold,
                    severity=severity, acknowledged=random.random() < 0.7,
                    raised_at=datetime.utcnow() - timedelta(hours=random.randint(0, 24 * 14)),
                )
            )
    session.add_all(telemetry)
    session.add_all(alarms)
    session.flush()


def _seed_terminal(session: Session, fake, n_receipts: int) -> None:
    receipts = []
    readings = []
    for i in range(1, n_receipts + 1):
        terminal = random.choice(TERMINALS)
        receipts.append(
            TerminalReceipt(
                receipt_number=f"TR-{i:06d}",
                terminal=terminal,
                vessel_or_source=fake.company() + " Tanker",
                quantity_bbl=round(random.uniform(5000, 80000), 0),
                received_at=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            )
        )
    session.add_all(receipts)

    for i in range(1, n_receipts * 2 + 1):
        readings.append(
            TankReading(
                tank_id=f"TANK-{random.randint(1, 12):02d}",
                terminal=random.choice(TERMINALS),
                reading_date=date.today() - timedelta(days=random.randint(0, 365)),
                quantity_bbl=round(random.uniform(2000, 60000), 0),
                method=random.choice(["sensor", "manual_gauge"]),
            )
        )
    session.add_all(readings)
    session.flush()


def _seed_wms(session: Session, material_codes: list[str]) -> None:
    rows = []
    for material_code in material_codes:
        for warehouse in WAREHOUSES:
            if random.random() >= 0.35:  # not every material is stocked at every warehouse
                continue
            rows.append(
                WMSInventory(
                    material_code=material_code, warehouse=warehouse,
                    bin_location=f"{random.choice('ABCDEF')}-{random.randint(1,40):02d}-{random.randint(1,6)}",
                    quantity_on_hand=round(random.uniform(0, 5000), 0),
                )
            )
    session.add_all(rows)
    session.flush()


def _seed_crm(session: Session, fake, customer_codes: list[str]) -> None:
    customers = []
    for code in customer_codes:
        customers.append(
            CRMCustomer(
                customer_code=code, name=fake.company(),
                segment=random.choice(["Strategic", "Standard", "Spot"]),
                account_manager=fake.name(),
            )
        )
    session.add_all(customers)
    session.flush()

    orders = []
    for i, code in enumerate(customer_codes, start=1):
        for _ in range(random.randint(0, 3)):
            orders.append(
                CRMOrder(
                    order_number=f"CRM-{600000 + i}-{random.randint(1,999)}",
                    customer_code=code, amount=round(random.uniform(10000, 2_000_000), 2),
                    status=random.choice(["Open", "Won", "Lost"]),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 400)),
                )
            )
    session.add_all(orders)
    session.flush()


def _seed_supplier_portal(session: Session, fake, vendor_codes: list[str]) -> None:
    doc_types = ["GST Certificate", "Insurance Certificate", "MSDS", "Bank Letter", "PAN Card"]
    rows = []
    for code in vendor_codes:
        for doc_type in random.sample(doc_types, k=random.randint(1, 3)):
            rows.append(
                SupplierDocument(
                    vendor_code=code, document_type=doc_type,
                    filename=f"{code}_{doc_type.replace(' ', '_').lower()}.pdf",
                    status=random.choices(["Approved", "Pending", "Rejected"], weights=[75, 20, 5])[0],
                    uploaded_at=datetime.utcnow() - timedelta(days=random.randint(1, 500)),
                )
            )
    session.add_all(rows)
    session.flush()


def _seed_email(session: Session, fake, n: int) -> None:
    subjects = [
        "Weekly maintenance status update", "Shipment confirmation", "Meeting request",
        "PO follow-up", "Monthly newsletter", "Budget review reminder", "Training schedule",
        "Site safety walkthrough notes", "Vendor performance review", "Contract renewal reminder",
    ]
    rows = []
    for i in range(1, n + 1):
        rows.append(
            EmailMessage(
                sender=fake.company_email(), sender_name=fake.name(),
                subject=random.choice(subjects) + f" #{i}",
                body=fake.paragraph(nb_sentences=3),
                department=random.choice(DEPARTMENTS),
                has_attachment=random.random() < 0.3,
                received_at=datetime.utcnow() - timedelta(days=random.randint(0, 90)),
            )
        )
    session.add_all(rows)
    session.flush()


def _seed_lims(session: Session, fake, n: int) -> None:
    test_types = [("Sulfur Content", "%wt", 0.1, 3.0), ("API Gravity", "°API", 20, 45), ("Water Content", "%vol", 0, 1.5)]
    rows = []
    for i in range(1, n + 1):
        test_type, unit, lo, hi = random.choice(test_types)
        value = round(random.uniform(lo, hi), 3)
        rows.append(
            LIMSResult(
                sample_id=f"SMP-{600000 + i}", test_type=test_type, result_value=value, unit=unit,
                pass_fail=random.choices(["Pass", "Fail"], weights=[92, 8])[0],
                location=random.choice(TERMINALS),
                tested_at=datetime.utcnow() - timedelta(days=random.randint(0, 200)),
            )
        )
    session.add_all(rows)
    session.flush()


def _seed_documents(session: Session, fake, n: int) -> None:
    categories = ["Invoice", "Vendor KYC", "Contract", "Customer Order", "Expense Receipt", "HSE Report"]
    rows = []
    for i in range(1, n + 1):
        rows.append(
            DocumentRecord(
                document_id=f"DOC-{700000 + i}", title=fake.catch_phrase(),
                category=random.choice(categories), file_type=random.choice(["pdf", "png", "docx"]),
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 500)),
            )
        )
    session.add_all(rows)
    session.flush()


def _seed_golden_scenarios(session: Session) -> None:
    """Hand-crafted fixtures for the Maintenance and Crude Reconciliation
    golden demo scenarios — fixed, never randomly generated."""
    # Maintenance: pump vibration well over threshold -> Emergency work order.
    session.add(
        SCADAAlarm(
            equipment_id=GOLDEN_EQUIPMENT_ID, parameter="vibration", value=12.0, threshold=5.0,
            severity="critical", acknowledged=False,
        )
    )
    session.add(
        SCADATelemetry(equipment_id=GOLDEN_EQUIPMENT_ID, parameter="vibration", value=12.0, unit="mm/s")
    )

    # Crude reconciliation: Terminal/Tank readings disagree with SAP's known
    # 10,000 bbl receipt (mock-sap PO-GOLDEN-CRUDE) by more than the 0.5%
    # hard-exception threshold, reproducing "Terminal quantity != SAP quantity".
    session.add(
        TerminalReceipt(
            receipt_number="TR-GOLDEN-01", terminal=TERMINALS[0], vessel_or_source="MT Petronova Voyager",
            quantity_bbl=9950.0, po_number=GOLDEN_CRUDE_PO_NUMBER,
        )
    )
    session.add(
        TankReading(
            tank_id="TANK-GOLDEN-01", terminal=TERMINALS[0], reading_date=date.today(),
            quantity_bbl=9850.0, method="manual_gauge", po_number=GOLDEN_CRUDE_PO_NUMBER,
        )
    )
    session.flush()
