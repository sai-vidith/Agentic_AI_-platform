import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


UNKNOWN_VALUES = {"", "unknown", "unavailable", "n/a", "none", "null"}


def clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def is_unknown(value: Any) -> bool:
    return clean_text(value).lower() in UNKNOWN_VALUES


def normalize_url(value: Any, *, linkedin_kind: Optional[str] = None) -> str:
    url = clean_text(value)
    if is_unknown(url):
        return ""
    if url.startswith("//"):
        url = f"https:{url}"
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    url = url.split("?")[0].rstrip("/")

    if linkedin_kind:
        match = re.search(r"linkedin\.com/(company|in)/([a-z0-9\-_%]+)", url.lower())
        if not match or match.group(1) != linkedin_kind:
            return ""
        slug = match.group(2).strip("/")
        if slug in {"unavailable", "search", "jobs", "pub", "login"}:
            return ""
        return f"https://www.linkedin.com/{linkedin_kind}/{slug}"

    return url


def extract_domain(value: Any) -> str:
    url = normalize_url(value)
    if not url:
        return ""
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def is_aggregator_url(value: Any) -> bool:
    url = clean_text(value).lower()
    domain = extract_domain(url)
    aggregators = [
        "globaldata",
        "zoominfo",
        "apollo.io",
        "crunchbase",
        "dnb.com",
        "pitchbook",
        "owler",
        "rocketreach",
        "lusha",
        "clearbit",
        "linkedin.com/company",
        "similarweb",
        "datanyze",
    ]
    return any(agg in domain or agg in url for agg in aggregators)


def is_shallow_company_url(value: Any) -> bool:
    url = normalize_url(value)
    if not url:
        return False
    try:
        path = urlparse(url).path.strip("/")
        return path in ("", "about", "home", "about-us", "contact")
    except Exception:
        return False


def coerce_int(value: Any) -> Optional[int]:
    if value is None or is_unknown(value):
        return None
    if isinstance(value, int):
        return value
    try:
        digits = re.sub(r"[^0-9]", "", str(value))
        return int(digits) if digits else None
    except Exception:
        return None


def normalize_company_details(company_name: str, details: Dict[str, Any]) -> Dict[str, Any]:
    details = dict(details or {})
    name = clean_text(details.get("name")) or clean_text(company_name, "Unknown Company")
    website = normalize_url(details.get("website") or details.get("domain"))
    linkedin = normalize_url(details.get("linkedin") or details.get("linkedin_company_url"), linkedin_kind="company")

    tech_stack = details.get("tech_stack") or []
    if isinstance(tech_stack, str):
        tech_stack = [item.strip() for item in tech_stack.split(",") if item.strip()]
    if not isinstance(tech_stack, list):
        tech_stack = []

    recent_funding = details.get("recent_funding")
    if not isinstance(recent_funding, dict):
        recent_funding = None

    return {
        **details,
        "name": name,
        "industry": clean_text(details.get("industry"), "Unknown"),
        "website": website,
        "linkedin": linkedin,
        "employees": coerce_int(details.get("employees")),
        "founded": coerce_int(details.get("founded")),
        "hq": clean_text(details.get("hq") or details.get("headquarters"), "Unknown"),
        "description": clean_text(details.get("description")),
        "tech_stack": tech_stack,
        "current_hr_tool": clean_text(details.get("current_hr_tool"), "unknown"),
        "growth_rate": clean_text(details.get("growth_rate")),
        "recent_funding": recent_funding,
    }


def normalize_contact(contact: Dict[str, Any], *, default_source_url: str = "") -> Dict[str, Any]:
    contact = dict(contact or {})
    name = clean_text(contact.get("name") or contact.get("full_name"))
    title = clean_text(contact.get("title"), "Executive")
    linkedin = normalize_url(contact.get("linkedin") or contact.get("linkedin_url"), linkedin_kind="in")
    email = clean_text(contact.get("email"), "unknown")
    phone = clean_text(contact.get("phone"), "unknown")
    source_url = normalize_url(contact.get("source_url") or default_source_url)

    return {
        **contact,
        "name": name,
        "full_name": name,
        "title": title,
        "persona_match": clean_text(contact.get("persona_match") or contact.get("role"), "UNKNOWN"),
        "email": email,
        "email_confidence": contact.get("email_confidence"),
        "phone": phone,
        "linkedin": linkedin,
        "linkedin_url": linkedin,
        "source_url": source_url,
        "confidence": clean_text(contact.get("confidence"), "MEDIUM").upper(),
        "extraction_method": clean_text(contact.get("extraction_method"), "structured_enrichment"),
        "persona_rank": contact.get("persona_rank"),
        "pii_fields_redacted": contact.get("pii_fields_redacted", []),
        "raw_email": contact.get("raw_email"),
        "raw_phone": contact.get("raw_phone"),
    }


def dedupe_contacts(contacts: List[Dict[str, Any]], *, default_source_url: str = "") -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen = set()
    for contact in contacts or []:
        normalized = normalize_contact(contact, default_source_url=default_source_url)
        name_key = normalized.get("name", "").lower()
        linkedin_key = normalized.get("linkedin", "").lower()
        if not name_key and not linkedin_key:
            continue
        key = linkedin_key or name_key
        if key in seen:
            continue
        seen.add(key)
        normalized["persona_rank"] = normalized.get("persona_rank") or len(deduped) + 1
        deduped.append(normalized)
    return deduped


def infer_committee_role(title: str) -> str:
    title_lower = clean_text(title).lower()
    if any(k in title_lower for k in ("chief", "vp", "president", "cpo", "cfo", "cio", "cto", "ceo", "head of")):
        return "Decision Maker"
    if any(k in title_lower for k in ("director", "manager", "lead", "architect", "engineer")):
        return "Influencer"
    return "Gatekeeper"
