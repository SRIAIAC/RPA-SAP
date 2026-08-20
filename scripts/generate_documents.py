"""Generates synthetic PDF documents under data/documents/{invoices,vendor,
contracts,customer_orders,expenses,hse}/ for PetroNova Energy Corporation —
purely cosmetic realism (nothing in the platform depends on these files
existing), deterministic via a fixed Faker seed.

Run with the backend venv (has Faker + fpdf2 already):
    backend\\.venv\\Scripts\\python.exe scripts\\generate_documents.py

Volumes are modest (15 per category) and configurable via DOC_COUNT below —
bump it if you want more for a specific demo.
"""

import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker
from fpdf import FPDF, XPos, YPos

SEED = 42
DOC_COUNT = 15
ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "documents"

COMPANY = "PetroNova Energy Corporation"


_NEXT_LINE = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


def _pdf(title: str) -> FPDF:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, COMPANY, **_NEXT_LINE)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Synthetic demo document - no real company or personal data", **_NEXT_LINE)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, title, **_NEXT_LINE)
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(2)
    return pdf


def _kv(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(45, 7, label)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, value, **_NEXT_LINE)


def generate_invoices(fake: Faker, out_dir: Path) -> None:
    for i in range(1, DOC_COUNT + 1):
        vendor = fake.company()
        invoice_number = f"INV-{900000 + i}"
        po_number = f"45000{10000 + i}"
        qty = random.randint(2, 50)
        unit_price = round(random.uniform(500, 25000), 2)
        total = round(qty * unit_price, 2)

        pdf = _pdf(f"Invoice {invoice_number}")
        _kv(pdf, "Vendor:", vendor)
        _kv(pdf, "Invoice Date:", str(date.today() - timedelta(days=random.randint(1, 300))))
        _kv(pdf, "PO Number:", po_number)
        _kv(pdf, "Quantity:", str(qty))
        _kv(pdf, "Unit Price:", f"INR {unit_price:,.2f}")
        _kv(pdf, "TOTAL DUE:", f"INR {total:,.2f}")
        pdf.output(str(out_dir / f"{invoice_number}.pdf"))


def generate_vendor_docs(fake: Faker, out_dir: Path) -> None:
    for i in range(1, DOC_COUNT + 1):
        vendor_code = f"V-{100000 + i}"
        pdf = _pdf(f"Vendor KYC - {vendor_code}")
        _kv(pdf, "Vendor Name:", fake.company())
        _kv(pdf, "GSTIN:", fake.bothify("##???????????#?#").upper())
        _kv(pdf, "PAN:", fake.bothify("?????####?").upper())
        _kv(pdf, "Insurance Expiry:", str(date.today() + timedelta(days=random.randint(-30, 700))))
        _kv(pdf, "Bank Account (last 4):", fake.numerify("####"))
        pdf.output(str(out_dir / f"{vendor_code}_kyc.pdf"))


def generate_contracts(fake: Faker, out_dir: Path) -> None:
    for i in range(1, DOC_COUNT + 1):
        contract_number = f"CTR-{100000 + i}"
        effective = date.today() - timedelta(days=random.randint(30, 900))
        expiry = effective + timedelta(days=365)
        pdf = _pdf(f"Contract {contract_number}")
        _kv(pdf, "Counterparty:", fake.company())
        _kv(pdf, "Effective Date:", str(effective))
        _kv(pdf, "Expiry Date:", str(expiry))
        _kv(pdf, "Renewal Notice Period:", "30 days")
        _kv(pdf, "Termination Clause:", "Either party may terminate with 60 days written notice.")
        pdf.output(str(out_dir / f"{contract_number}.pdf"))


def generate_customer_orders(fake: Faker, out_dir: Path) -> None:
    for i in range(1, DOC_COUNT + 1):
        so_number = f"SO-{600000 + i}"
        pdf = _pdf(f"Sales Order Confirmation {so_number}")
        _kv(pdf, "Customer:", fake.company())
        _kv(pdf, "Order Date:", str(date.today() - timedelta(days=random.randint(1, 200))))
        _kv(pdf, "Delivery Window:", f"{random.randint(3, 21)} business days")
        _kv(pdf, "Quantity (BBL):", str(random.randint(500, 20000)))
        pdf.output(str(out_dir / f"{so_number}.pdf"))


def generate_expenses(fake: Faker, out_dir: Path) -> None:
    categories = ["Travel", "Meals", "Lodging", "Training", "Equipment Rental"]
    for i in range(1, DOC_COUNT + 1):
        expense_number = f"EXP-{200000 + i}"
        pdf = _pdf(f"Expense Receipt {expense_number}")
        _kv(pdf, "Employee:", fake.name())
        _kv(pdf, "Category:", random.choice(categories))
        _kv(pdf, "Date:", str(date.today() - timedelta(days=random.randint(1, 300))))
        _kv(pdf, "Amount:", f"INR {round(random.uniform(200, 45000), 2):,.2f}")
        _kv(pdf, "Vendor:", fake.company())
        pdf.output(str(out_dir / f"{expense_number}.pdf"))


def generate_hse_reports(fake: Faker, out_dir: Path) -> None:
    descriptions = [
        "Minor injury reported, first aid administered on site.",
        "Near miss - dropped object narrowly avoided a technician.",
        "Routine safety walkthrough completed, no issues identified.",
        "Spill of hydrocarbon detected in containment area, contained immediately.",
    ]
    for i in range(1, DOC_COUNT + 1):
        incident_number = f"HSE-{300000 + i}"
        pdf = _pdf(f"HSE Incident Report {incident_number}")
        _kv(pdf, "Location:", random.choice(["Refinery Alpha", "Refinery Beta", "Refinery Gamma", "Terminal North", "Terminal South"]))
        _kv(pdf, "Reported:", str(date.today() - timedelta(days=random.randint(1, 500))))
        _kv(pdf, "Description:", random.choice(descriptions))
        pdf.output(str(out_dir / f"{incident_number}.pdf"))


def main() -> None:
    random.seed(SEED)
    fake = Faker()
    Faker.seed(SEED)

    categories = {
        "invoices": generate_invoices,
        "vendor": generate_vendor_docs,
        "contracts": generate_contracts,
        "customer_orders": generate_customer_orders,
        "expenses": generate_expenses,
        "hse": generate_hse_reports,
    }
    for name, generator in categories.items():
        out_dir = DOCS_DIR / name
        out_dir.mkdir(parents=True, exist_ok=True)
        generator(fake, out_dir)
        print(f"Generated {DOC_COUNT} documents in {out_dir}")


if __name__ == "__main__":
    main()
