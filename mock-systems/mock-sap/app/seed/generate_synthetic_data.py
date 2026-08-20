"""Deterministic synthetic data generator for PetroNova Energy Corporation —
a fully fictional Oil & Gas company. Fixed random seed (42) throughout, so
every fresh database seed produces byte-identical data, including the
golden demo scenario fixtures.

Performance note: uses two-phase inserts (session.add_all + session.flush()
to obtain autoincrement PKs, then build child rows, one session.commit() at
the very end) rather than per-row commits — at section-4-spec volumes
(2000+ POs, 3000+ invoices, 5000+ production records, etc.) that keeps a
fresh seed to a few seconds instead of minutes.

SEED_SCALE=full targets the literal volumes from the platform spec;
SEED_SCALE=small (~10% of full) exists purely for fast local iteration
during development and is not used in the shipped demo.
"""

import random
from datetime import date, datetime, timedelta

from faker import Faker
from sqlmodel import Session, select

from app.models import (
    Contract,
    Customer,
    Delivery,
    Equipment,
    Expense,
    FunctionalLocation,
    GLAccount,
    GoodsReceipt,
    GoodsReceiptItem,
    HSEIncident,
    Invoice,
    InvoiceItem,
    Inventory,
    Material,
    MaintenanceNotification,
    MaintenanceOrder,
    ProductionOrder,
    ProductionRecord,
    PurchaseOrder,
    PurchaseOrderItem,
    SalesOrder,
    SalesOrderItem,
    Vendor,
    CostCenter,
)

SEED = 42

DEPARTMENTS = ["Procurement", "Maintenance", "Finance", "HSE", "Production"]
PLANTS = ["PetroNova Refinery Alpha (RFA)", "PetroNova Refinery Beta (RFB)", "PetroNova Refinery Gamma (RFG)"]
PLANT_CODES = ["RFA", "RFB", "RFG"]
TERMINALS = ["PetroNova Terminal North (TMN)", "PetroNova Terminal South (TMS)"]
WAREHOUSES = [f"PetroNova Warehouse {i} (WH{i})" for i in range(1, 6)]
MATERIAL_CATEGORIES = [
    "Rotating Equipment Spare", "Valve", "Gasket/Seal", "Piping", "Instrumentation",
    "Electrical", "Chemical/Catalyst", "PPE", "General MRO", "Structural Steel",
]
SKILL_GROUPS = ["Electrical", "Rotating Equipment", "Instrumentation", "Mechanical", "Civil"]

# Volumes per SEED_SCALE — "full" matches the platform spec's literal targets.
_VOLUMES = {
    "full": dict(
        vendors=520, materials=1050, customers=320, equipment=520, contracts=520,
        purchase_orders=2050, maintenance_orders=1550, sales_orders=2050,
        production_orders=180, production_days=28, hse_incidents=520, expenses=2050,
    ),
    "small": dict(
        vendors=60, materials=120, customers=40, equipment=60, contracts=60,
        purchase_orders=200, maintenance_orders=150, sales_orders=200,
        production_orders=20, production_days=14, hse_incidents=50, expenses=200,
    ),
}

# --- Golden demo scenario fixed identifiers (never randomly generated) ------
GOLDEN_VENDOR_CODE = "V-999001"
GOLDEN_MATERIAL_CODE = "MAT-999001"
GOLDEN_EXPIRED_VENDOR_CODE = "V-999002"
GOLDEN_CONTRACT_NUMBER = "CTR-GOLDEN-01"
GOLDEN_EQUIPMENT_ID = "EQ-GOLDEN-PUMP-01"
GOLDEN_PRODUCTION_MATERIAL_CODE = "MAT-999002"
GOLDEN_CRUDE_MATERIAL_CODE = "MAT-999003"
GOLDEN_CRUDE_PO_NUMBER = "PO-GOLDEN-CRUDE"


