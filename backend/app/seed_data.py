import json

from sqlmodel import Session, select

from app.auth import hash_password
from app.models import Department, Level, User, Workflow, WorkflowAccess

DEMO_PASSWORD = "Demo@123"

WORKFLOWS = [
    # Procurement
    dict(
        key="PO_CREATE",
        name="Purchase Order Creation",
        department=Department.PROCUREMENT,
        description="Reads an approved purchase request, validates vendor and material master data, creates the PO in SAP MM and emails it to the supplier.",
        sap_systems="SAP S/4HANA MM",
        non_sap_systems="Email, Excel, Supplier Portal",
        steps=[
            "Read approved purchase request",
            "Validate vendor master in SAP",
            "Validate material master in SAP",
            "Create Purchase Order in SAP MM",
            "Email PO to supplier",
            "Log confirmation in tracker",
        ],
        exceptions=[
            "Vendor blocked in SAP",
            "Material not found in material master",
            "Budget exceeds cost center limit",
            "Supplier email bounced",
        ],
    ),
    dict(
        key="INV_MATCH",
        name="Invoice 3-Way Matching",
        department=Department.PROCUREMENT,
        description="Extracts supplier invoices from email, matches PO / GRN / invoice, posts clean matches in SAP FI and routes mismatches to an exception queue.",
        sap_systems="SAP FI, SAP MM",
        non_sap_systems="Email, PDF Invoices, Vendor Portal",
        steps=[
            "Retrieve invoice from email inbox",
            "OCR extract invoice fields",
            "Lookup PO in SAP MM",
            "Lookup GRN in SAP MM",
            "Perform 3-way match",
            "Post invoice in SAP FI",
            "Notify AP team",
        ],
        exceptions=[
            "Quantity mismatch between GRN and invoice",
            "Price variance beyond tolerance",
            "PO not found in SAP",
            "Duplicate invoice detected",
        ],
    ),
    dict(
        key="VENDOR_ONBOARD",
        name="Vendor Onboarding",
        department=Department.PROCUREMENT,
        description="Collects vendor documents from the portal, validates KYC/compliance paperwork, runs a duplicate check and creates the vendor master in SAP.",
        sap_systems="SAP S/4HANA",
        non_sap_systems="Email, Vendor Portal, KYC Documents",
        steps=[
            "Collect vendor documents from portal",
            "OCR extract vendor details",
            "Run duplicate vendor check in SAP",
            "Validate KYC/compliance documents",
            "Create vendor master in SAP",
            "Route to approval workflow",
        ],
        exceptions=[
            "Missing GST/tax certificate",
            "Duplicate vendor found in SAP",
            "Insurance certificate expired",
            "Bank details validation failed",
        ],
    ),
    # Maintenance
    dict(
        key="MAINT_WO",
        name="Maintenance Work Order Automation",
        department=Department.MAINTENANCE,
        description="Turns a SCADA/IoT equipment alert into a SAP PM notification and work order, then assigns and notifies the technician.",
        sap_systems="SAP PM",
        non_sap_systems="SCADA/IoT, Email, Microsoft Teams",
        steps=[
            "Receive equipment alert from SCADA/IoT",
            "Identify equipment in SAP Asset Master",
            "Check for existing open notifications",
            "Create maintenance notification in SAP PM",
            "Create and assign work order",
            "Notify technician via Teams/Email",
        ],
        exceptions=[
            "Equipment ID not found in Asset Master",
            "Duplicate open work order exists",
            "No technician available in required skill group",
            "Spare part shortage blocks work order",
        ],
    ),
    dict(
        key="SPARE_REPLEN",
        name="Spare Parts Replenishment",
        department=Department.MAINTENANCE,
        description="Monitors SAP stock against minimum thresholds, checks open POs and warehouse/supplier availability, and raises a purchase requisition.",
        sap_systems="SAP MM, SAP PP",
        non_sap_systems="Warehouse Management System, Supplier Portal",
        steps=[
            "Monitor SAP stock levels vs minimum threshold",
            "Check open purchase orders in SAP MM",
            "Check warehouse system for available stock",
            "Check supplier portal for availability",
            "Create purchase requisition in SAP",
            "Notify procurement team",
        ],
        exceptions=[
            "Supplier lead time exceeds SLA",
            "No approved supplier for material",
            "Requisition exceeds department budget",
        ],
    ),
    dict(
        key="SHIFT_HANDOVER",
        name="Shift Handover Automation",
        department=Department.MAINTENANCE,
        description="Consolidates open work orders, active alarms and production data into a shift handover report for the incoming shift lead.",
        sap_systems="SAP PM",
        non_sap_systems="SCADA, Historian, Email",
        steps=[
            "Collect open work orders from SAP PM",
            "Collect active alarms from SCADA",
            "Collect production data from Historian",
            "Consolidate shift handover report",
            "Distribute report to incoming shift lead",
        ],
        exceptions=[
            "SCADA data feed unavailable",
            "Unresolved critical alarm carried over",
            "Historian data gap detected",
        ],
    ),
    # Finance
    dict(
        key="EXPENSE_PROC",
        name="Employee Expense Processing",
        department=Department.FINANCE,
        description="Reads expense receipts, validates against policy, matches to the SAP Concur claim and posts approved expenses in SAP FI.",
        sap_systems="SAP Concur, SAP FI",
        non_sap_systems="Email, PDF Receipts, Banking Portal",
        steps=[
            "Retrieve expense receipts from email",
            "OCR extract receipt line items",
            "Validate against travel & expense policy",
            "Match to SAP Concur claim",
            "Post approved expense in SAP FI",
            "Flag policy violations for review",
        ],
        exceptions=[
            "Receipt exceeds policy limit",
            "Missing itemized receipt",
            "Duplicate expense claim detected",
        ],
    ),
    dict(
        key="FUEL_RECON",
        name="Fuel & Lubricant Stock Reconciliation",
        department=Department.FINANCE,
        description="Compares tank monitoring readings against SAP inventory balances and routes variances beyond tolerance to the finance controller.",
        sap_systems="SAP MM",
        non_sap_systems="Tank Monitoring System, Excel",
        steps=[
            "Retrieve tank readings from Tank Monitoring System",
            "Retrieve SAP inventory balance",
            "Calculate variance",
            "Apply tolerance rules",
            "Generate reconciliation report",
            "Route variance to finance controller",
        ],
        exceptions=[
            "Variance exceeds tolerance threshold",
            "Tank sensor reading anomaly",
            "SAP inventory posting delay",
        ],
    ),
    dict(
        key="CONTRACT_EXPIRY",
        name="Contract Expiry Monitoring",
        department=Department.FINANCE,
        description="Scans the contract repository for agreements expiring within 30 days, cross-checks SAP and creates renewal tasks for the owner.",
        sap_systems="SAP",
        non_sap_systems="SharePoint, Excel, Contract Management System",
        steps=[
            "Scan SharePoint contract repository",
            "Cross-check contract end dates against SAP",
            "Identify contracts expiring within 30 days",
            "Notify contract owner and finance",
            "Create renewal task in tracker",
        ],
        exceptions=[
            "Contract document missing key terms",
            "No owner assigned to contract",
            "Renewal task overdue",
        ],
    ),
    # HSE
    dict(
        key="HSE_INCIDENT",
        name="HSE Incident Reporting",
        department=Department.HSE,
        description="Classifies an incident reported via the mobile app, creates the SAP EHS record and opens an investigation workflow.",
        sap_systems="SAP EHS",
        non_sap_systems="Mobile App, Email, SharePoint",
        steps=[
            "Capture incident report from mobile app",
            "AI classification of incident severity",
            "Identify affected location/equipment",
            "Create incident record in SAP EHS",
            "Notify HSE manager",
            "Open investigation workflow",
        ],
        exceptions=[
            "High-severity incident requires immediate escalation",
            "Incomplete incident description",
            "Equipment/location not found in SAP",
        ],
    ),
    dict(
        key="COMPLIANCE_DOC",
        name="Compliance Document Collection",
        department=Department.HSE,
        description="Identifies vendors/employees with missing certificates, requests documents automatically and updates SAP compliance records.",
        sap_systems="SAP",
        non_sap_systems="SharePoint, Email, Vendor Portal",
        steps=[
            "Identify vendors/employees with missing certificates",
            "Auto-request documents via email",
            "Validate received documents",
            "Update compliance records in SAP",
            "Notify HSE of outstanding items",
        ],
        exceptions=[
            "Certificate rejected due to poor quality scan",
            "Certificate expired on submission",
            "No response after 3 reminders",
        ],
    ),
    dict(
        key="ENV_COMPLIANCE",
        name="Environmental Compliance Reporting",
        department=Department.HSE,
        description="Consolidates emissions data against regulatory thresholds and submits the compliance report to the regulator portal.",
        sap_systems="SAP EHS",
        non_sap_systems="Environmental Monitoring System, Regulator Portal",
        steps=[
            "Collect emissions data from monitoring stations",
            "Compare against regulatory thresholds",
            "Consolidate compliance report",
            "Submit report to regulator portal",
            "Archive report in SAP EHS",
        ],
        exceptions=[
            "Emissions reading exceeds regulatory limit",
            "Monitoring station offline",
            "Regulator portal submission failed",
        ],
    ),
    # Production
    dict(
        key="PROD_REPORT",
        name="Daily Production Reporting",
        department=Department.PRODUCTION,
        description="Consolidates SCADA/Historian data against SAP production orders, runs anomaly detection and distributes the daily report.",
        sap_systems="SAP PP",
        non_sap_systems="SCADA, Historian, Excel, Power BI",
        steps=[
            "Collect production data from SCADA/Historian",
            "Retrieve SAP production orders",
            "Compare actual vs planned output",
            "Run AI anomaly detection",
            "Generate daily production report",
            "Distribute via Power BI/Email",
        ],
        exceptions=[
            "Production variance exceeds threshold",
            "SCADA/Historian data gap",
            "SAP production order not confirmed",
        ],
    ),
    dict(
        key="CRUDE_RECON",
        name="Crude Oil Receipt Reconciliation",
        department=Department.PRODUCTION,
        description="Reconciles shipment, tank farm and SAP receipt quantities for incoming crude and flags variances beyond tolerance.",
        sap_systems="SAP MM, SAP IS-Oil",
        non_sap_systems="Terminal Management System, Tank Farm System, Excel",
        steps=[
            "Retrieve shipment quantity from Terminal System",
            "Retrieve tank measurement from Tank Farm System",
            "Retrieve SAP MM receipt quantity",
            "Consolidate and compare quantities",
            "Apply reconciliation rules engine",
            "Auto-close or flag exception",
        ],
        exceptions=[
            "Variance exceeds allowed tolerance (BBL)",
            "Tank Farm reading unavailable",
            "SAP receipt not yet posted",
        ],
    ),
    dict(
        key="SALES_ORDER",
        name="Sales Order Processing",
        department=Department.PRODUCTION,
        description="Extracts customer purchase orders from email, validates credit and material availability, and creates the sales order in SAP SD.",
        sap_systems="SAP SD",
        non_sap_systems="Customer Email, PDF, CRM",
        steps=[
            "Retrieve customer PO from email/portal",
            "AI extract order details",
            "Validate customer credit limit in SAP",
            "Validate material availability",
            "Create sales order in SAP SD",
            "Trigger delivery creation",
            "Notify customer",
        ],
        exceptions=[
            "Customer credit limit exceeded",
            "Material out of stock",
            "Customer master blocked in SAP",
        ],
    ),
]

