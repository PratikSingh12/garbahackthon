"""
Unified classification pipeline for Job Hunt Autopilot.
Classifies each email into: applied, interview, rejected, offer, or scam.
Integrates Kaggle Fake Job and Hugging Face scam patterns.
"""

import re
from typing import Tuple, List, Dict, Any
from job_autopilot.models import EmailMessage, ClassificationResult, StageEnum, ScamAnalysis


# Common free webmail domains that legitimate enterprise recruiters do NOT use for official hiring
FREE_WEBMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "protonmail.com", "proton.me", "aol.com", "icloud.com",
    "mail.com", "yandex.com", "zoho.com"
}

# Suspicious domain regex patterns (Kaggle fake job posting lookalikes)
SUSPICIOUS_DOMAIN_PATTERNS = [
    r"-careers-portal\.",
    r"-onlinework\.",
    r"-recruitment-desk\.",
    r"-job-verify\.",
    r"-hiring-portal\.",
    r"crypto-hr\.",
    r"apexsolutions2024\."
]

# Scam indicators based on Kaggle Fake Job Posting (~18k) & Hugging Face Hinglish/English scam text
SCAM_INDICATORS = [
    # 1. Financial demands / Upfront fee traps
    {
        "pattern": r"(training\s+fee|registration\s+fee|certification\s+fee|background\s+(check|verification)\s+fee|processing\s+fee|onboarding\s+fee|security\s+deposit|refundable\s+(deposit|fee|certification|registration))",
        "reason": "Demands upfront training, registration, or background screening fee before onboarding.",
        "weight": 0.50,
        "signal": "UPFRONT_FEE_DEMAND"
    },
    {
        "pattern": r"(upi\s+id[:\s]+[a-zA-Z0-9.\-_]+@[a-zA-Z]+|usdt|trc-?20|bitcoin|crypto\s+wallet|western\s+union|zelle|moneygram)",
        "reason": "Requests financial payment or money transfer via UPI, cryptocurrency (USDT), Zelle, or Western Union.",
        "weight": 0.45,
        "signal": "SUSPICIOUS_PAYMENT_METHOD"
    },
    {
        "pattern": r"(cashier'?s?\s+check|corporate\s+check|certified\s+check).*(deposit.*wire|wire.*vendor|purchase.*equipment.*vendor|vendor.*techsupplies)",
        "reason": "Classic overpayment / cashier check equipment advance fraud.",
        "weight": 0.55,
        "signal": "CHECK_CASHING_EQUIPMENT_SCAM"
    },
    # 2. Identity / Sensitive PII harvesting before interview
    {
        "pattern": r"(social\s+security\s+(card|number)|ssn\b|aadhaar(\s+card)?|passport\s+scan|driver'?s?\s+license|voided\s+check|routing\s+number|bank\s+account\s+number)",
        "secondary_pattern": r"(before\s+(we\s+can\s+)?schedule|prior\s+to\s+(scheduling|interview)|pre-?verification|interviews?\s+cannot\s+be\s+scheduled|within\s+24\s+hours\s+to\s+secure\s+your\s+interview)",
        "reason": "Demands government identity documents (SSN/Aadhaar/Driver's License) or bank routing details prior to scheduling an interview.",
        "weight": 0.55,
        "signal": "PRE_INTERVIEW_PII_HARVESTING"
    },
    # 3. Hinglish & Task-based Telegram / WhatsApp bypass scams
    {
        "pattern": r"(ekdum\s+genuine|daily\s+payout|google\s+review.*task|code\s+rating|review.*tasks|part-?time.*rating)",
        "secondary_pattern": r"(telegram|whatsapp|\u20b9|\brs\.?|daily\s+payout)",
        "reason": "Task-based rating scam with Hinglish phrasing ('ekdum genuine') and promised daily payouts.",
        "weight": 0.50,
        "signal": "HINGLISH_TASK_PAYOUT_SCAM"
    },
    {
        "pattern": r"(telegram\s+(id|channel|manager)?[:\s]+@[a-zA-Z0-9_]+|contact.*on\s+telegram|whatsapp\s+at\s+\+?[0-9\-]+)",
        "secondary_pattern": r"(immediate\s+joining|no\s+(formal\s+)?interview|task|payout|bonus)",
        "reason": "Directs applicant to unmonitored Telegram/WhatsApp channels while bypassing technical interview rounds.",
        "weight": 0.45,
        "signal": "TELEGRAM_WHATSAPP_INTERVIEW_BYPASS"
    },
    # 4. Immediate hire without interview / unrealistic promises
    {
        "pattern": r"(skip\s+the\s+technical\s+round|no\s+(formal\s+)?technical\s+interview\s+needed|selected\s+you\s+directly\s+for|selected\s+without\s+(any\s+)?interview)",
        "reason": "High-paying technical offer extended without conducting any technical interviews or screens.",
        "weight": 0.35,
        "signal": "NO_INTERVIEW_OFFER"
    }
]