def seed_all(session: Session, scale: str = "full") -> None:
    random.seed(SEED)
    fake = Faker()
    Faker.seed(SEED)
    volumes = _VOLUMES.get(scale, _VOLUMES["full"])

    vendors = _seed_vendors(session, fake, volumes["vendors"])
    materials = _seed_materials(session, fake, volumes["materials"])
    customers = _seed_customers(session, fake, volumes["customers"])
    equipment = _seed_equipment(session, fake, volumes["equipment"])
    _seed_contracts(session, fake, volumes["contracts"], vendors, customers)
    purchase_orders = _seed_purchase_orders_grns(session, fake, volumes["purchase_orders"], vendors, materials)
    _seed_invoices(session, fake, purchase_orders)
    _seed_maintenance(session, fake, volumes["maintenance_orders"], equipment)
    _seed_sales(session, fake, volumes["sales_orders"], customers, materials)
    _seed_production(session, fake, volumes["production_orders"], volumes["production_days"], materials)
    _seed_hse(session, fake, volumes["hse_incidents"], equipment)
    _seed_expenses(session, fake, volumes["expenses"])
    _seed_cost_centers_and_gl(session)
    _seed_golden_scenarios(session, fake, materials)

    session.commit()


def _seed_vendors(session, fake, n) -> list[Vendor]:
    vendors = []
    for i in range(1, n + 1):
        expiry_roll = random.random()
        if expiry_roll < 0.03:
            insurance_expiry = date.today() - timedelta(days=random.randint(1, 200))  # already expired
        elif expiry_roll < 0.08:
            insurance_expiry = date.today() + timedelta(days=random.randint(1, 30))  # renewal window
        else:
            insurance_expiry = date.today() + timedelta(days=random.randint(60, 730))
        vendors.append(
            Vendor(
                vendor_code=f"V-{100000 + i}",
                name=fake.company() + random.choice([" Pvt Ltd", " Industries", " Trading Co", " Engineering", ""]),
                gstin=fake.bothify("##???????????#?#").upper(),
                bank_account_last4=fake.numerify("####"),
                insurance_expiry=insurance_expiry,
                blocked=random.random() < 0.02,
                city=fake.city(),
                department=random.choice(DEPARTMENTS),
                created_at=datetime.utcnow() - timedelta(days=random.randint(30, 2000)),
            )
        )
    session.add_all(vendors)
    session.flush()
    return vendors


def _seed_materials(session, fake, n) -> list[Material]:
    materials = []
    for i in range(1, n + 1):
        category = random.choice(MATERIAL_CATEGORIES)
        materials.append(
            Material(
                material_code=f"MAT-{500000 + i}",
                description=f"{category} - {fake.word().capitalize()} {random.choice(['6in','4in','8in','300#','150#','Type A','Type B'])}",
                uom=random.choice(["EA", "KG", "L", "M", "SET"]),
                unit_price=round(random.uniform(50, 85000), 2),
                hazard_classification=category in ("Chemical/Catalyst", "PPE") and random.random() < 0.4,
                plant=random.choice(PLANT_CODES),
            )
        )
    session.add_all(materials)
    session.flush()
    return materials


def _seed_customers(session, fake, n) -> list[Customer]:
    customers = []
    for i in range(1, n + 1):
        limit = round(random.uniform(500_000, 25_000_000), 2)
        customers.append(
            Customer(
                customer_code=f"C-{700000 + i}",
                name=fake.company() + random.choice([" Refining", " Petrochem", " Energy", " Holdings", ""]),
                credit_limit=limit,
                credit_balance=round(limit * random.uniform(0, 0.9), 2),
                blocked=random.random() < 0.03,
                city=fake.city(),
            )
        )
    session.add_all(customers)
    session.flush()
    return customers


def _seed_equipment(session, fake, n) -> list[Equipment]:
    fl_by_plant = {}
    for plant in PLANT_CODES:
        fl = FunctionalLocation(code=f"FL-{plant}-MAIN", description=f"{plant} Main Process Unit", plant=plant)
        session.add(fl)
        fl_by_plant[plant] = fl
    session.flush()

    equipment_types = ["Centrifugal Pump", "Compressor", "Heat Exchanger", "Distillation Column",
                        "Storage Tank", "Pressure Relief Valve", "Motor", "Control Valve", "Boiler"]
    equipment = []
    for i in range(1, n + 1):
        plant = random.choice(PLANT_CODES)
        criticality = random.choices(
            ["Standard", "Critical", "Single Point of Failure"], weights=[70, 25, 5]
        )[0]
        equipment.append(
            Equipment(
                equipment_id=f"EQ-{100000 + i}",
                description=f"{random.choice(equipment_types)} {fake.bothify('##-?#')}",
                functional_location_id=fl_by_plant[plant].id,
                criticality=criticality,
                plant=plant,
            )
        )
    session.add_all(equipment)
    session.flush()
    return equipment


