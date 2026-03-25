"""
Keyword expansion engine. Step 94 / Step 105 – generate related keyword candidates from base keyword.
Rule-based: token similarity, modifiers, context overlap, title patterns; advanced: co-occurrence,
reverse ASIN context, category overlap, repeated niche/cluster association. Scanner and seed manager compatible.
"""
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

from amazon_research.logging_config import get_logger

logger = get_logger("keywords.expansion")

DEFAULT_MODIFIER_TOKENS = ("wireless", "gaming", "usb", "bluetooth", "professional", "portable", "rechargeable")

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"


def _tokenize(text: str) -> Set[str]:
    """Lowercase alphanumeric tokens."""
    if not text or not str(text).strip():
        return set()
    return set(re.findall(r"[a-z0-9]+", str(text).lower()))


def _gather_keywords_from_discovery(asin_list: List[str], limit_per_asin: int = 20) -> List[Tuple[str, str, Optional[str]]]:
    """
    For each ASIN, get discovery context (reverse ASIN); collect keyword source_ids and category source_ids.
    Returns list of (keyword_or_id, signal_type, category_hint). signal_type: keyword_cooccurrence | category_context.
    """
    if not asin_list:
        return []
    out: List[Tuple[str, str, Optional[str]]] = []
    seen_kw: Set[str] = set()
    try:
        from amazon_research.db import get_discovery_context_for_asin
    except ImportError:
        return []
    for asin in asin_list[:50]:
        try:
            ctxs = get_discovery_context_for_asin(str(asin).strip(), limit=limit_per_asin)
        except Exception as e:
            logger.debug("_gather_keywords_from_discovery: %s", e)
            continue
        for ctx in ctxs:
            st = (ctx.get("source_type") or "").strip().lower()
            sid = (ctx.get("source_id") or "").strip()
            if not sid:
                continue
            if st == "keyword":
                key = sid.lower()
                if key not in seen_kw:
                    seen_kw.add(key)
                    out.append((sid, "keyword_cooccurrence", None))
            elif st == "category":
                out.append((sid, "category_context", sid))
    return out


def _gather_keywords_from_clusters(
    clusters: List[Dict[str, Any]],
    limit_per_asin: int = 15,
) -> Counter:
    """
    For each cluster, get member ASINs and discovery context keywords; count keyword frequency.
    Returns Counter of keyword -> count (repeated niche association).
    """
    counter: Counter = Counter()
    try:
        from amazon_research.db import get_discovery_context_for_asin
    except ImportError:
        return counter
    for cluster in (clusters or [])[:30]:
        members = cluster.get("member_asins") or []
        for asin in members[:20]:
            try:
                ctxs = get_discovery_context_for_asin(str(asin).strip(), limit=limit_per_asin)
            except Exception:
                continue
            for ctx in ctxs:
                if (ctx.get("source_type") or "").strip().lower() != "keyword":
                    continue
                sid = (ctx.get("source_id") or "").strip()
                if sid:
                    counter[sid] += 1
    return counter


def _confidence(signal_summary: Dict[str, Any]) -> str:
    """Rule-based confidence from expansion signal summary."""
    if not signal_summary:
        return CONFIDENCE_LOW
    if signal_summary.get("keyword_cooccurrence") or signal_summary.get("repeated_niche_association"):
        return CONFIDENCE_HIGH
    if signal_summary.get("context_overlap") or signal_summary.get("title_cooccurrence") or signal_summary.get("token_similarity"):
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


