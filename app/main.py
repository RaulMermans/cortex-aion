"""Read-only local investigation workspace."""
from pathlib import Path
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from .source import load_batch
from .domain import investigate

app = FastAPI(title="CORTEX AION", version="0.2.0")
logger = logging.getLogger(__name__)

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "index.html")

@app.get("/api/investigation")
def investigation():
    try:
        silver, quarantine, provenance = load_batch()
        return {**investigate(silver, quarantine), "provenance": provenance}
    except Exception as exc:
        # Never silently fall back to demo or disclose credentials/provider response bodies.
        logger.warning("Investigation unavailable (%s)", type(exc).__name__)
        raise HTTPException(503, "Batch unavailable or invalid. Check Azure authentication, exact blob paths and batch contract.") from None
