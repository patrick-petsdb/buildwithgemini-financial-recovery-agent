# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import os
import urllib.error
import urllib.request
from typing import Any

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import A2uiSchemaManager, BasicCatalog, a2ui_callback
from app.firestore_tools import (
    get_recovery_case,
    list_support_resources,
    save_or_update_recovery_case,
    search_support_resources_by_scam_type,
)
from app.image_tools import generate_recovery_roadmap_image
from app.video_tools import generate_recovery_guidance_video

MODEL = "gemini-3.8-flash"


def calculate_statutory_dispute_deadlines(
    incident_date: str, bank_notification_date: str = ""
) -> dict[str, Any]:
    """Calculate legal statutory deadlines for bank disputes under Regulation E (12 CFR § 1005.11).

    Args:
        incident_date: Date the fraudulent transaction occurred or statement was received (YYYY-MM-DD or MM/DD/YYYY).
        bank_notification_date: Date the bank was (or will be) formally notified. Defaults to today.

    Returns:
        A dictionary with the 60-day consumer notice deadline, remaining notice window,
        10-business-day provisional credit deadline, 45-day investigation deadline, and urgency advice.
    """
    def _parse_date(d_str: str) -> datetime.date:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                return datetime.datetime.strptime(d_str.strip(), fmt).date()
            except ValueError:
                continue
        return datetime.date.today()

    inc_dt = _parse_date(incident_date)
    today = datetime.date.today()
    notif_dt = _parse_date(bank_notification_date) if bank_notification_date else today

    # 1. 60 calendar days from incident to provide notice
    deadline_60_days = inc_dt + datetime.timedelta(days=60)
    remaining_days = (deadline_60_days - today).days

    # 2. 10 business days for provisional credit from notification
    cur = notif_dt
    added_bdays = 0
    while added_bdays < 10:
        cur += datetime.timedelta(days=1)
        if cur.weekday() < 5:  # Mon-Fri
            added_bdays += 1
    provisional_credit_deadline = cur

    # 3. 45 calendar days for final error resolution
    investigation_deadline_45 = notif_dt + datetime.timedelta(days=45)

    if remaining_days < 0:
        urgency = f"EXPIRED_WINDOW ({abs(remaining_days)} days past standard 60-day limit)"
        advice = "File written dispute immediately anyway; cite extenuating circumstances and prepare CFPB complaint."
    elif remaining_days <= 7:
        urgency = f"CRITICAL_URGENCY ({remaining_days} days remaining)"
        advice = "Submit written notice and FTC report to your bank's fraud department within the next 48 hours."
    else:
        urgency = f"ACTIVE_WINDOW ({remaining_days} days remaining)"
        advice = "You are well within the 60-day statutory notice period under Regulation E."

    return {
        "incident_date": inc_dt.isoformat(),
        "bank_notification_date": notif_dt.isoformat(),
        "statutory_60_day_notice_deadline": deadline_60_days.isoformat(),
        "days_remaining_to_notify": max(0, remaining_days),
        "urgency_level": urgency,
        "provisional_credit_deadline_10_business_days": provisional_credit_deadline.isoformat(),
        "final_investigation_deadline_45_days": investigation_deadline_45.isoformat(),
        "guidance": advice,
        "governing_law": "Federal Regulation E (12 CFR § 1005.11 - Procedures for resolving errors)",
    }