# (username, full_name, department, level)
USERS = [
    ("admin", "System Administrator", Department.ADMIN, Level.ADMIN),
    ("asha.rao", "Asha Rao", Department.PROCUREMENT, Level.MANAGER),
    ("vikram.shah", "Vikram Shah", Department.PROCUREMENT, Level.SENIOR_MANAGER),
    ("neha.kapoor", "Neha Kapoor", Department.PROCUREMENT, Level.DEPT_HEAD),
    ("rahul.verma", "Rahul Verma", Department.MAINTENANCE, Level.MANAGER),
    ("priya.nair", "Priya Nair", Department.MAINTENANCE, Level.SENIOR_MANAGER),
    ("suresh.iyer", "Suresh Iyer", Department.MAINTENANCE, Level.DEPT_HEAD),
    ("anjali.mehta", "Anjali Mehta", Department.FINANCE, Level.MANAGER),
    ("karan.singh", "Karan Singh", Department.FINANCE, Level.SENIOR_MANAGER),
    ("deepa.joshi", "Deepa Joshi", Department.FINANCE, Level.DEPT_HEAD),
    ("farhan.ali", "Farhan Ali", Department.HSE, Level.MANAGER),
    ("meera.pillai", "Meera Pillai", Department.HSE, Level.SENIOR_MANAGER),
    ("omar.hassan", "Omar Hassan", Department.HSE, Level.DEPT_HEAD),
    ("sanjay.gupta", "Sanjay Gupta", Department.PRODUCTION, Level.MANAGER),
    ("leela.menon", "Leela Menon", Department.PRODUCTION, Level.SENIOR_MANAGER),
    ("arjun.reddy", "Arjun Reddy", Department.PRODUCTION, Level.DEPT_HEAD),
]


