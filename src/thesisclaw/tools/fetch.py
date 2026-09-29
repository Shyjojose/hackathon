from __future__ import annotations

import asyncio
import re
import time

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from thesisclaw.models.paper import Claim, PaperContent

# Rate limiter state: arXiv requires <= 1 request per 3 seconds
_LAST_REQUEST_TIMESTAMP: float = 0.0
_RATE_LIMIT_LOCK = asyncio.Lock()


async def _enforce_rate_limit(min_interval: float = 3.0) -> None:
    """Enforce strict rate limit between requests to respect arXiv guidelines."""
    global _LAST_REQUEST_TIMESTAMP
    async with _RATE_LIMIT_LOCK:
        now = time.time()
        elapsed = now - _LAST_REQUEST_TIMESTAMP
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        _LAST_REQUEST_TIMESTAMP = time.time()


def extract_arxiv_id(url_or_id: str) -> str:
    """Extract standard arXiv ID from a URL or raw ID string (e.g. '2404.12345')."""
    match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", url_or_id)
    if match:
        return match.group(1)
    # Handle older legacy formats like math/0211159
    match_legacy = re.search(r"([a-z\-]+/\d{7})", url_or_id)
    if match_legacy:
        return match_legacy.group(1)
    return url_or_id.strip()


def split_sections(text: str) -> dict[str, str]:
    """Split raw paper text into common academic sections."""
    sections: dict[str, str] = {}
    known_headings = [
        "abstract",
        "introduction",
        "background",
        "related work",
        "methodology",
        "methods",
        "system architecture",
        "experiments",
        "evaluation",
        "results",
        "discussion",
        "conclusion",
    ]

    pattern = r"(?im)^(?:\d+\.?\s*)?(" + "|".join(known_headings) + r")(?:\s*[:\-\n])"
    splits = re.split(pattern, text)

    if len(splits) <= 1:
        sections["body"] = text
        return sections

    # First segment before any heading
    if splits[0].strip():
        sections["header"] = splits[0].strip()

    for i in range(1, len(splits), 2):
        heading = splits[i].strip().lower()
        content = splits[i + 1].strip() if i + 1 < len(splits) else ""
        sections[heading] = content

    return sections


def extract_key_claims(text: str, max_claims: int = 5) -> list[Claim]:
    """Heuristic extraction of falsifiable claims with direct quotes."""
    claims: list[Claim] = []
    # Match sentences containing measurable engineering statements
    sentences = re.split(r"(?<=[.!?])\s+", text)
    claim_indicators = [
        "achieve",
        "decreas",
        "increas",
        "reduc",
        "outperform",
        "demonstrat",
        "quantiz",
        "wer",
        "rtf",
        "latency",
        "accuracy",
        "memory",
    ]

    for sent in sentences:
        sent_clean = sent.strip()
        if len(sent_clean) < 30 or len(sent_clean) > 300:
            continue
        lower_sent = sent_clean.lower()
        if any(ind in lower_sent for ind in claim_indicators):
            claims.append(
                Claim(
                    text=f"Paper reports: {sent_clean}",
                    quote=sent_clean,
                    section="extracted",
                )
            )
            if len(claims) >= max_claims:
                break

    return claims


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    reraise=True,
)
async def fetch_paper_text(
    url_or_id: str,
    client: httpx.AsyncClient | None = None,
) -> PaperContent:
    """Fetch full paper text from arxiv-txt.org, arXiv HTML, or raw abstract."""
    arxiv_id = extract_arxiv_id(url_or_id)
    await _enforce_rate_limit(min_interval=3.0)

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        owns_client = True

    try:
        raw_text = ""
        title = f"arXiv:{arxiv_id}"
        abstract = ""

        # Strategy 1: Fetch via LLM-friendly arxiv-txt.org service
        txt_url = f"https://arxiv-txt.org/abs/{arxiv_id}"
        try:
            resp = await client.get(txt_url)
            if resp.status_code == 200 and len(resp.text) > 50:
                raw_text = resp.text
        except (httpx.HTTPError, ValueError):
            raw_text = ""

        # Strategy 2: Fetch via experimental arXiv HTML
        if not raw_text:
            html_url = f"https://arxiv.org/html/{arxiv_id}"
            try:
                resp = await client.get(html_url)
                if resp.status_code == 200 and len(resp.text) > 100:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    # Extract title
                    title_elem = soup.find("h1", class_="ltx_title")
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                    # Extract text body
                    raw_text = soup.get_text(separator="\n", strip=True)
            except (httpx.HTTPError, ValueError):
                raw_text = ""

        # Strategy 3: Fetch abstract metadata from arXiv abstract page
        if not raw_text:
            abs_url = f"https://arxiv.org/abs/{arxiv_id}"
            resp = await client.get(abs_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                title_elem = soup.find("h1", class_="title")
                if title_elem:
                    title = title_elem.get_text(strip=True).replace("Title:", "").strip()
                abs_elem = soup.find("blockquote", class_="abstract")
                if abs_elem:
                    abstract = abs_elem.get_text(strip=True).replace("Abstract:", "").strip()
                raw_text = f"Title: {title}\n\nAbstract: {abstract}"

        sections = split_sections(raw_text)
        claims = extract_key_claims(raw_text)

        return PaperContent(
            arxiv_id=arxiv_id,
            title=title,
            abstract=abstract or sections.get("abstract", "")[:1000],
            sections=sections,
            claims=claims,
            source_url=f"https://arxiv.org/abs/{arxiv_id}",
        )
    finally:
        if owns_client:
            await client.aclose()
