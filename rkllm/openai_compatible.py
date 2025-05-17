#!/usr/bin/env python3
"""
openai_compat.py – minimal OpenAI-style /v1/chat/completions endpoint
backed by a single RKLLM model.

Start with:   uvicorn openai_compat:app --host 0.0.0.0 --port 8000
Then aim your OpenAI SDK at http://localhost:8000
"""

import time, uuid, itertools, asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from model_class import RKLLMLoaderClass, available_models
from contextlib import asynccontextmanager
import os

# ---------- RKLLM bootstrap ----------
MODELS = available_models()
print("Available models:", list(MODELS.keys()))
model_env = os.environ.get("RKLLM_MODEL")
MODEL_KEY = model_env if model_env is not None else next(iter(MODELS))
if MODEL_KEY not in MODELS:
    raise RuntimeError(f"Model '{MODEL_KEY}' not found in available models: {list(MODELS.keys())}")
LLM = RKLLMLoaderClass(model=MODEL_KEY)

# ---------- Pydantic shapes mimicking OpenAI ----------
class _ChatMessage(BaseModel):
    role: str
    content: str

class _ChatReq(BaseModel):
    model: str                       # ignored, but required by OpenAI clients
    messages: List[_ChatMessage]
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None # accepted but ignored, etc.
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    measure: Optional[bool] = False  # If true, return timing & throughput metrics

# ---------- helpers ----------
def _now() -> int: return int(time.time())

def _completion_chunk(delta: str, idx: int = 0, finish: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion.chunk",
        "created": _now(),
        "model": MODEL_KEY,
        "choices": [{
            "index": idx,
            "delta": {"content": delta} if delta else {},
            "finish_reason": finish,
        }],
    }

# ---------- FastAPI ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic (if any) would go here
    yield
    # Shutdown logic
    LLM.release()

app = FastAPI(title="RKLLM-OpenAI bridge", lifespan=lifespan)

@app.post("/v1/chat/completions")
async def chat(req: _ChatReq):
    start_ts = time.time()  # Timestamp for performance measurement
    # single-turn; we only look at the last user message
    if not req.messages:
        raise HTTPException(400, "messages list empty")
    prompt = req.messages[-1].content

    

    # generator from RKLLM
    stream = LLM.get_RKLLM_output(prompt, [])          # no history

    if req.stream:
        # For streaming mode: we'll compute metrics after generation finishes
        tokens_generated = 0
        async def event_stream():
            nonlocal tokens_generated
            prev = ""
            for piece in stream:
                text = piece["content"]
                delta = text[len(prev):]               # new fragment only
                prev = text
                tokens_generated += len(delta.split())
                if delta:
                    chunk = _completion_chunk(delta)
                    yield f"data: {chunk}\n\n"
            # After stream completes, optionally send metrics
            if req.measure:
                elapsed = max(time.time() - start_ts, 1e-6)
                tps = tokens_generated / elapsed
                metrics = {"timestamp": start_ts, "duration_seconds": elapsed, "token_count": tokens_generated, "tokens_per_second": tps}
                yield f"data: {{\"metrics\": {metrics}}}\n\n"
            # send final [DONE] marker
            yield "data: [DONE]\n\n"
        return StreamingResponse(event_stream(),
                                 media_type="text/event-stream")

    # non-stream mode: collect full text then return once
    _full_text = ""  # Initialize to empty string
    for _piece in stream:  # Iterate through the stream of pieces
        # Assuming each piece is a dict with a "content" key holding cumulative text
        if isinstance(_piece, dict) and "content" in _piece:
            _full_text = _piece["content"]  # The last piece's content is the full text
    full = _full_text
    resp = _completion_chunk(full, finish="stop")
    if req.measure:
        tokens_generated = len(full.split())
        elapsed = max(time.time() - start_ts, 1e-6)
        resp["metrics"] = {
            "timestamp": start_ts,
            "duration_seconds": elapsed,
            "token_count": tokens_generated,
            "tokens_per_second": tokens_generated / elapsed,
        }
    resp["object"] = "chat.completion"
    return JSONResponse(resp)
