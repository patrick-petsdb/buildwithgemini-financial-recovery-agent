"""Seed script to populate Firestore collections for Financial Scam Recovery Agent.

Uses hardcoded project ID to prevent Agent Platform / ADC runtime project number issues.
"""

from google.cloud import firestore

# IMPORTANT: Hardcoded Project ID string
PROJECT_ID = "qwiklabs-gcp-03-44680d3a8b6a"


def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)

    # 1. Seed Support Resources
    resources = [
        {
            "id": "ftc_fraud_report",
            "name": "Federal Trade Commission (FTC) ReportFraud",
            "category": "Government & Legal Reporting",
            "scam_types": ["imposter", "identity_theft", "phishing", "tech_support", "online_shopping"],
            "phone": "1-877-382-4357",
            "website": "https://reportfraud.ftc.gov",
            "description": "Official federal agency for reporting consumer fraud, scams, and deceptive business practices. Generates an official report essential for bank disputes.",
            "action_steps": [
                "Submit online incident report at reportfraud.ftc.gov",
                "Save your official FTC Reference Number",
                "Provide FTC report copy to bank fraud department"
            ],
            "priority": "Immediate (within 24-48 hours)"
        },
        {
            "id": "ic3_cyber_fraud",
            "name": "FBI Internet Crime Complaint Center (IC3)",
            "category": "Federal Law Enforcement",
            "scam_types": ["wire_fraud", "crypto_investment", "romance_scam", "business_email_compromise"],
            "phone": "N/A (Online Portal)",
            "website": "https://www.ic3.gov",
            "description": "Federal law enforcement hub for investigating cyber-enabled financial fraud, large unauthorized wires, and cryptocurrency investment scams.",
            "action_steps": [
                "Gather wire transaction details and crypto wallet addresses",
                "File detailed complaint on IC3.gov",
                "Request IC3 Recovery Asset Team (RAT) intervention if wire was sent <72h ago"
            ],
            "priority": "Critical for wire / crypto losses"
        },
        {
            "id": "identity_theft_gov",
            "name": "IdentityTheft.gov (FTC Recovery Hub)",
            "category": "Identity Protection",
            "scam_types": ["identity_theft", "account_takeover", "ssn_compromise"],
            "phone": "1-877-438-4338",
            "website": "https://www.identitytheft.gov",
            "description": "National resource for personalized identity theft recovery plans, pre-filled dispute letters, and credit bureau freeze guides.",
            "action_steps": [
                "Place free 1-year fraud alerts with Equifax, Experian, TransUnion",
                "Freeze credit files with all 3 major bureaus",
                "File Identity Theft Affidavit"
            ],
            "priority": "Immediate"
        },
        {
            "id": "cfpb_financial_protection",
            "name": "Consumer Financial Protection Bureau (CFPB)",
            "category": "Banking Regulatory Disputes",
            "scam_types": ["bank_unauthorized_transfer", "denied_bank_dispute", "credit_card_fraud", "loan_scam"],
            "phone": "1-855-411-2372",
            "website": "https://www.consumerfinance.gov/complaint",
            "description": "Enforces Regulation E and Truth in Lending Act. Handles consumer complaints when financial institutions improperly deny reimbursement for fraudulent transactions.",
            "action_steps": [
                "Submit formal dispute to bank first and allow statutory investigation window",
                "If bank denies claim without proper explanation, file CFPB complaint",
                "Attach all bank correspondence, police reports, and FTC filings"
            ],
            "priority": "Secondary / Escalation"
        },
        {
            "id": "victim_connect_hotline",
            "name": "VictimConnect Resource Center",
            "category": "Emotional Support & Social Services",
            "scam_types": ["all", "romance_scam", "elder_fraud"],
            "phone": "1-855-484-2846",
            "website": "https://victimconnect.org",
            "description": "Confidential referral service providing empathetic emotional support, trauma-informed guidance, and local victim advocacy referrals.",
            "action_steps": [
                "Call or text for confidential emotional triage",
                "Request local financial counseling or social worker referrals"
            ],
            "priority": "Anytime"
        }
    ]

    print("Seeding 'support_resources' collection...")
    for res in resources:
        doc_id = res["id"]
        db.collection("support_resources").document(doc_id).set(res)
        print(f"  ✓ Seeded resource: {res['name']} ({doc_id})")

    # 2. Seed Sample Recovery Case
    sample_case = {
        "case_id": "CASE-2026-001",
        "victim_alias": "Alex M.",
        "scam_type": "imposter_bank_fraud",
        "financial_loss": 3200.0,
        "date_reported": "2026-11-12",
        "status": "triage_in_progress",
        "compromised_bank": "Chase Bank",
        "action_checklist": [
            {"task": "Call Chase Fraud Department to freeze compromised checking account", "completed": True},
            {"task": "File fraud report with FTC at ReportFraud.ftc.gov", "completed": True},
            {"task": "Place credit freezes at Experian, Equifax, TransUnion", "completed": False},
            {"task": "Submit written Reg E dispute letter with FTC report attached", "completed": False}
        ],
        "notes": "Victim received spoofed bank SMS asking to authorize Zelle transfer to 'fraud department'. Advised to secure email passwords and freeze credit."
    }

    print("Seeding 'recovery_cases' collection...")
    db.collection("recovery_cases").document(sample_case["case_id"]).set(sample_case)
    print(f"  ✓ Seeded sample case: {sample_case['case_id']}")

    print("\n✅ Firestore seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
