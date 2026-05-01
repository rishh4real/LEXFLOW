"""
services/llm_service.py
Claude API calls for extraction and action plan generation.
"""
import os, json
import anthropic
from dotenv import load_dotenv
load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-5"

EXTRACTION_PROMPT = """You are a legal AI. Extract structured data from this court judgment.
Return ONLY valid JSON with these exact fields:
{
  "case_number": "...",
  "parties": "...",
  "date_of_order": "YYYY-MM-DD",
  "key_directions": "...",
  "compliance_deadline": "YYYY-MM-DD",
  "appeal_window": "...",
  "responsible_department": "...",
  "action_plan": {
    "recommendation": "comply or appeal",
    "urgency": "high or medium or low",
    "required_action": "..."
  },
  "source_references": {
    "compliance_deadline": "exact sentence from text",
    "responsible_department": "exact sentence from text"
  }
}

Court judgment text:
"""

def extract_case(text: str) -> dict:
    """Send PDF text to Claude and get structured extraction back."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT + text[:12000]}]
    )
    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