def expand_keywords(
    base_keyword: str,
    *,
    context_keywords: Optional[List[str]] = None,
    title_tokens: Optional[List[str]] = None,
    modifier_tokens: Optional[List[str]] = None,
    max_candidates: int = 30,
    use_db: bool = False,
    asin_list: Optional[List[str]] = None,
    clusters: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate related keyword candidates from a base keyword. Expansion signals: token_modifier,
    context_overlap, title_cooccurrence, token_similarity; when use_db/asin_list/clusters:
    keyword_cooccurrence (reverse ASIN context), category_context, repeated_niche_association.
    Returns { base_keyword, candidates, summary }. Each candidate: base_keyword, expanded_keyword,
    context_signal, expansion_signal_summary (optional), confidence (optional).
    Compatible with keyword scanner, seed manager, automated niche discovery, reverse ASIN engine.
    """
    base = (base_keyword or "").strip()
    if not base:
        return {"base_keyword": "", "candidates": [], "summary": {"total": 0}}

    base_tokens = _tokenize(base)
    seen: Set[str] = set()
    seen.add(base.lower())
    candidates: List[Dict[str, Any]] = []
    modifiers = list(modifier_tokens or DEFAULT_MODIFIER_TOKENS)

    # --- Step 105: Richer signals from discovery and clusters (use_db) ---
    discovery_keywords: List[Tuple[str, str, Optional[str]]] = []
    niche_counter: Counter = Counter()
    if use_db and asin_list:
        discovery_keywords = _gather_keywords_from_discovery(asin_list)
    if use_db and clusters:
        niche_counter = _gather_keywords_from_clusters(clusters)
    category_hints: Set[str] = set()
    for _kw, sig, hint in discovery_keywords:
        if sig == "category_context" and hint:
            category_hints.add(hint)

    # --- Repeated niche: keywords that appear in multiple clusters/ASINs (high confidence) ---
    for kw, count in niche_counter.most_common(30):
        kw_clean = (kw or "").strip()
        if not kw_clean or kw_clean.lower() in seen or kw_clean.lower() == base.lower():
            continue
        seen.add(kw_clean.lower())
        candidates.append({
            "base_keyword": base,
            "expanded_keyword": kw_clean,
            "context_signal": "repeated_niche_association",
            "expansion_signal_summary": {"repeated_niche_association": count, "category_context": list(category_hints)[:3] if category_hints else None},
            "confidence": CONFIDENCE_HIGH,
        })
        if len(candidates) >= max_candidates:
            return _result(base, candidates, max_candidates)

    # --- Keyword co-occurrence from discovery / reverse ASIN context ---
    for kw, sig, _ in discovery_keywords:
        if sig != "keyword_cooccurrence":
            continue
        kw_clean = (kw or "").strip()
        if not kw_clean or kw_clean.lower() in seen or kw_clean.lower() == base.lower():
            continue
        seen.add(kw_clean.lower())
        candidates.append({
            "base_keyword": base,
            "expanded_keyword": kw_clean,
            "context_signal": "keyword_cooccurrence",
            "expansion_signal_summary": {"keyword_cooccurrence": True, "category_context": list(category_hints)[:3] if category_hints else None},
            "confidence": CONFIDENCE_HIGH,
        })
        if len(candidates) >= max_candidates:
            return _result(base, candidates, max_candidates)

    # --- Token modifier: prepend/append common modifiers ---
    for mod in modifiers:
        mod_lower = mod.lower()
        if mod_lower in base_tokens:
            continue
        for expanded in (f"{mod} {base}", f"{base} {mod}"):
            ex_lower = expanded.lower()
            if ex_lower not in seen:
                seen.add(ex_lower)
                summary = {"token_modifier": mod_lower}
                candidates.append({
                    "base_keyword": base,
                    "expanded_keyword": expanded,
                    "context_signal": "token_modifier",
                    "expansion_signal_summary": summary,
                    "confidence": _confidence(summary),
                })
                if len(candidates) >= max_candidates:
                    return _result(base, candidates, max_candidates)

    # --- Context overlap: keywords from same scan/category context ---
    for kw in (context_keywords or []):
        kw_clean = (kw or "").strip()
        if not kw_clean or kw_clean.lower() in seen:
            continue
        seen.add(kw_clean.lower())
        summary = {"context_overlap": True}
        candidates.append({
            "base_keyword": base,
            "expanded_keyword": kw_clean,
            "context_signal": "context_overlap",
            "expansion_signal_summary": summary,
            "confidence": _confidence(summary),
        })
        if len(candidates) >= max_candidates:
            return _result(base, candidates, max_candidates)

    # --- Token similarity: context keywords that share tokens with base ---
    for kw in (context_keywords or []):
        kw_clean = (kw or "").strip()
        if not kw_clean or kw_clean.lower() == base.lower():
            continue
        kw_tokens = _tokenize(kw_clean)
        if base_tokens & kw_tokens and kw_clean.lower() not in seen:
            seen.add(kw_clean.lower())
            summary = {"token_similarity": True, "shared_tokens": list(base_tokens & kw_tokens)}
            candidates.append({
                "base_keyword": base,
                "expanded_keyword": kw_clean,
                "context_signal": "token_similarity",
                "expansion_signal_summary": summary,
                "confidence": _confidence(summary),
            })
            if len(candidates) >= max_candidates:
                return _result(base, candidates, max_candidates)

    # --- Title co-occurrence: tokens from product titles (base + token / token + base) ---
    tokens_to_try = list(title_tokens or [])
    if use_db and asin_list and not tokens_to_try:
        try:
            from amazon_research.db import get_asins_metadata
            meta = get_asins_metadata(asin_list)
            for r in meta:
                t = (r.get("title") or "").strip()
                tokens_to_try.extend(_tokenize(t))
        except Exception as e:
            logger.debug("expand_keywords: get_asins_metadata: %s", e)
    for token in tokens_to_try:
        if not token or token in base_tokens or len(token) < 2:
            continue
        for expanded in (f"{token} {base}", f"{base} {token}"):
            ex_lower = expanded.lower()
            if ex_lower not in seen:
                seen.add(ex_lower)
                summary = {"title_cooccurrence": token}
                candidates.append({
                    "base_keyword": base,
                    "expanded_keyword": expanded,
                    "context_signal": "title_cooccurrence",
                    "expansion_signal_summary": summary,
                    "confidence": _confidence(summary),
                })
                if len(candidates) >= max_candidates:
                    return _result(base, candidates, max_candidates)

    return _result(base, candidates, max_candidates)


def _result(base: str, candidates: List[Dict[str, Any]], max_candidates: int) -> Dict[str, Any]:
    trimmed = candidates[:max_candidates]
    for c in trimmed:
        if "expansion_signal_summary" not in c:
            c["expansion_signal_summary"] = {c.get("context_signal", ""): True}
        if "confidence" not in c:
            c["confidence"] = _confidence(c.get("expansion_signal_summary") or {})
    signal_counts: Dict[str, int] = {}
    for c in trimmed:
        sig = c.get("context_signal") or ""
        signal_counts[sig] = signal_counts.get(sig, 0) + 1
    return {
        "base_keyword": base,
        "candidates": trimmed,
        "summary": {"total": len(trimmed), "by_signal": signal_counts},
    }