def _seed_contracts(session, fake, n, vendors, customers) -> None:
    contracts = []
    for i in range(1, n + 1):
        is_vendor_contract = random.random() < 0.7
        effective = date.today() - timedelta(days=random.randint(30, 1000))
        # Skew expiry so a meaningful slice fall within/near the 30-day renewal window.
        expiry_roll = random.random()
        if expiry_roll < 0.05:
            expiry = date.today() + timedelta(days=random.randint(1, 30))
        elif expiry_roll < 0.1:
            expiry = date.today() - timedelta(days=random.randint(1, 60))
        else:
            expiry = date.today() + timedelta(days=random.randint(60, 900))
        contracts.append(
            Contract(
                contract_number=f"CTR-{100000 + i}",
                vendor_id=random.choice(vendors).id if is_vendor_contract else None,
                customer_id=None if is_vendor_contract else random.choice(customers).id,
                title=f"{'Supply' if is_vendor_contract else 'Offtake'} Agreement {fake.bothify('??-####')}",
                effective_date=effective,
                expiry_date=expiry,
                owner=None if random.random() < 0.05 else fake.name(),
                status="Active" if expiry >= date.today() else "Expired",
            )
        )
    session.add_all(contracts)
    session.flush()


def _seed_purchase_orders_grns(session, fake, n, vendors, materials) -> list[PurchaseOrder]:
    orders = []
    for i in range(1, n + 1):
        orders.append(
            PurchaseOrder(
                po_number=f"45000{10000 + i}",
                vendor_id=random.choice(vendors).id,
                status="Open",
                department=random.choice(DEPARTMENTS),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 400)),
            )
        )
    session.add_all(orders)
    session.flush()

    items = []
    item_index: dict[int, list[PurchaseOrderItem]] = {}
    for po in orders:
        n_items = random.randint(1, 3)
        po_items = []
        for line_no in range(1, n_items + 1):
            material = random.choice(materials)
            qty = round(random.uniform(2, 200), 0)
            item = PurchaseOrderItem(
                po_id=po.id, line_no=line_no, material_id=material.id,
                quantity=qty, unit_price=material.unit_price,
            )
            items.append(item)
            po_items.append(item)
        item_index[po.id] = po_items
    session.add_all(items)
    session.flush()

    # ~85% of POs get a goods receipt (the rest stay "no GRN yet" — realistic
    # in-transit/open orders, and the natural source of MISSING_GRN exceptions).
    grns = []
    for po in orders:
        if random.random() >= 0.85:
            continue
        grns.append(GoodsReceipt(grn_number=f"5000{10000 + po.id}", po_id=po.id))
    session.add_all(grns)
    session.flush()

    grn_items = []
    for grn in grns:
        for po_item in item_index[grn.po_id]:
            # Most receipts match exactly; a slice have a small realistic variance.
            variance_roll = random.random()
            if variance_roll < 0.9:
                received = po_item.quantity
            else:
                received = round(po_item.quantity * random.uniform(0.9, 1.05), 0)
            grn_items.append(
                GoodsReceiptItem(grn_id=grn.id, po_item_id=po_item.id, quantity_received=received)
            )
    session.add_all(grn_items)
    session.flush()

    return orders


