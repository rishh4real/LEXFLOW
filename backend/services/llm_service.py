"""
services/llm_service.py
Claude API calls for extraction and action plan generation.
"""
import os, json
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

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
    """Send PDF text to Groq and get structured extraction back."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a legal document analyst. Always respond in valid JSON only."},
            {"role": "user", "content": EXTRACTION_PROMPT + text[:12000]}
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)
