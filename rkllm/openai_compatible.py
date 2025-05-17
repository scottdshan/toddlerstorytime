#!/usr/bin/env python3
"""
openai_compat.py – minimal OpenAI-style /v1/chat/completions endpoint
backed by a single RKLLM model.

Start with:   python rkllm/openai_compatible.py [--measure] [--host <ip>] [--port <num>]
Then aim your OpenAI SDK at http://<host>:<port>/v1
"""

import time, uuid, itertools, asyncio, json, os, argparse
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from model_class import RKLLMLoaderClass, available_models
from contextlib import asynccontextmanager

# Global flag for performance measurement
MEASURE_PERFORMANCE = False

# ---------- RKLLM bootstrap ----------
# Manage CWD for model loading to ensure paths are resolved correctly
# relative to the script's directory (rkllm/), especially if model_class.py uses CWD-relative paths.
_orig_cwd = os.getcwd()
_script_dir = os.path.dirname(os.path.abspath(__file__))
_models_expected_path = os.path.join(_script_dir, "models")

try:
    # Change CWD to script's directory if it's different,
    # to help model_class.py find "./models" if it's CWD-sensitive.
    if _orig_cwd != _script_dir:
        os.chdir(_script_dir)
    
    MODELS = available_models()
    if not MODELS:
        # Check if the 'models' subdirectory actually exists where expected (now relative to _script_dir)
        if not os.path.isdir("models"): 
             raise RuntimeError(f"The 'models' directory was not found at {_models_expected_path}. Please ensure it exists and contains .rkllm files.")
        raise RuntimeError(f"No .rkllm files found in '{_models_expected_path}' – download one first.")
    MODEL_KEY = next(iter(MODELS))
    LLM = RKLLMLoaderClass(model=MODEL_KEY)
finally:
    # Restore original CWD if it was changed
    if os.getcwd() != _orig_cwd :
        os.chdir(_orig_cwd)

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
    if MEASURE_PERFORMANCE:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Application shutting down. Releasing LLM.")
    LLM.release()

app = FastAPI(title="RKLLM-OpenAI bridge", lifespan=lifespan)