def _seed_invoices(session, fake, purchase_orders: list[PurchaseOrder]) -> None:
    invoices = []
    items = []
    seen_numbers: set[str] = set()
    # Roughly 1.3 invoices per PO on average (some POs invoiced across
    # multiple partial invoices), reaching the 3000+ target off 2000+ POs.
    idx = 1
    for po in purchase_orders:
        n_invoices = 1 if random.random() < 0.45 else 2
        for _ in range(n_invoices):
            invoice_number = f"INV-{900000 + idx}"
            idx += 1
            po_items = None
            invoice = Invoice(
                invoice_number=invoice_number,
                vendor_id=po.vendor_id,
                po_id=po.id,
                invoice_date=date.today() - timedelta(days=random.randint(0, 380)),
                total_amount=0.0,  # filled after items below
                status=random.choices(["Posted", "Pending"], weights=[70, 30])[0],
            )
            invoices.append(invoice)
    session.add_all(invoices)
    session.flush()

    # Attach 1 line item per invoice referencing a random item of its PO,
    # with realistic price found on the invoice (mostly == PO price).
    po_items_by_po: dict[int, list[PurchaseOrderItem]] = {}
    for invoice in invoices:
        if invoice.po_id not in po_items_by_po:
            po_items_by_po[invoice.po_id] = session.exec(
                select(PurchaseOrderItem).where(PurchaseOrderItem.po_id == invoice.po_id)
            ).all()
        po_item = random.choice(po_items_by_po[invoice.po_id])
        price = po_item.unit_price if random.random() < 0.9 else round(po_item.unit_price * random.uniform(0.97, 1.03), 2)
        items.append(
            InvoiceItem(invoice_id=invoice.id, po_item_id=po_item.id, quantity=po_item.quantity, unit_price=price)
        )
        invoice.total_amount = round(po_item.quantity * price, 2)
    session.add_all(items)
    session.flush()


def _seed_maintenance(session, fake, n, equipment: list[Equipment]) -> None:
    notifications = []
    for i in range(1, n // 2 + 1):
        eq = random.choice(equipment)
        priority = random.choices(["Emergency", "Urgent", "Routine"], weights=[10, 25, 65])[0]
        notifications.append(
            MaintenanceNotification(
                notification_number=f"NOTIF-{800000 + i}",
                equipment_id=eq.id,
                description=f"{priority} maintenance alert on {eq.description}",
                priority=priority,
                status=random.choices(["Open", "Closed"], weights=[20, 80])[0],
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            )
        )
    session.add_all(notifications)
    session.flush()

    orders = []
    for i in range(1, n + 1):
        eq = random.choice(equipment)
        priority = random.choices(["Emergency", "Urgent", "Routine"], weights=[10, 25, 65])[0]
        notif = random.choice(notifications) if notifications and random.random() < 0.6 else None
        orders.append(
            MaintenanceOrder(
                order_number=f"WO-{810000 + i}",
                notification_id=notif.id if notif else None,
                equipment_id=eq.id,
                priority=priority,
                status=random.choices(["Open", "In Progress", "Closed"], weights=[15, 15, 70])[0],
                technician=fake.name(),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            )
        )
    session.add_all(orders)
    session.flush()


def _seed_sales(session, fake, n, customers: list[Customer], materials: list[Material]) -> None:
    orders = []
    for i in range(1, n + 1):
        customer = random.choice(customers)
        orders.append(
            SalesOrder(
                so_number=f"SO-{600000 + i}",
                customer_id=customer.id,
                status="Blocked" if customer.blocked else random.choices(["Created", "Delivered"], weights=[30, 70])[0],
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 400)),
            )
        )
    session.add_all(orders)
    session.flush()

    items = []
    deliveries = []
    for order in orders:
        for _ in range(random.randint(1, 2)):
            material = random.choice(materials)
            items.append(
                SalesOrderItem(
                    so_id=order.id, material_id=material.id,
                    quantity=round(random.uniform(1, 500), 0), unit_price=material.unit_price,
                )
            )
        if order.status == "Delivered":
            deliveries.append(
                Delivery(
                    delivery_number=f"DLV-{650000 + order.id}", so_id=order.id,
                    shipped_at=order.created_at + timedelta(days=random.randint(1, 10)), status="Shipped",
                )
            )
    session.add_all(items)
    session.add_all(deliveries)
    session.flush()