def seed(session: Session) -> None:
    if session.exec(select(User)).first() is not None:
        return  # already seeded

    users_by_username = {}
    for username, full_name, department, level in USERS:
        user = User(
            username=username,
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name=full_name,
            department=department,
            level=level,
        )
        session.add(user)
        users_by_username[username] = user
    session.commit()
    for user in users_by_username.values():
        session.refresh(user)

    workflows_by_dept = {}
    for wf in WORKFLOWS:
        workflow = Workflow(
            key=wf["key"],
            name=wf["name"],
            department=wf["department"],
            description=wf["description"],
            sap_systems=wf["sap_systems"],
            non_sap_systems=wf["non_sap_systems"],
            steps_json=json.dumps(wf["steps"]),
            exception_reasons_json=json.dumps(wf["exceptions"]),
        )
        session.add(workflow)
        workflows_by_dept.setdefault(wf["department"], []).append(workflow)
    session.commit()
    for wfs in workflows_by_dept.values():
        for wf in wfs:
            session.refresh(wf)

    # Grant Manager-level users access to the first two workflows in their
    # department, leaving the last one for a Dept Head/Admin to grant live
    # during the demo (illustrates access management).
    admin_user = users_by_username["admin"]
    for username, full_name, department, level in USERS:
        if level != Level.MANAGER:
            continue
        dept_workflows = workflows_by_dept.get(department, [])
        for wf in dept_workflows[:2]:
            session.add(
                WorkflowAccess(
                    user_id=users_by_username[username].id,
                    workflow_id=wf.id,
                    granted_by_id=admin_user.id,
                )
            )
    session.commit()
