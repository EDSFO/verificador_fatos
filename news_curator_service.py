import io
import os
import time
import re
import unicodedata
from urllib.parse import urljoin
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx
try:
    from ddgs import DDGS
except Exception:
    DDGS = None
from openai import OpenAI

from N3_news_curator_agent import news_curator_workflow, output_dir

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}

STOPWORDS = {
    "a", "o", "os", "as", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das", "e", "em", "no", "na",
    "nos", "nas", "por", "para", "com", "sem", "sob", "sobre", "que", "se", "ao", "aos", "ou", "como", "mais",
    "menos", "entre", "contra", "apos", "antes", "durante", "tema", "noticia", "reportagem", "materia", "video",
    "texto", "suspeito", "analise", "verificacao", "fato", "fake", "news", "boato", "real", "esta", "estao",
    "disse", "diz", "ser", "foi", "sao", "uma", "sobre", "through", "from", "with", "that", "this",
}


def _snapshot_markdown_files() -> Dict[str, Tuple[Path, int, int]]:
    if not output_dir.exists():
        return {}
    snapshot: Dict[str, Tuple[Path, int, int]] = {}
    for path in output_dir.glob("*.md"):
        stat = path.stat()
        snapshot[path.name] = (path, stat.st_mtime_ns, stat.st_size)
    return snapshot


def _find_generated_file(
    before: Dict[str, Tuple[Path, int, int]],
    after: Dict[str, Tuple[Path, int, int]],
    started_at_ns: int,
) -> Optional[Path]:
    candidates: list[Tuple[Path, int]] = []
    for name, (path, mtime_ns, size) in after.items():
        before_entry = before.get(name)
        is_new = before_entry is None
        is_updated = before_entry is not None and (mtime_ns > before_entry[1] or size != before_entry[2])
        changed_in_this_run = mtime_ns >= started_at_ns
        if (is_new or is_updated) and changed_in_this_run:
            candidates.append((path, mtime_ns))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[1])
    return candidates[-1][0]


def _find_generated_files(
    before: Dict[str, Tuple[Path, int, int]],
    after: Dict[str, Tuple[Path, int, int]],
    started_at_ns: int,
) -> list[Path]:
    candidates: list[Tuple[Path, int]] = []
    for name, (path, mtime_ns, size) in after.items():
        before_entry = before.get(name)
        is_new = before_entry is None
        is_updated = before_entry is not None and (mtime_ns > before_entry[1] or size != before_entry[2])
        changed_in_this_run = mtime_ns >= started_at_ns
        if (is_new or is_updated) and changed_in_this_run:
            candidates.append((path, mtime_ns))

    candidates.sort(key=lambda item: item[1], reverse=True)
    return [path for path, _ in candidates]


def _require_api_key() -> None:
    if not os.getenv("ZAI_API_KEY"):
        raise EnvironmentError("ZAI_API_KEY nao encontrado. Configure no .env.")


def _is_balance_error(message: str) -> bool:
    text = (message or "").lower()
    return "insufficient balance" in text or "no resource package" in text or "'code': '1113'" in text


def _extract_urls(text: str) -> list[str]:
    if not text:
        return []
    urls = re.findall(r"https?://[^\s\)\]>\"']+", text)
    unique: list[str] = []
    seen = set()
    for url in urls:
        normalized = url.strip().rstrip(".,;")
        if normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def _extract_image_from_html(page_url: str, html_text: str) -> Optional[str]:
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        r'<img[^>]+src=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if not candidate:
                continue
            absolute = urljoin(page_url, candidate)
            if absolute.startswith("http"):
                return absolute
    return None


def _extract_image_candidates_from_html(page_url: str, html_text: str) -> list[str]:
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        r'<img[^>]+src=["\']([^"\']+)["\']',
    ]
    candidates: list[str] = []
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, html_text, flags=re.IGNORECASE):
            candidate = (match.group(1) or "").strip()
            if not candidate:
                continue
            absolute = urljoin(page_url, candidate)
            if not absolute.startswith("http") or absolute in seen:
                continue
            seen.add(absolute)
            candidates.append(absolute)
    return candidates


