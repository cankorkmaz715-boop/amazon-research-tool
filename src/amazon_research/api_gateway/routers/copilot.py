"""
LLM Copilot API routes.

POST /api/copilot/analyze  – analyze multi-market scrape results with Claude
POST /api/copilot/ask      – ask free-form research question with optional market context
GET  /api/copilot/status   – check if ANTHROPIC_API_KEY is configured
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from amazon_research.logging_config import get_logger

logger = get_logger("api_gateway.copilot")
router = APIRouter()


class AnalyzeRequest(BaseModel):
    asin: Optional[str] = None
    market_results: List[Dict[str, Any]]
    stream: bool = True


class AskRequest(BaseModel):
    query: str
    asin: Optional[str] = None
    market_results: Optional[List[Dict[str, Any]]] = None
    stream: bool = True


@router.get("/status")
def copilot_status() -> Dict[str, Any]:
    """Check if ANTHROPIC_API_KEY is configured and anthropic package is installed."""
    import os
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    try:
        import anthropic  # noqa: F401
        has_package = True
    except ImportError:
        has_package = False

    return {
        "ready": has_key and has_package,
        "api_key_configured": has_key,
        "anthropic_installed": has_package,
        "model": "claude-opus-4-6",
    }


@router.post("/analyze")
async def analyze_opportunity(body: AnalyzeRequest):
    """
    Analyze multi-market product data with Claude.
    Returns streaming text (SSE) when stream=True, or JSON when stream=False.
    """
    if not body.market_results:
        raise HTTPException(status_code=400, detail="market_results required")

    try:
        from amazon_research.discovery.llm_copilot import analyze_multi_market

        if body.stream:
            async def event_stream():
                try:
                    async for chunk in analyze_multi_market(
                        body.market_results, asin=body.asin, stream=True
                    ):
                        # SSE format: data: <chunk>\n\n
                        yield f"data: {chunk}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error("copilot stream error: %s", e)
                    yield f"data: Error: {e}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            chunks = []
            async for chunk in analyze_multi_market(
                body.market_results, asin=body.asin, stream=False
            ):
                chunks.append(chunk)
            return {"analysis": "".join(chunks), "asin": body.asin}

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("copilot analyze error: %s", e)
        raise HTTPException(status_code=500, detail="analysis failed")


@router.post("/ask")
async def ask_copilot_endpoint(body: AskRequest):
    """
    Ask the LLM copilot a free-form research question.
    Optionally attach multi-market data for context.
    """
    if not body.query or not body.query.strip():
        raise HTTPException(status_code=400, detail="query required")

    try:
        from amazon_research.discovery.llm_copilot import ask_copilot

        if body.stream:
            async def event_stream():
                try:
                    async for chunk in ask_copilot(
                        body.query,
                        market_results=body.market_results,
                        asin=body.asin,
                        stream=True,
                    ):
                        yield f"data: {chunk}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error("copilot ask stream error: %s", e)
                    yield f"data: Error: {e}\n\n"
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            chunks = []
            async for chunk in ask_copilot(
                body.query,
                market_results=body.market_results,
                asin=body.asin,
                stream=False,
            ):
                chunks.append(chunk)
            return {"response": "".join(chunks), "query": body.query}

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("copilot ask error: %s", e)
        raise HTTPException(status_code=500, detail="ask failed")
