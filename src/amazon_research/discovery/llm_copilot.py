"""
LLM Copilot – Claude API integration for intelligent Amazon opportunity analysis.

Wraps the existing rule-based copilot with claude-opus-4-6 (adaptive thinking, streaming)
for deep multi-market analysis, arbitrage detection, and keyword suggestions.

Usage:
    from amazon_research.discovery.llm_copilot import analyze_multi_market, ask_copilot
    # Analyze 3-market scrape results
    async for chunk in analyze_multi_market(market_results, asin="B07THHQMHM"):
        print(chunk, end="", flush=True)
"""
import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.llm_copilot")

_SYSTEM_PROMPT = """You are an expert Amazon marketplace research analyst specializing in:
- Cross-marketplace arbitrage opportunity detection (DE/US/AU price differences)
- BSR (Best Seller Rank) analysis and market competitiveness
- Review velocity and rating quality signals
- Keyword strategy and SEO optimization for Amazon listings
- Product launch viability and timing

You analyze real scraped Amazon data and provide actionable insights for sellers.
Be concise, specific, and data-driven. Always cite the actual numbers from the data."""

_ARBITRAGE_PROMPT = """Analyze the following multi-market Amazon product data and provide:

1. **Arbitrage Opportunity Score** (0-100): Based on price differences across markets
2. **Best Market to Source From**: Lowest price market
3. **Best Market to Sell In**: Highest price/demand ratio
4. **Price Spread Analysis**: % difference between cheapest and most expensive markets
5. **Review Signal Analysis**: Rating consistency and review count across markets
6. **BSR Context**: What BSR rankings tell us about market competitiveness
7. **Top 5 Keyword Suggestions**: Based on the product category and market data
8. **Action Recommendation**: Buy / Watch / Skip with reasoning

Multi-market data:
{market_data}

ASIN: {asin}
"""

_QUERY_PROMPT = """You are an Amazon research assistant. Answer the following research question
based on your expertise. If market data is provided, incorporate it into your analysis.

{context}

Question: {query}
"""


