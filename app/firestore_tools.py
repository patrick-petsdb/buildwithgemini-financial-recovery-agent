"""Firestore tools for Financial Scam Recovery Social Worker Agent.

Note: Project ID is hardcoded as a string to ensure stability across
local development and Google Cloud Agent Platform / Agent Runtime environments.
"""

from typing import Any
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-44680d3a8b6a"


def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client configured with the hardcoded project ID."""
    return firestore.Client(project=PROJECT_ID)


def list_support_resources(category: str = "") -> list[dict[str, Any]]:
    """List all official scam recovery and victim relief support resources from Firestore.

    Args:
        category: Optional category filter (e.g. 'Government & Legal Reporting',
                  'Identity Protection', 'Federal Law Enforcement',
                  'Banking Regulatory Disputes', 'Emotional Support & Social Services').

    Returns:
        A list of support resource dictionaries containing name, contact info,
        website, priority, and actionable steps.
    """
    db = get_firestore_client()
    collection_ref = db.collection("support_resources")
    docs = collection_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        if category:
            if category.lower() in data.get("category", "").lower():
                results.append(data)
        else:
            results.append(data)
    return results


def search_support_resources_by_scam_type(scam_type: str) -> list[dict[str, Any]]:
    """Search verified reporting and recovery resources for a specific scam type.

    Args:
        scam_type: The type of scam (e.g. 'wire_fraud', 'crypto_investment',
                   'imposter', 'identity_theft', 'phishing', 'bank_unauthorized_transfer',
                   'romance_scam', 'tech_support').

    Returns:
        A list of relevant support resources and reporting agency recommendations.
    """
    db = get_firestore_client()
    docs = db.collection("support_resources").stream()

    query_lower = scam_type.lower().replace(" ", "_")
    results = []
    for doc in docs:
        data = doc.to_dict()
        types = [t.lower() for t in data.get("scam_types", [])]
        if "all" in types or any(query_lower in t or t in query_lower for t in types):
            results.append(data)

    # Fallback to all if no exact keyword match
    if not results:
        results = [doc.to_dict() for doc in db.collection("support_resources").stream()]
    return results


def get_recovery_case(case_id: str) -> dict[str, Any]:
    """Retrieve an existing victim recovery case and its action checklist from Firestore.

    Args:
        case_id: The unique ID of the recovery case (e.g. 'CASE-2026-001').

    Returns:
        The recovery case data dictionary, or a message if not found.
    """
    db = get_firestore_client()
    doc = db.collection("recovery_cases").document(case_id).get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"Case ID '{case_id}' not found."}


def save_or_update_recovery_case(
    case_id: str,
    victim_alias: str,
    scam_type: str,
    financial_loss: float,
    status: str,
    compromised_bank: str = "",
    action_checklist: list[dict[str, Any]] = None,
    notes: str = ""
) -> dict[str, Any]:
    """Save or update a victim's incident recovery case and checklist in Firestore.

    Args:
        case_id: Unique case identifier (e.g. 'CASE-2026-001').
        victim_alias: First name or alias of the victim for privacy (e.g. 'Alex M.').
        scam_type: Type of scam (e.g. 'imposter_bank_fraud', 'crypto_wire_scam', 'phishing').
        financial_loss: Total dollar amount lost or in dispute.
        status: Current status (e.g. 'triage_in_progress', 'bank_dispute_filed', 'police_reported', 'stabilized').
        compromised_bank: Name of the bank or payment platform involved.
        action_checklist: List of checklist items, each with 'task' (str) and 'completed' (bool).
        notes: Case notes, safety precautions, or next follow-up dates.

    Returns:
        A confirmation dictionary with the saved case data and status.
    """
    db = get_firestore_client()

    if action_checklist is None:
        action_checklist = [
            {"task": "Contact bank fraud department to freeze accounts", "completed": False},
            {"task": "File official fraud report at ReportFraud.ftc.gov", "completed": False},
            {"task": "Place credit freezes with Experian, Equifax, TransUnion", "completed": False},
            {"task": "Submit written bank dispute citing Regulation E", "completed": False}
        ]

    case_data = {
        "case_id": case_id,
        "victim_alias": victim_alias,
        "scam_type": scam_type,
        "financial_loss": financial_loss,
        "status": status,
        "compromised_bank": compromised_bank,
        "action_checklist": action_checklist,
        "notes": notes,
    }

    db.collection("recovery_cases").document(case_id).set(case_data, merge=True)
    return {"status": "success", "message": f"Case '{case_id}' successfully saved.", "case": case_data}