def _extract_title_from_html(html_text: str) -> str:
    patterns = [
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
        r"<title[^>]*>(.*?)</title>",
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


def _extract_description_from_html(html_text: str) -> str:
    patterns = [
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def _topic_keywords(topic: str) -> list[str]:
    normalized = _normalize_text(topic)
    tokens = re.findall(r"[a-z0-9]{3,}", normalized)
    keywords: list[str] = []
    seen = set()
    for token in tokens:
        if token in STOPWORDS or len(token) < 4:
            continue
        if token not in seen:
            seen.add(token)
            keywords.append(token)
    return keywords[:10]


def _relevance_threshold(keyword_count: int) -> int:
    if keyword_count <= 2:
        return 1
    if keyword_count <= 5:
        return 2
    return 3


def _score_source_relevance(topic: str, page_text: str) -> tuple[int, list[str]]:
    keywords = _topic_keywords(topic)
    if not keywords:
        return 0, []

    haystack = _normalize_text(page_text)
    matched = [keyword for keyword in keywords if keyword in haystack]
    return len(matched), matched


def _looks_like_clean_article(text: str) -> bool:
    if not text:
        return False
    word_count = len(re.findall(r"\w+", text))
    if word_count < 110:
        return False

    lowered = text.lower()
    noisy_tokens = [
        "workflow information",
        "step 1:",
        "step 2:",
        "completed)",
        "error   ",
        "insufficient balance",
    ]
    if any(token in lowered for token in noisy_tokens):
        return False

    special_count = sum(text.count(ch) for ch in ("|", "┏", "┃", "┗", "╭", "╰"))
    if special_count > 40:
        return False
    if special_count / max(len(text), 1) > 0.02:
        return False
    return True


def _validate_reference_sources(topic: str, urls: list[str], timeout_seconds: float = 4.0, max_sources: int = 5) -> list[dict]:
    if not urls:
        return []

    validated: list[dict] = []
    seen = set()
    threshold = _relevance_threshold(len(_topic_keywords(topic)))

    with httpx.Client(follow_redirects=True, timeout=timeout_seconds, headers=HEADERS) as client:
        for url in urls:
            if url in seen:
                continue
            seen.add(url)

            try:
                response = client.get(url)
            except Exception:
                continue

            if response.status_code >= 400:
                continue

            html_text = response.text
            title = _extract_title_from_html(html_text)
            description = _extract_description_from_html(html_text)
            body_text = re.sub(r"<[^>]+>", " ", html_text)
            body_text = re.sub(r"\s+", " ", body_text)[:5000]
            score, matched_keywords = _score_source_relevance(topic, " ".join([title, description, body_text]))
            if score < threshold:
                continue

            validated.append(
                {
                    "url": url,
                    "title": title or url,
                    "matched_keywords": matched_keywords,
                    "score": score,
                }
            )
            if len(validated) >= max_sources:
                break

    validated.sort(key=lambda item: item["score"], reverse=True)
    return validated


def _article_candidate_bias(path: Path) -> int:
    name = _normalize_text(path.name)
    score = 0
    if path.suffix.lower() == ".md":
        score += 4
    if "materia" in name:
        score += 10
    if "redacao" in name:
        score += 7
    if "posicionamento" in name:
        score -= 3
    if "verificacao" in name or "verificacao" in name:
        score -= 6
    if "relatorio" in name:
        score -= 8
    if "pesquisa" in name or "apuracao" in name:
        score -= 10
    return score


def _select_best_article_content(topic: str, files: list[Path], workflow_response: str, console_output: str) -> tuple[Optional[Path], Optional[str]]:
    best_path: Optional[Path] = None
    best_content: Optional[str] = None
    best_score = -10**9

    for path in files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if not _looks_like_clean_article(content):
            continue

        relevance, _ = _score_source_relevance(topic, content[:12000])
        bias = _article_candidate_bias(path)
        total_score = (relevance * 10) + bias
        if total_score > best_score:
            best_score = total_score
            best_path = path
            best_content = content

    if best_score <= 0:
        return None, None
    return best_path, best_content


def _is_valid_image_url(client: httpx.Client, image_url: str) -> bool:
    try:
        response = client.get(image_url, headers={**HEADERS, "Range": "bytes=0-4096"})
    except Exception:
        return False

    if response.status_code >= 400:
        return False
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "image/" not in content_type:
        return False
    return True


def _resolve_evidence_image(reference_urls: list[str], timeout_seconds: float = 4.0) -> tuple[Optional[str], Optional[str]]:
    if not reference_urls:
        return None, None

    with httpx.Client(follow_redirects=True, timeout=timeout_seconds, headers=HEADERS) as client:
        for url in reference_urls[:6]:
            try:
                response = client.get(url)
                if response.status_code >= 400:
                    continue
                image_candidates = _extract_image_candidates_from_html(url, response.text)
                for image_url in image_candidates:
                    if _is_valid_image_url(client, image_url):
                        return image_url, url
            except Exception:
                continue
    return None, None


def _search_news_urls(topic: str, max_results: int = 10) -> list[str]:
    if not DDGS:
        return []

    query_variants = [
        f"{topic} noticia",
        f"{topic} reportagem",
        f"{topic} verificacao",
        topic,
    ]
    unique: list[str] = []
    seen = set()

    for query in query_variants:
        for region in ("br-pt", "wt-wt"):
            try:
                results = DDGS().text(
                    query=query,
                    region=region,
                    safesearch="moderate",
                    max_results=max_results,
                )
            except Exception:
                continue

            for item in results or []:
                href = (item or {}).get("href") or (item or {}).get("url")
                if not href or not href.startswith("http"):
                    continue
                if href in seen:
                    continue
                seen.add(href)
                unique.append(href)
                if len(unique) >= max_results:
                    return unique
    return unique


def _search_contextual_image(topic: str) -> tuple[Optional[str], Optional[str]]:
    if not DDGS:
        return None, None

    query_variants = [
        f"{topic} noticia reportagem",
        f"{topic} jornal",
        topic,
    ]
    for query in query_variants:
        for region in ("br-pt", "wt-wt"):
            try:
                results = DDGS().images(
                    query=query,
                    region=region,
                    safesearch="moderate",
                    max_results=10,
                    type_image="photo",
                )
            except Exception:
                continue

            with httpx.Client(follow_redirects=True, timeout=4.0, headers=HEADERS) as client:
                for item in results or []:
                    image_url = (item or {}).get("image")
                    source_url = (item or {}).get("url") or (item or {}).get("href")
                    if not image_url or not source_url:
                        continue
                    if _is_valid_image_url(client, image_url):
                        return image_url, source_url
    return None, None


def _check_provider_access() -> None:
    client = OpenAI(
        api_key=os.getenv("ZAI_API_KEY"),
        base_url=os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4/"),
    )
    model = os.getenv("ZAI_MODEL", "glm-4.7")

    try:
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            temperature=0,
        )
    except Exception as exc:
        message = str(exc)
        if _is_balance_error(message):
            raise RuntimeError(
                "A conta da Z.AI esta sem saldo/pacote para o modelo configurado. "
                "Se seu plano for Coding, use ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4/."
            ) from exc
        raise


def run_news_curator(topic: str, stream: bool = False, markdown: bool = True) -> Dict[str, Optional[str]]:
    clean_topic = (topic or "").strip()
    if not clean_topic:
        raise ValueError("Informe um tema valido para iniciar a curadoria.")

    _require_api_key()
    _check_provider_access()
    output_dir.mkdir(parents=True, exist_ok=True)

    before_files = _snapshot_markdown_files()
    started_at_ns = time.time_ns()

    if stream:
        result = news_curator_workflow.print_response(clean_topic, stream=True, markdown=markdown)
        console_output = ""
    else:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            result = news_curator_workflow.print_response(clean_topic, stream=False, markdown=markdown)
        console_output = buffer.getvalue().strip()

    workflow_response = str(result).strip() if result is not None else ""
    after_files = _snapshot_markdown_files()
    generated_files = _find_generated_files(before_files, after_files, started_at_ns)
    article_file, article_content = _select_best_article_content(clean_topic, generated_files, workflow_response, console_output)

    final_text = "\n".join([
        workflow_response,
        console_output,
        article_content or "",
    ])
    if _is_balance_error(final_text):
        raise RuntimeError(
            "A Z.AI retornou saldo/pacote insuficiente para o modelo atual. "
            "Recarregue a conta/pacote ou ajuste o ZAI_MODEL."
        )

    candidate_text = article_content or final_text
    reference_urls = _extract_urls(candidate_text)
    web_urls = _search_news_urls(clean_topic, max_results=12)
    validated_sources = _validate_reference_sources(clean_topic, reference_urls, max_sources=5)
    if len(validated_sources) < 2:
        extra_validated = _validate_reference_sources(clean_topic, web_urls, max_sources=5)
        known = {item["url"] for item in validated_sources}
        for item in extra_validated:
            if item["url"] not in known:
                validated_sources.append(item)
                known.add(item["url"])
            if len(validated_sources) >= 5:
                break

    all_candidate_urls: list[str] = []
    seen_urls = set()
    validated_urls = [item["url"] for item in validated_sources]
    for url in validated_urls + reference_urls + web_urls:
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_candidate_urls.append(url)

    evidence_image_url, evidence_source_url = _resolve_evidence_image(all_candidate_urls)
    if not evidence_image_url:
        evidence_image_url, evidence_source_url = _search_contextual_image(clean_topic)

    return {
        "workflow_response": workflow_response,
        "console_output": console_output,
        "article_path": str(article_file) if article_file else None,
        "article_content": article_content,
        "evidence_image_url": evidence_image_url,
        "evidence_source_url": evidence_source_url,
        "validated_sources": validated_sources,
        "primary_source_url": validated_urls[0] if validated_urls else None,
    }