def _get_client():
    """Lazy-load Anthropic client; reads ANTHROPIC_API_KEY from env/.env."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic package not installed. Run: pip install anthropic>=0.40.0"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Try loading from .env manually if python-dotenv already loaded it
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        except ImportError:
            pass

    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Add it to your .env file: ANTHROPIC_API_KEY=sk-ant-..."
        )

    return anthropic.Anthropic(api_key=api_key)


def _format_market_data(market_results: List[Dict[str, Any]], asin: Optional[str] = None) -> str:
    """Format multi-market scrape results into readable text for the LLM."""
    lines = []
    ok_results = [r for r in market_results if r.get("status") == "ok"]

    if not ok_results:
        return "No successful market data available."

    for r in ok_results:
        market = r.get("market", "?")
        metrics = r.get("metrics", {})
        price = metrics.get("price")
        currency = metrics.get("currency", "")
        rating = metrics.get("rating")
        review_count = metrics.get("review_count")
        bsr = metrics.get("bsr")

        parts = [f"**{market}**:"]
        if price is not None:
            parts.append(f"Price={currency}{price:.2f}")
        if rating is not None:
            parts.append(f"Rating={rating}/5")
        if review_count is not None:
            parts.append(f"Reviews={review_count:,}")
        if bsr:
            parts.append(f"BSR={bsr[:80]}")
        elapsed = r.get("elapsed_ms", 0)
        parts.append(f"(scraped in {elapsed}ms)")

        lines.append(" | ".join(parts))

    # Price comparison summary
    prices_usd = {}
    # Rough USD conversion rates
    fx = {"USD": 1.0, "EUR": 1.09, "GBP": 1.27, "AUD": 0.65}
    for r in ok_results:
        metrics = r.get("metrics", {})
        price = metrics.get("price")
        currency = metrics.get("currency", "USD")
        if price and currency in fx:
            prices_usd[r["market"]] = price * fx[currency]

    if len(prices_usd) >= 2:
        min_market = min(prices_usd, key=prices_usd.get)
        max_market = max(prices_usd, key=prices_usd.get)
        min_price = prices_usd[min_market]
        max_price = prices_usd[max_market]
        if min_price > 0:
            spread_pct = ((max_price - min_price) / min_price) * 100
            lines.append(
                f"\nPrice spread: {min_market}(~${min_price:.2f}) → {max_market}(~${max_price:.2f})"
                f" = {spread_pct:.1f}% difference (approximate USD)"
            )

    failed = [r for r in market_results if r.get("status") != "ok"]
    if failed:
        lines.append(f"\nFailed markets: {', '.join(r['market'] for r in failed)}")

    return "\n".join(lines)


async def analyze_multi_market(
    market_results: List[Dict[str, Any]],
    asin: Optional[str] = None,
    stream: bool = True,
) -> AsyncIterator[str]:
    """
    Analyze multi-market scrape results with Claude. Yields text chunks when stream=True.

    Args:
        market_results: List of per-market dicts from scrape_asin_multi_market()
        asin: Product ASIN for context
        stream: Stream response chunks (default True)

    Yields:
        Text chunks of the analysis
    """
    import anthropic

    client = _get_client()
    market_data = _format_market_data(market_results, asin)
    prompt = _ARBITRAGE_PROMPT.format(
        market_data=market_data,
        asin=asin or "unknown",
    )

    logger.info(
        "llm_copilot analyze_multi_market",
        extra={"asin": asin, "markets": [r.get("market") for r in market_results]},
    )

    try:
        if stream:
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=2048,
                thinking={"type": "adaptive"},
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            ) as s:
                for text in s.text_stream:
                    yield text
        else:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=2048,
                thinking={"type": "adaptive"},
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            for block in response.content:
                if block.type == "text":
                    yield block.text

    except anthropic.AuthenticationError:
        yield "Error: Invalid ANTHROPIC_API_KEY. Check your .env file."
        logger.error("llm_copilot: authentication error")
    except anthropic.RateLimitError:
        yield "Error: Claude API rate limit hit. Please retry shortly."
        logger.warning("llm_copilot: rate limit")
    except Exception as e:
        yield f"Error during LLM analysis: {e}"
        logger.error("llm_copilot: unexpected error: %s", e)


async def ask_copilot(
    query: str,
    market_results: Optional[List[Dict[str, Any]]] = None,
    asin: Optional[str] = None,
    stream: bool = True,
) -> AsyncIterator[str]:
    """
    Ask the LLM copilot a free-form research question, optionally with market context.

    Args:
        query: Natural language question
        market_results: Optional multi-market scrape data for context
        asin: Optional ASIN for context
        stream: Stream response chunks (default True)

    Yields:
        Text chunks of the response
    """
    import anthropic

    client = _get_client()

    context_parts = []
    if asin:
        context_parts.append(f"ASIN: {asin}")
    if market_results:
        market_data = _format_market_data(market_results, asin)
        context_parts.append(f"Market data:\n{market_data}")

    context = "\n".join(context_parts)
    prompt = _QUERY_PROMPT.format(context=context, query=query)

    logger.info("llm_copilot ask_copilot", extra={"query": query[:80]})

    try:
        if stream:
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=1024,
                thinking={"type": "adaptive"},
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            ) as s:
                for text in s.text_stream:
                    yield text
        else:
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                thinking={"type": "adaptive"},
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            for block in response.content:
                if block.type == "text":
                    yield block.text

    except anthropic.AuthenticationError:
        yield "Error: Invalid ANTHROPIC_API_KEY. Check your .env file."
    except anthropic.RateLimitError:
        yield "Error: Claude API rate limit hit. Please retry shortly."
    except Exception as e:
        yield f"Error: {e}"
        logger.error("llm_copilot ask_copilot: %s", e)


def analyze_multi_market_sync(
    market_results: List[Dict[str, Any]],
    asin: Optional[str] = None,
) -> str:
    """
    Synchronous wrapper for analyze_multi_market. Returns full text response.
    Useful for scripts and non-async callers.
    """
    import asyncio

    async def _collect():
        chunks = []
        async for chunk in analyze_multi_market(market_results, asin, stream=True):
            chunks.append(chunk)
        return "".join(chunks)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In an existing event loop (e.g., FastAPI), use a thread executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _collect())
                return future.result()
        else:
            return loop.run_until_complete(_collect())
    except Exception as e:
        logger.error("analyze_multi_market_sync: %s", e)
        return f"Error: {e}"