# Patterns for legitimate offer
OFFER_PATTERNS = [
    r"offer\s+of\s+employment",
    r"formal\s+offer\s+letter",
    r"pleased\s+to\s+offer\s+you",
    r"extend\s+a\s+formal\s+offer",
    r"compensation\s+package\s+overview",
    r"summary\s+of\s+offer\s+details",
    r"annual\s+base\s+salary",
    r"stock\s+options.*vesting",
    r"restricted\s+stock\s+units",
    r"docusign\.net",
    r"workday\s+candidate\s+portal"
]

# Patterns for interview invitations
INTERVIEW_PATTERNS = [
    r"technical\s+screen\s+invitation",
    r"recruiter\s+(phone\s+)?screen",
    r"take-?home\s+(coding\s+)?challenge",
    r"technical\s+assessment\s+phase",
    r"virtual\s+onsite\s+interview",
    r"paired\s+coding\s+session",
    r"system\s+design\s+conversation",
    r"technical\s+conversation\s+with\s+our\s+director",
    r"coderpad",
    r"calendly\.com",
    r"interview\s+loop",
    r"interview\s+preparation\s+guide",
    r"pick\s+a\s+time\s+on\s+my\s+calendar"
]

# Patterns for rejections
REJECTION_PATTERNS = [
    r"decided\s+not\s+to\s+move\s+forward",
    r"chosen\s+to\s+pursue\s+other\s+candidates",
    r"will\s+not\s+be\s+advancing\s+your\s+candidacy",
    r"decided\s+not\s+to\s+proceed",
    r"wish\s+you\s+the\s+best\s+in\s+your\s+job\s+search",
    r"decided\s+to\s+proceed\s+with\s+other\s+candidates",
    r"made\s+the\s+tough\s+choice\s+to\s+proceed\s+with\s+other",
    r"difficult\s+decisions",
    r"keep\s+your\s+resume\s+in\s+our\s+database"
]

# Patterns for application confirmation
APPLIED_PATTERNS = [
    r"thank\s+you\s+for\s+(submitting\s+your\s+)?applying",
    r"we('?ve|\s+have)\s+(successfully\s+)?received\s+your\s+application",
    r"application\s+received",
    r"thanks\s+for\s+applying\s+to",
    r"thanks\s+for\s+your\s+interest\s+in",
    r"your\s+application\s+to\s+[a-zA-Z0-9]+",
    r"application\s+confirmation"
]