def _seed_production(session, fake, n_orders, n_days, materials: list[Material]) -> None:
    orders = []
    for i in range(1, n_orders + 1):
        plant = PLANT_CODES[i % len(PLANT_CODES)]
        orders.append(
            ProductionOrder(
                order_number=f"PORD-{400000 + i}",
                plant=plant,
                material_id=random.choice(materials).id,
                planned_quantity=round(random.uniform(500, 20000), 0),
                status=random.choices(["Confirmed", "Unconfirmed"], weights=[85, 15])[0],
                created_at=datetime.utcnow() - timedelta(days=n_days + random.randint(0, 30)),
            )
        )
    session.add_all(orders)
    session.flush()

    records = []
    for order in orders:
        for day_offset in range(n_days):
            variance_roll = random.random()
            if variance_roll < 0.85:
                actual = order.planned_quantity * random.uniform(0.97, 1.02)
            elif variance_roll < 0.95:
                actual = order.planned_quantity * random.uniform(0.90, 0.97)  # anomaly-flag band
            else:
                actual = order.planned_quantity * random.uniform(0.75, 0.89)  # critical band
            records.append(
                ProductionRecord(
                    production_order_id=order.id, plant=order.plant,
                    record_date=date.today() - timedelta(days=day_offset),
                    planned_quantity=order.planned_quantity, actual_quantity=round(actual, 0),
                )
            )
    session.add_all(records)
    session.flush()


def _seed_hse(session, fake, n, equipment: list[Equipment]) -> None:
    templates = [
        ("Minor injury reported, first aid administered on site.", "Low"),
        ("Near miss — dropped object narrowly avoided a technician.", "Medium"),
        ("Chemical exposure during sampling, medical treatment provided.", "High"),
        ("Fire reported near the process unit, extinguished quickly, no injuries.", "Critical"),
        ("Routine safety walkthrough completed, no issues identified.", "Low"),
        ("Spill of hydrocarbon detected in containment area, contained immediately.", "Medium"),
        ("Worker suffered a fall resulting in hospitalization.", "Critical"),
        ("H2S alarm triggered in confined space, area evacuated per procedure.", "High"),
    ]
    incidents = []
    for i in range(1, n + 1):
        desc, severity = random.choice(templates)
        eq = random.choice(equipment) if random.random() < 0.5 else None
        incidents.append(
            HSEIncident(
                incident_number=f"HSE-{300000 + i}",
                description=desc,
                severity=severity,
                location=random.choice(PLANTS + TERMINALS + WAREHOUSES),
                equipment_id=eq.id if eq else None,
                reported_at=datetime.utcnow() - timedelta(days=random.randint(1, 700)),
                status=random.choices(["Open", "Investigating", "Closed"], weights=[10, 15, 75])[0],
            )
        )
    session.add_all(incidents)
    session.flush()


def _seed_expenses(session, fake, n) -> None:
    categories = ["Travel", "Meals", "Lodging", "Training", "Equipment Rental", "Office Supplies"]
    expenses = []
    for i in range(1, n + 1):
        amount = round(random.uniform(200, 45000), 2)
        expenses.append(
            Expense(
                expense_number=f"EXP-{200000 + i}",
                employee_name=fake.name(),
                department=random.choice(DEPARTMENTS),
                amount=amount,
                category=random.choice(categories),
                expense_date=date.today() - timedelta(days=random.randint(1, 400)),
                has_receipt=random.random() > 0.05,
            )
        )
    session.add_all(expenses)
    session.flush()


def _seed_cost_centers_and_gl(session) -> None:
    cost_centers = []
    for dept in DEPARTMENTS:
        budget = round(random.uniform(5_000_000, 50_000_000), 2)
        cost_centers.append(
            CostCenter(
                code=f"CC-{dept[:4].upper()}", name=f"{dept} Cost Center", department=dept,
                budget=budget, spent=round(budget * random.uniform(0.3, 0.95), 2),
            )
        )
    session.add_all(cost_centers)

    gl_accounts = [
        GLAccount(account_number="400000", name="Materials & Supplies Expense", account_type="Expense"),
        GLAccount(account_number="410000", name="Maintenance & Repairs Expense", account_type="Expense"),
        GLAccount(account_number="420000", name="Travel & Entertainment Expense", account_type="Expense"),
        GLAccount(account_number="500000", name="Accounts Payable", account_type="Liability"),
        GLAccount(account_number="600000", name="Product Sales Revenue", account_type="Revenue"),
    ]
    session.add_all(gl_accounts)
    session.flush()


