#!/usr/bin/env python3
"""
openai_compat.py – minimal OpenAI-style /v1/chat/completions endpoint
backed by a single RKLLM model.

Start with:   uvicorn openai_compat:app --host 0.0.0.0 --port 8000
Then aim your OpenAI SDK at http://localhost:8000
"""

import time, uuid, itertools, asyncio, argparse, json, sys
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from model_class import RKLLMLoaderClass, available_models
from contextlib import asynccontextmanager

# NEW: Argument parsing
parser = argparse.ArgumentParser(
    description="OpenAI-compatible server for RKLLM models."
)
parser.add_argument(
    "--measure",
    action="store_true",
    help="Enable performance measurement (timestamps and tokens/sec)."
)
parser.add_argument(
    "--model_key",
    type=str,
    default=None,
    help="Specify the model key to use. Lists available models if not specified or invalid."
)
script_args, _ = parser.parse_known_args()

# ---------- RKLLM bootstrap ----------
MODELS = available_models()
if not MODELS:
    print("Error: No .rkllm files found in ./models – download one first.", file=sys.stderr)
    sys.exit(1)

# MODIFIED: Model selection logic
if script_args.model_key:
    if script_args.model_key in MODELS:
        MODEL_KEY = script_args.model_key
        print(f"Using specified model: {MODEL_KEY}")
    else:
        print(f"Error: Model key '{script_args.model_key}' not found.", file=sys.stderr)
        print("Available models are:", file=sys.stderr)
        for key in MODELS:
            print(f"  - {key}", file=sys.stderr)
        sys.exit(1)
else:
    MODEL_KEY = next(iter(MODELS)) # Default to the first model
    print(f"No model key specified. Defaulting to first available model: {MODEL_KEY}")
    if len(MODELS) > 1:
        print("To use a different model, pass the --model_key argument.")
        print("Available models are:")
        for key in MODELS:
            print(f"  - {key}")

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
    # single-turn; we only look at the last user message
    if not req.messages:
        raise HTTPException(400, "messages list empty")
    prompt = req.messages[-1].content

    # generator from RKLLM
    stream = LLM.get_RKLLM_output(prompt, [])          # no history

    if req.stream:
        async def event_stream():
            nonlocal stream # Ensure we are using the correct stream variable
            _prev_text_stream = ""
            _token_count_stream = 0
            _start_time_stream = 0.0 # Initialize

            if script_args.measure: # MODIFIED: Start timing and logging
                _start_time_stream = time.perf_counter()
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Stream request started. Model: {MODEL_KEY}. Prompt: \"{prompt[:80]}...\"")

            for piece in stream:
                text = piece["content"]
                delta = text[len(_prev_text_stream):]
                _prev_text_stream = text
                if delta:
                    if script_args.measure: # MODIFIED: Count tokens
                        _token_count_stream += len(delta)  # Using char length as token count
                    chunk = _completion_chunk(delta)
                    yield f"data: {json.dumps(chunk)}\\n\\n" # MODIFIED: Use json.dumps for proper event stream data
            
            if script_args.measure: # MODIFIED: Finish timing and logging
                end_time_stream = time.perf_counter()
                duration_stream = end_time_stream - _start_time_stream
                tokens_per_sec_stream = _token_count_stream / duration_stream if duration_stream > 0 else 0
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Stream request finished. Duration: {duration_stream:.4f}s. Tokens: {_token_count_stream}. Tokens/sec: {tokens_per_sec_stream:.2f}")
            
            yield "data: [DONE]\\n\\n" # Ensure [DONE] is sent
        return StreamingResponse(event_stream(),
                                 media_type="text/event-stream")

    # non-stream mode: collect full text then return once
    _start_time_full = 0.0 # Initialize
    if script_args.measure: # MODIFIED: Start timing and logging
        _start_time_full = time.perf_counter()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Full request started. Model: {MODEL_KEY}. Prompt: \"{prompt[:80]}...\"")
    
    _full_text = ""
    for _piece in stream:  # Iterate through the stream of pieces
        # Assuming each piece is a dict with a "content" key holding cumulative text
        if isinstance(_piece, dict) and "content" in _piece:
            _full_text = _piece["content"]  # The last piece's content is the full text
    full = _full_text
    
    if script_args.measure: # MODIFIED: Finish timing and logging
        end_time_full = time.perf_counter()
        duration_full = end_time_full - _start_time_full
        _token_count_full = len(full) # Using char length as token count
        tokens_per_sec_full = _token_count_full / duration_full if duration_full > 0 else 0
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Full request finished. Duration: {duration_full:.4f}s. Tokens: {_token_count_full}. Tokens/sec: {tokens_per_sec_full:.2f}")

    resp = _completion_chunk(full, finish="stop")
    resp["object"] = "chat.completion"
    return JSONResponse(resp)