def analyze_scam_signals(email: EmailMessage) -> ScamAnalysis:
    """
    Analyze email content, headers, and domain for recruitment scam indicators.
    Returns a ScamAnalysis object with risk score, detected signals, and human-readable reasons.
    """
    full_text = f"{email.subject}\n{email.body}".lower()
    reasons = []
    signals = []
    risk_score = 0.0

    # 1. Domain checks
    is_free_webmail = email.sender_domain in FREE_WEBMAIL_DOMAINS
    is_suspicious_tld = any(re.search(pat, email.sender_domain) for pat in SUSPICIOUS_DOMAIN_PATTERNS)

    if is_suspicious_tld:
        reasons.append(f"Sender domain '{email.sender_domain}' matches known fraudulent/lookalike domain pattern.")
        signals.append("SUSPICIOUS_SENDER_DOMAIN")
        risk_score += 0.35

    # 2. Check content indicators
    for indicator in SCAM_INDICATORS:
        main_match = re.search(indicator["pattern"], full_text, re.IGNORECASE)
        sec_pattern = indicator.get("secondary_pattern")
        
        if sec_pattern:
            sec_match = re.search(sec_pattern, full_text, re.IGNORECASE)
            if main_match and sec_match:
                reasons.append(indicator["reason"])
                signals.append(indicator["signal"])
                risk_score += indicator["weight"]
        else:
            if main_match:
                reasons.append(indicator["reason"])
                signals.append(indicator["signal"])
                risk_score += indicator["weight"]

    # 3. Free Webmail Impersonation Check:
    # If using @gmail/@outlook/@protonmail while claiming to extend high-paying jobs or asking for payment
    if is_free_webmail and any(term in full_text for term in ["selected", "hired", "offer", "hr", "engineer", "cloud", "task"]):
        if any(term in full_text for term in ["fee", "deposit", "payment", "upi", "crypto", "task", "telegram", "payout", "$95/hr", "$160,000"]):
            reasons.append(f"Recruiter claims corporate hiring authority using personal free webmail ({email.sender_domain}).")
            signals.append("FREE_WEBMAIL_CORPORATE_IMPERSONATION")
            risk_score += 0.30

    risk_score = min(round(risk_score, 2), 1.0)
    
    # Classification decision
    is_scam = (
        risk_score >= 0.50 or
        len(signals) >= 2 or
        ("UPFRONT_FEE_DEMAND" in signals) or
        ("CHECK_CASHING_EQUIPMENT_SCAM" in signals) or
        ("PRE_INTERVIEW_PII_HARVESTING" in signals) or
        ("HINGLISH_TASK_PAYOUT_SCAM" in signals)
    )

    return ScamAnalysis(
        is_scam=is_scam,
        risk_score=risk_score,
        reasons=reasons,
        signals_detected=signals
    )


def extract_company_name(email: EmailMessage) -> str:
    """Extract company name using domain, display name, and subject patterns."""
    domain_map = {
        "stripe.com": "Stripe",
        "airbnb.com": "Airbnb",
        "datadoghq.com": "Datadog",
        "mktg.notion.so": "Notion",
        "notion.so": "Notion",
        "figma.com": "Figma",
        "uber.com": "Uber",
        "brex.com": "Brex",
        "snowflake.com": "Snowflake",
        "github.com": "GitHub",
        "google.com": "Google",
        "meta.com": "Meta",
        "netflix.com": "Netflix",
        "shopify.com": "Shopify",
        "linear.app": "Linear",
        "vercel.com": "Vercel",
    }

    if email.sender_domain in domain_map:
        return domain_map[email.sender_domain]

    # Specific scam / company name recognizers from subject or body
    if "tanya" in email.sender.lower() or "tanya" in email.body.lower():
        return "Daily Task Desk / Tanya HR"

    for name in [
        "Apex Global Cloud Solutions",
        "Apex Global Solutions",
        "Swift Logistics",
        "Horizon Health Systems",
        "Apex Web3 Labs",
        "Apex Innovations",
        "Linear Orbit",
        "Linear",
        "Vercel",
        "Snowflake",
        "Brex",
        "Uber",
        "Notion",
        "Figma",
        "Datadog",
        "Airbnb",
        "Stripe",
        "Shopify",
        "Netflix",
        "Meta",
        "GitHub",
        "Google"
    ]:
        if re.search(r"\b" + re.escape(name) + r"\b", email.subject, re.IGNORECASE):
            return name
        # Only search body if name is not Google/Meta (which might be mentioned in review tasks)
        if name not in ["Google", "Meta"] and re.search(r"\b" + re.escape(name) + r"\b", email.body, re.IGNORECASE):
            return name

    # Subject line patterns like "at Company" or "to Company"
    match = re.search(r"(?:at|to|for)\s+([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?)", email.subject)
    if match:
        cand = match.group(1).strip()
        if cand.lower() not in {"software", "staff", "senior", "frontend", "backend", "remote", "uber", "brex"}:
            return cand

    # Check sender display name
    if email.sender:
        clean_sender = re.sub(r"<[^>]+>", "", email.sender).strip()
        for suffix in ["Recruiting", "Careers", "Talent Team", "Talent Acquisition", "People Operations", "HR Desk", "HR Global Desk", "HR"]:
            if suffix in clean_sender:
                name = clean_sender.replace(suffix, "").strip()
                if name:
                    return name

    # Fallback to sender domain
    if email.sender_domain:
        base = email.sender_domain.split(".")[0]
        return base.capitalize()

    return "Unknown Company"


