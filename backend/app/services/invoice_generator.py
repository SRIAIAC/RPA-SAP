"""Renders realistic-looking scanned-invoice PNG images using PIL, so the OCR
service in this demo has real pixels with real rendered text to read — not a
hardcoded stand-in for OCR output.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "invoices"

FONT_PATH = "C:\\Windows\\Fonts\\arial.ttf"
FONT_PATH_BOLD = "C:\\Windows\\Fonts\\arialbd.ttf"


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    path = FONT_PATH_BOLD if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        try:
            return ImageFont.truetype(FONT_PATH, size)
        except Exception:
            return ImageFont.load_default()


INVOICES = [
    dict(
        filename="invoice_001_deccan_valves.png",
        vendor="Deccan Valves & Fittings Pvt Ltd",
        address="Plot 42, MIDC Industrial Estate, Pune, MH 411019",
        invoice_number="INV-58231",
        invoice_date="2026-07-12",
        po_number="PO-100482",
        items=[
            ("Gate Valve 6in 300# API 600", "4", "18,500.00", "74,000.00"),
            ("Gasket Spiral Wound 6in", "8", "1,200.00", "9,600.00"),
        ],
        subtotal="83,600.00",
        tax="15,048.00",
        total="98,648.00",
        currency="INR",
        terms="Net 30 days from invoice date",
    ),
    dict(
        filename="invoice_002_bharat_pumps.png",
        vendor="Bharat Pumps & Compressors Ltd",
        address="Industrial Area, Naini, Allahabad, UP 211008",
        invoice_number="INV-90144",
        invoice_date="2026-07-18",
        po_number="PO-100510",
        items=[
            ("Centrifugal Pump Overhaul Kit", "2", "1,45,000.00", "2,90,000.00"),
            ("Mechanical Seal Assembly", "2", "32,500.00", "65,000.00"),
        ],
        subtotal="3,55,000.00",
        tax="63,900.00",
        total="4,18,900.00",
        currency="INR",
        terms="Net 45 days from invoice date",
    ),
    dict(
        filename="invoice_003_gulf_safety.png",
        vendor="Gulf Safety Equipment Trading LLC",
        address="Jebel Ali Free Zone, Dubai, UAE",
        invoice_number="INV-2201",
        invoice_date="2026-06-29",
        po_number="PO-100455",
        items=[
            ("H2S Personal Monitor (Set of 25)", "1", "3,750.00", "3,750.00"),
            ("Confined Space Gas Detector", "5", "410.00", "2,050.00"),
        ],
        subtotal="5,800.00",
        tax="290.00",
        total="6,090.00",
        currency="USD",
        terms="Net 30 days from invoice date",
    ),
    dict(
        filename="invoice_004_krishna_chemicals.png",
        vendor="Krishna Specialty Chemicals Pvt Ltd",
        address="GIDC Estate, Vadodara, GJ 390010",
        invoice_number="INV-77390",
        invoice_date="2026-07-25",
        po_number="PO-100521",
        items=[
            ("Corrosion Inhibitor (200L drum)", "10", "24,800.00", "2,48,000.00"),
            ("Scale Inhibitor (200L drum)", "6", "21,300.00", "1,27,800.00"),
        ],
        subtotal="3,75,800.00",
        tax="67,644.00",
        total="4,43,444.00",
        currency="INR",
        terms="Net 30 days from invoice date",
    ),
    dict(
        filename="invoice_005_offshore_logistics.png",
        vendor="Offshore Logistics & Freight Solutions",
        address="Port Road, Kandla, GJ 370210",
        invoice_number="INV-33021",
        invoice_date="2026-08-02",
        po_number="PO-100560",
        items=[
            ("Crane Barge Charter - 3 days", "1", "9,60,000.00", "9,60,000.00"),
            ("Marine Survey & Certification", "1", "45,000.00", "45,000.00"),
        ],
        subtotal="10,05,000.00",
        tax="1,80,900.00",
        total="11,85,900.00",
        currency="INR",
        terms="Net 30 days from invoice date",
    ),
]


def _draw_invoice(spec: dict) -> Image.Image:
    W, H = 1000, 1300
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    f_h1 = _font(38, bold=True)
    f_h2 = _font(22, bold=True)
    f_body = _font(18)
    f_small = _font(15)

    d.text((50, 40), spec["vendor"], font=f_h2, fill="black")
    d.text((50, 70), spec["address"], font=f_small, fill="black")

    d.text((650, 40), "INVOICE", font=f_h1, fill="black")
    d.line((50, 120, 950, 120), fill="black", width=2)

    y = 150
    d.text((50, y), f"Invoice Number: {spec['invoice_number']}", font=f_body, fill="black")
    d.text((550, y), f"Invoice Date: {spec['invoice_date']}", font=f_body, fill="black")
    y += 32
    d.text((50, y), f"PO Number: {spec['po_number']}", font=f_body, fill="black")
    y += 32
    d.text((50, y), f"Payment Terms: {spec['terms']}", font=f_body, fill="black")
    y += 50

    d.line((50, y, 950, y), fill="black", width=1)
    y += 15
    d.text((50, y), "Description", font=f_h2, fill="black")
    d.text((600, y), "Qty", font=f_h2, fill="black")
    d.text((680, y), "Unit Price", font=f_h2, fill="black")
    d.text((820, y), "Line Total", font=f_h2, fill="black")
    y += 34
    d.line((50, y, 950, y), fill="black", width=1)
    y += 15

    for desc, qty, price, line_total in spec["items"]:
        d.text((50, y), desc, font=f_body, fill="black")
        d.text((600, y), qty, font=f_body, fill="black")
        d.text((680, y), f"{spec['currency']} {price}", font=f_body, fill="black")
        d.text((820, y), f"{spec['currency']} {line_total}", font=f_body, fill="black")
        y += 34

    y += 20
    d.line((600, y, 950, y), fill="black", width=1)
    y += 15
    d.text((680, y), "Subtotal:", font=f_body, fill="black")
    d.text((820, y), f"{spec['currency']} {spec['subtotal']}", font=f_body, fill="black")
    y += 30
    d.text((680, y), "Tax:", font=f_body, fill="black")
    d.text((820, y), f"{spec['currency']} {spec['tax']}", font=f_body, fill="black")
    y += 30
    d.text((680, y), "TOTAL DUE:", font=f_h2, fill="black")
    d.text((820, y), f"{spec['currency']} {spec['total']}", font=f_h2, fill="black")

    y += 80
    d.line((50, y, 950, y), fill="black", width=1)
    y += 20
    d.text((50, y), "Please remit payment to the account on file within the stated payment terms.", font=f_small, fill="black")
    y += 25
    d.text((50, y), f"Thank you for your business — {spec['vendor']}", font=f_small, fill="black")

    return img


def generate_all_invoices() -> list[str]:
    """Generates the 5 invoice PNGs if they don't already exist. Returns the
    list of absolute file paths."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for spec in INVOICES:
        path = DATA_DIR / spec["filename"]
        if not path.exists():
            img = _draw_invoice(spec)
            img.save(path)
        paths.append(str(path))
    return paths


def invoice_spec_for_filename(filename: str) -> dict | None:
    for spec in INVOICES:
        if spec["filename"] == filename:
            return spec
    return None