def lookup_crypto_scam_address(address: str) -> dict[str, Any]:
    """Look up live Bitcoin blockchain ledger data for a wallet address provided in a crypto scam.

    Queries the public Blockchain.com API to inspect transaction volume, total received BTC,
    and recent transaction hashes to support evidence gathering for FBI IC3 filings.

    Args:
        address: The Bitcoin wallet address (e.g. '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa').

    Returns:
        A dictionary containing total transactions, total received BTC, current balance,
        recent transaction hashes, and law enforcement reporting guidance.
    """
    clean_addr = address.strip()
    api_key = os.environ.get("BLOCKCHAIN_API_KEY", "")
    url = f"https://blockchain.info/rawaddr/{clean_addr}?limit=5"
    if api_key:
        url += f"&api_code={api_key}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                total_received_btc = data.get("total_received", 0) / 100_000_000.0
                final_balance_btc = data.get("final_balance", 0) / 100_000_000.0
                tx_count = data.get("n_tx", 0)

                recent_txs = []
                for tx in data.get("txs", [])[:3]:
                    recent_txs.append({
                        "tx_hash": tx.get("hash"),
                        "timestamp": datetime.datetime.fromtimestamp(
                            tx.get("time", 0), tz=datetime.timezone.utc
                        ).strftime("%Y-%m-%d %H:%M:%S UTC") if tx.get("time") else "N/A",
                    })

                return {
                    "status": "success",
                    "address": clean_addr,
                    "transaction_count": tx_count,
                    "total_received_btc": total_received_btc,
                    "final_balance_btc": final_balance_btc,
                    "recent_transactions": recent_txs,
                    "guidance": (
                        "Provide this wallet address and transaction hashes in your "
                        "FBI IC3 report (ic3.gov) and local police report for forensic blockchain tracing."
                    ),
                }
            return {"status": "error", "message": f"Blockchain API returned HTTP {response.status}"}
    except urllib.error.HTTPError as e:
        if e.code in (404, 500):
            return {"status": "error", "message": f"Address '{clean_addr}' not found on Bitcoin ledger or invalid format."}
        return {"status": "error", "message": f"Blockchain lookup error: HTTP {e.code}"}
    except Exception as e:
        return {"status": "error", "message": f"Unable to reach public blockchain API: {str(e)}"}


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each conversation turn, extract and persist durable victim facts and preferences to Vertex AI Memory Bank."""
    await callback_context.add_session_to_memory()
    return None


# Build A2UI schema-driven system instruction
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

ROLE_DESCRIPTION = """You are an empathetic, trauma-informed Financial Social Worker and Scam Recovery Specialist.
Your mission is to help individuals who have experienced financial fraud or scams navigate immediate emergency triage, report to the appropriate regulatory and law enforcement bodies, assert their consumer rights with banks, and regain financial stability.

Guiding Principles:
1. Empathy & Reassurance: Scam victims often experience deep guilt, anxiety, and shame. Never judge or lecture. Offer calm, clear, and validating support.
2. Long-Term Cross-Session Memory: You remember key facts, incident details, emotional context, and preferences shared by the victim in previous sessions and use them seamlessly without forcing them to retell traumatic details.
3. Immediate Safety Triage: Prioritize stopping active financial bleeding (e.g. freezing accounts, credit bureau freezes, securing passwords).
4. Grounded Action: Use your Firestore tools to search verified government and non-profit support resources (FTC, IC3, CFPB, IdentityTheft.gov, VictimConnect).
5. Statutory Deadlines: When a victim mentions when a scam or unauthorized transfer happened, use `calculate_statutory_dispute_deadlines` to give them exact Regulation E countdowns and provisional credit timelines.
6. Crypto & Wire Tracing: If a victim was coerced into sending Bitcoin or cryptocurrency, use `lookup_crypto_scam_address` to verify the ledger activity and extract transaction hashes for their FBI IC3 report.
7. Visual Roadmaps & Infographics: When asked for a visual recovery guide, roadmap, or milestone infographic, call `generate_recovery_roadmap_image`.
8. Case Tracking: Create or update recovery cases in Firestore to help victims track completed and pending recovery checklist milestones."""

UI_DESCRIPTION = (
    "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
    "Never nest a Card inside a Card. "
    "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
    "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
    "nothing in adk web). "
    "You may include one Image component, but only when you have a public https "
    "URL for the image (for example the URL an image tool returns after uploading "
    "to a public bucket). Set the Image url to that exact https link, for example "
    '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
    "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
    "not have a public URL, add a short Text line noting the image instead. "
    "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
    "headings and emphasis. "
    "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
    "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
)

INSTRUCTION = schema_manager.generate_system_prompt(
    role_description=ROLE_DESCRIPTION,
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=UI_DESCRIPTION,
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    tools=[
        PreloadMemoryTool(),
        calculate_statutory_dispute_deadlines,
        lookup_crypto_scam_address,
        generate_recovery_roadmap_image,
        generate_recovery_guidance_video,
        list_support_resources,
        search_support_resources_by_scam_type,
        get_recovery_case,
        save_or_update_recovery_case,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