def _seed_golden_scenarios(session, fake, materials: list[Material]) -> None:
    """Hand-crafted, fixed-ID records for the platform's golden demo
    scenarios — never randomly generated, so a Demo Scenario run always
    reproduces the exact documented outcome."""
    golden_vendor = Vendor(
        vendor_code=GOLDEN_VENDOR_CODE, name="Deccan Valves & Fittings Pvt Ltd",
        gstin="27AAAAA0000A1Z5", bank_account_last4="4471",
        insurance_expiry=date.today() + timedelta(days=365), blocked=False,
        city="Pune", department="Procurement",
    )
    expired_vendor = Vendor(
        vendor_code=GOLDEN_EXPIRED_VENDOR_CODE, name="Krishna Industrial Contractors",
        gstin="27BBBBB1111B1Z6", bank_account_last4="8820",
        insurance_expiry=date.today() - timedelta(days=15), blocked=False,  # golden scenario: expired insurance
        city="Nagpur", department="Maintenance",
    )
    session.add_all([golden_vendor, expired_vendor])
    session.flush()

    golden_material = Material(
        material_code=GOLDEN_MATERIAL_CODE, description="Gate Valve 6in 300# API 600",
        uom="EA", unit_price=18500.0, hazard_classification=False, plant="RFA",
    )
    production_material = Material(
        material_code=GOLDEN_PRODUCTION_MATERIAL_CODE, description="Refined Diesel — Grade A",
        uom="BBL", unit_price=6200.0, hazard_classification=False, plant="RFA",
    )
    session.add_all([golden_material, production_material])
    session.flush()

    # --- Invoice 3-way match: 5 golden scenarios (PO#/GRN#/Invoice# fixed) ---
    golden_pos = []
    for suffix, qty in [("01", 4), ("02", 4), ("03", 4), ("05", 4)]:  # scenario 4 (duplicate) reuses scenario 1's PO
        po = PurchaseOrder(
            po_number=f"PO-GOLDEN-{suffix}", vendor_id=golden_vendor.id, status="Open", department="Procurement",
        )
        session.add(po)
        golden_pos.append((suffix, po))
    session.flush()

    po_by_suffix = dict(golden_pos)
    po_items_by_suffix = {}
    for suffix, po in golden_pos:
        item = PurchaseOrderItem(po_id=po.id, line_no=1, material_id=golden_material.id, quantity=4, unit_price=125000.0)
        session.add(item)
        po_items_by_suffix[suffix] = item
    session.flush()

    # GRNs: scenario 1 (exact match), 2 (short-received: 3 of 4), 3 (exact),
    # 4 (duplicate reuses scenario 1's GRN/PO). Scenario 5 has NO GRN at all.
    grn_specs = [("01", 4), ("02", 3), ("03", 4)]
    grns_by_suffix = {}
    for suffix, received_qty in grn_specs:
        grn = GoodsReceipt(grn_number=f"GRN-GOLDEN-{suffix}", po_id=po_by_suffix[suffix].id)
        session.add(grn)
        grns_by_suffix[suffix] = grn
    session.flush()
    for suffix, received_qty in grn_specs:
        session.add(
            GoodsReceiptItem(
                grn_id=grns_by_suffix[suffix].id, po_item_id=po_items_by_suffix[suffix].id,
                quantity_received=received_qty,
            )
        )
    session.flush()

    # Invoices: 1=auto-approve, 2=qty mismatch, 3=price mismatch,
    # 4=duplicate (same invoice number as #1, posted against the same PO),
    # 5=missing GRN (invoice against PO-GOLDEN-05, which has no GRN).
    invoice_specs = [
        ("INV-GOLDEN-01", "01", 4, 125000.0),
        ("INV-GOLDEN-02", "02", 4, 125000.0),
        ("INV-GOLDEN-03", "03", 4, 140000.0),
        ("INV-GOLDEN-01", "01", 4, 125000.0),  # duplicate: same invoice_number handled at recipe level
        ("INV-GOLDEN-05", "05", 4, 125000.0),
    ]
    # invoice_number is unique in the schema, so the literal "duplicate
    # invoice" row can't be persisted twice under the same number — instead
    # we persist the first 3 + the missing-GRN one, and the workflow recipe
    # (Phase 7) simulates scenario 4 by re-submitting INV-GOLDEN-01's number
    # against the same vendor, which the duplicate-check step will find via
    # SAPIntegrationService.get_invoice().
    seen = set()
    for invoice_number, suffix, qty, price in invoice_specs:
        if invoice_number in seen:
            continue
        seen.add(invoice_number)
        invoice = Invoice(
            invoice_number=invoice_number, vendor_id=golden_vendor.id, po_id=po_by_suffix[suffix].id,
            invoice_date=date.today(), total_amount=round(qty * price, 2), status="Pending",
        )
        session.add(invoice)
        session.flush()
        session.add(
            InvoiceItem(invoice_id=invoice.id, po_item_id=po_items_by_suffix[suffix].id, quantity=qty, unit_price=price)
        )
    session.flush()

    # --- Vendor onboarding / compliance: expired insurance ------------------
    # (expired_vendor above already carries an expired insurance_expiry.)

    # --- Contract expiry: expires in 12 days, owned -------------------------
    session.add(
        Contract(
            contract_number=GOLDEN_CONTRACT_NUMBER, vendor_id=golden_vendor.id,
            title="Valve & Fittings Supply Agreement", effective_date=date.today() - timedelta(days=353),
            expiry_date=date.today() + timedelta(days=12), owner="Vikram Shah", status="Active",
        )
    )

    # --- Crude receipt reconciliation: known SAP-side receipt quantity that
    # mock-non-sap's golden Terminal/Tank Farm readings (Phase 5) deliberately
    # disagree with, to reproduce the "Terminal qty != SAP qty" golden scenario.
    crude_material = Material(
        material_code=GOLDEN_CRUDE_MATERIAL_CODE, description="Crude Oil - WTI Blend",
        uom="BBL", unit_price=6800.0, hazard_classification=True, plant="RFA",
    )
    session.add(crude_material)
    session.flush()
    crude_po = PurchaseOrder(
        po_number=GOLDEN_CRUDE_PO_NUMBER, vendor_id=golden_vendor.id, status="Open", department="Production",
    )
    session.add(crude_po)
    session.flush()
    crude_po_item = PurchaseOrderItem(
        po_id=crude_po.id, line_no=1, material_id=crude_material.id, quantity=10000.0, unit_price=6800.0,
    )
    session.add(crude_po_item)
    session.flush()
    crude_grn = GoodsReceipt(grn_number=f"GRN-{GOLDEN_CRUDE_PO_NUMBER}", po_id=crude_po.id)
    session.add(crude_grn)
    session.flush()
    session.add(
        GoodsReceiptItem(grn_id=crude_grn.id, po_item_id=crude_po_item.id, quantity_received=10000.0)
    )

    # --- Maintenance: pump equipment for the SCADA-vibration golden scenario
    fl = session.exec(select(FunctionalLocation).where(FunctionalLocation.plant == "RFA")).first()
    session.add(
        Equipment(
            equipment_id=GOLDEN_EQUIPMENT_ID, description="Centrifugal Pump P-101 (Crude Feed)",
            functional_location_id=fl.id if fl else None, criticality="Critical", plant="RFA",
        )
    )

    # --- Production: a production order with a large planned-vs-actual gap --
    prod_order = ProductionOrder(
        order_number="PORD-GOLDEN-01", plant="RFA", material_id=production_material.id,
        planned_quantity=10000.0, status="Confirmed",
    )
    session.add(prod_order)
    session.flush()
    session.add(
        ProductionRecord(
            production_order_id=prod_order.id, plant="RFA", record_date=date.today(),
            planned_quantity=10000.0, actual_quantity=8500.0,  # 15% below plan -> Critical anomaly
        )
    )

    session.flush()