@app.post("/v1/chat/completions")
async def chat(req: _ChatReq):
    global MEASURE_PERFORMANCE # Allow writing to global if it were to be changed, ensure read from global

    request_received_time = 0.0
    if MEASURE_PERFORMANCE:
        request_received_time = time.perf_counter()
        prompt_len = 0
        if req.messages:
            prompt_len = len(req.messages[-1].content)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Request received. Model: {req.model}, Stream: {req.stream}, Prompt length: {prompt_len}")

    if not req.messages:
        raise HTTPException(400, "messages list empty")
    prompt = req.messages[-1].content

    llm_call_start_time = time.perf_counter()
    llm_output_stream = LLM.get_RKLLM_output(prompt, []) # no history

    if req.stream:
        async def event_stream_generator(initial_request_time: float, call_llm_time: float):
            prev_content = ""
            first_token_timestamp = 0.0
            # Time right before starting to iterate the LLM's stream
            actual_generation_start_time = time.perf_counter() 

            for piece in llm_output_stream:
                current_content = piece.get("content", "") # Make robust if 'content' key missing
                delta = current_content[len(prev_content):]
                prev_content = current_content

                if delta: # A content delta exists
                    if MEASURE_PERFORMANCE and first_token_timestamp == 0.0:
                        first_token_timestamp = time.perf_counter()
                        time_to_first_token = first_token_timestamp - initial_request_time
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Stream: Time to first content token: {time_to_first_token:.4f}s")
                    
                    chunk = _completion_chunk(delta)
                    yield f"data: {json.dumps(chunk)}\n\n"
                # If there's no delta, but it's the first piece and potentially carries role info, 
                # we could log "time to first piece" if desired, but current focus is on content tokens.

            yield "data: [DONE]\n\n"

            if MEASURE_PERFORMANCE:
                stream_end_time = time.perf_counter()
                # NOTE: Using simple word count. For accurate token counts, integrate model's tokenizer.
                final_token_count = len(prev_content.split()) 
                
                overall_duration = stream_end_time - initial_request_time
                # Duration from when we started iterating the LLM output to when we finished
                generation_loop_duration = stream_end_time - actual_generation_start_time
                # Duration including the call to LLM.get_RKLLM_output and iteration
                llm_plus_generation_duration = stream_end_time - call_llm_time

                overall_tps = final_token_count / overall_duration if overall_duration > 0 else 0
                generation_loop_tps = final_token_count / generation_loop_duration if generation_loop_duration > 0 else 0
                
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Stream: COMPLETED")
                print(f"    Final generated tokens: {final_token_count} (approx. words)")
                if first_token_timestamp > 0.0:
                     print(f"    Time to first content token: {(first_token_timestamp - initial_request_time):.4f}s")
                else:
                     print(f"    Time to first content token: N/A (no content generated or measured)")
                print(f"    Generation loop duration: {generation_loop_duration:.4f}s (TPS: {generation_loop_tps:.2f}) approx.")
                print(f"    LLM call + Generation loop duration: {llm_plus_generation_duration:.4f}s")
                print(f"    Overall request duration: {overall_duration:.4f}s (Overall TPS: {overall_tps:.2f}) approx.")

        return StreamingResponse(event_stream_generator(request_received_time, llm_call_start_time),
                                 media_type="text/event-stream")
    else: # Non-stream mode
        _full_text = ""
        # Time right before starting to iterate the LLM's stream (for non-streaming case)
        actual_generation_start_time = time.perf_counter() 
        for _piece in llm_output_stream:
            # Assuming each piece is a dict with a "content" key holding cumulative text
            if isinstance(_piece, dict) and "content" in _piece:
                _full_text = _piece["content"]
        full = _full_text
        
        generation_end_time = time.perf_counter() # Time after collecting full text

        if MEASURE_PERFORMANCE:
            # NOTE: Using simple word count. For accurate token counts, integrate model's tokenizer.
            final_token_count = len(full.split())

            overall_duration = generation_end_time - request_received_time
            # Duration of iterating the LLM output
            generation_loop_duration = generation_end_time - actual_generation_start_time
            # Duration including the call to LLM.get_RKLLM_output and iteration
            llm_plus_generation_duration = generation_end_time - llm_call_start_time

            overall_tps = final_token_count / overall_duration if overall_duration > 0 else 0
            generation_loop_tps = final_token_count / generation_loop_duration if generation_loop_duration > 0 else 0

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Non-Stream: COMPLETED")
            print(f"    Final generated tokens: {final_token_count} (approx. words)")
            print(f"    Generation loop duration: {generation_loop_duration:.4f}s (TPS: {generation_loop_tps:.2f}) approx.")
            print(f"    LLM call + Generation loop duration: {llm_plus_generation_duration:.4f}s")
            print(f"    Overall request duration: {overall_duration:.4f}s (Overall TPS: {overall_tps:.2f}) approx.")

        resp = _completion_chunk(full, finish="stop")
        resp["object"] = "chat.completion"
        return JSONResponse(resp)

# ---------- Main execution for direct run ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OpenAI compatible server for RKLLM, with optional performance measurement.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Example:
  python rkllm/openai_compatible.py --measure --port 8001

This will start the server on port 8001 with performance measurement enabled.
The server expects model files to be in a 'models' subdirectory relative to this script (e.g., rkllm/models/).
"""
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind the server to (default: 0.0.0.0).")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to (default: 8000).")
    parser.add_argument("--measure", action="store_true", help="Enable performance measurement (timestamps and tokens/sec).")
    args = parser.parse_args()

    if args.measure:
        MEASURE_PERFORMANCE = True # Set the global flag
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Performance measurement ENABLED.")
    else:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Performance measurement DISABLED (to enable, use --measure flag).")

    try:
        import uvicorn
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting server on http://{args.host}:{args.port}/v1")
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except ImportError:
        print("Error: uvicorn is not installed. Please install it with 'pip install uvicorn'")
        print("You can run the server using: python rkllm/openai_compatible.py")
    except Exception as e:
        print(f"Failed to start server: {e}")
