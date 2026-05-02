"""
Email tools — mailto builder, Gmail compose URL, word/char counting.
"""
import urllib.parse


def build_mailto_link(
    to: str,
    subject: str,
    body: str,
    from_email: str = "",
) -> str:
    """Build RFC 2368-compliant mailto: URL for one-click email client open."""
    params = {"subject": subject, "body": body}
    if from_email:
        params["from"] = from_email
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"mailto:{urllib.parse.quote(to)}?{query}"


def build_gmail_url(to: str, subject: str, body: str) -> str:
    """Build Gmail compose URL for one-click open in browser."""
    params = {
        "view": "cm",
        "fs": "1",
        "to": to,
        "su": subject,
        "body": body,
    }
    return "https://mail.google.com/mail/?" + urllib.parse.urlencode(params)


def count_words(text: str) -> int:
    return len(text.split())


def truncate_to_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


def detect_ai_cliches(text: str) -> list[str]:
    """Return list of AI-sounding phrases found in the text."""
    cliches = [
        "i hope this email finds you well",
        "i am writing to express my interest",
        "please find attached",
        "i am passionate about",
        "leverage my skills",
        "synergize",
        "thought leadership",
        "as per my last email",
        "as an ai language model",
        "i would like to bring to your attention",
        "i am excited to apply",
        "i am thrilled to",
        "dynamic and motivated",
        "results-driven professional",
        "proactive team player",
    ]
    lower = text.lower()
    return [c for c in cliches if c in lower]