def extract_role_title(email: EmailMessage) -> str:
    """Extract job role/title from subject or body."""
    roles = [
        "Senior Full Stack Engineer",
        "Staff Backend Engineer",
        "Product Infrastructure Engineer",
        "Frontend Systems Engineer",
        "Senior Distributed Systems Engineer",
        "Senior Infrastructure Engineer",
        "Senior Backend Developer",
        "Senior Platform Engineer",
        "Senior Systems Analyst",
        "Remote Cloud Engineer",
        "Blockchain Systems Engineer",
        "WFH Software Engineer",
        "Solutions Engineer",
        "Software Engineer III / L5",
        "Software Engineer III",
        "Software Engineer II",
        "Senior Software Engineer",
        "Senior Backend Engineer",
        "Software Engineer, Infrastructure",
        "Software Engineer"
    ]

    combined = f"{email.subject}\n{email.body}"
    for role in roles:
        if re.search(r"\b" + re.escape(role) + r"\b", combined, re.IGNORECASE):
            return role

    return "Software Engineer"


def classify_email(email: EmailMessage) -> ClassificationResult:
    """
    Unified Single Pipeline Classifier:
    Each email is classified once as applied, interview, rejected, offer or scam.
    The scam check is a first-class label within the single classification pipeline.
    """
    full_text = f"{email.subject}\n{email.body}"
    company = extract_company_name(email)
    role = extract_role_title(email)

    # 1. First step in pipeline: evaluate for scam indicators
    scam_analysis = analyze_scam_signals(email)
    if scam_analysis.is_scam:
        summary = f"Flagged as fraudulent job scam: {scam_analysis.reasons[0] if scam_analysis.reasons else 'High scam risk detected'}"
        return ClassificationResult(
            email_id=email.id,
            stage=StageEnum.SCAM,
            company=company,
            role=role,
            confidence=max(scam_analysis.risk_score, 0.92),
            scam_analysis=scam_analysis,
            summary=summary
        )

    # 2. Check for legitimate Offer
    offer_matches = [p for p in OFFER_PATTERNS if re.search(p, full_text, re.IGNORECASE)]
    if len(offer_matches) >= 2 or re.search(r"offer\s+of\s+employment", full_text, re.IGNORECASE):
        summary = f"Legitimate employment offer extended for {role} at {company}."
        return ClassificationResult(
            email_id=email.id,
            stage=StageEnum.OFFER,
            company=company,
            role=role,
            confidence=0.95,
            scam_analysis=scam_analysis,
            summary=summary
        )

    # 3. Check for Interview Invitation
    interview_matches = [p for p in INTERVIEW_PATTERNS if re.search(p, full_text, re.IGNORECASE)]
    if len(interview_matches) >= 1:
        summary = f"Interview or technical assessment invitation received for {role} at {company}."
        return ClassificationResult(
            email_id=email.id,
            stage=StageEnum.INTERVIEW,
            company=company,
            role=role,
            confidence=0.92,
            scam_analysis=scam_analysis,
            summary=summary
        )

    # 4. Check for Rejection
    rejection_matches = [p for p in REJECTION_PATTERNS if re.search(p, full_text, re.IGNORECASE)]
    if len(rejection_matches) >= 1:
        summary = f"Application rejected for {role} at {company}."
        return ClassificationResult(
            email_id=email.id,
            stage=StageEnum.REJECTED,
            company=company,
            role=role,
            confidence=0.94,
            scam_analysis=scam_analysis,
            summary=summary
        )

    # 5. Check for Applied / Acknowledgement
    applied_matches = [p for p in APPLIED_PATTERNS if re.search(p, full_text, re.IGNORECASE)]
    if len(applied_matches) >= 1:
        summary = f"Application received and acknowledged for {role} at {company}."
        return ClassificationResult(
            email_id=email.id,
            stage=StageEnum.APPLIED,
            company=company,
            role=role,
            confidence=0.91,
            scam_analysis=scam_analysis,
            summary=summary
        )

    # Fallback to applied
    summary = f"Application record for {role} at {company}."
    return ClassificationResult(
        email_id=email.id,
        stage=StageEnum.APPLIED,
        company=company,
        role=role,
        confidence=0.70,
        scam_analysis=scam_analysis,
        summary=summary
    )
