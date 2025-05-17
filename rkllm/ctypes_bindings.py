import ctypes

# Define global variables to store the callback function output for displaying in the Gradio interface
global_text = []
global_state = -1
split_byte_data = bytes(b"") # Used to store the segmented byte data

# Set the dynamic library path
# Default is v1.1.2
rkllm_lib = ctypes.CDLL('lib/librkllmrt.so')

# Define the structures from the library
RKLLM_Handle_t = ctypes.c_void_p
userdata = ctypes.c_void_p(None)

# Replace enum type aliases and attribute assignments with plain integer constants for compatibility
# LLM call states
RKLLM_RUN_NORMAL: int = 0
RKLLM_RUN_WAITING: int = 1
RKLLM_RUN_FINISH: int = 2
RKLLM_RUN_ERROR: int = 3

# Input types supported by RKLLM
RKLLM_INPUT_PROMPT: int = 0
RKLLM_INPUT_TOKEN: int = 1
RKLLM_INPUT_EMBED: int = 2
RKLLM_INPUT_MULTIMODAL: int = 3

# Inference modes
RKLLM_INFER_GENERATE: int = 0
RKLLM_INFER_GET_LAST_HIDDEN_LAYER: int = 1
RKLLM_INFER_GET_LOGITS: int = 2

# ctypes integer aliases for enum types (used inside structures)
LLMCallState_t = ctypes.c_int
RKLLMInputType_t = ctypes.c_int
RKLLMInferMode_t = ctypes.c_int

class RKLLMExtendParam(ctypes.Structure):
    _fields_ = [
        ("base_domain_id", ctypes.c_int32),
        ("embed_flash", ctypes.c_int8),
        ("enabled_cpus_num", ctypes.c_int8),
        ("enabled_cpus_mask", ctypes.c_uint32),
        ("reserved", ctypes.c_uint8 * 106),  # Keep overall struct size aligned with C definition
    ]

class RKLLMParam(ctypes.Structure):
    _fields_ = [
        ("model_path", ctypes.c_char_p),
        ("max_context_len", ctypes.c_int32),
        ("max_new_tokens", ctypes.c_int32),
        ("top_k", ctypes.c_int32),
        ("n_keep", ctypes.c_int32),
        ("top_p", ctypes.c_float),
        ("temperature", ctypes.c_float),
        ("repeat_penalty", ctypes.c_float),
        ("frequency_penalty", ctypes.c_float),
        ("presence_penalty", ctypes.c_float),
        ("mirostat", ctypes.c_int32),
        ("mirostat_tau", ctypes.c_float),
        ("mirostat_eta", ctypes.c_float),
        ("skip_special_token", ctypes.c_bool),
        ("is_async", ctypes.c_bool),
        ("img_start", ctypes.c_char_p),
        ("img_end", ctypes.c_char_p),
        ("img_content", ctypes.c_char_p),
        ("extend_param", RKLLMExtendParam),
    ]

class RKLLMLoraAdapter(ctypes.Structure):
    _fields_ = [
        ("lora_adapter_path", ctypes.c_char_p),
        ("lora_adapter_name", ctypes.c_char_p),
        ("scale", ctypes.c_float)
    ]

class RKLLMEmbedInput(ctypes.Structure):
    _fields_ = [
        ("embed", ctypes.POINTER(ctypes.c_float)),
        ("n_tokens", ctypes.c_size_t)
    ]

class RKLLMTokenInput(ctypes.Structure):
    _fields_ = [
        ("input_ids", ctypes.POINTER(ctypes.c_int32)),
        ("n_tokens", ctypes.c_size_t)
    ]

class RKLLMMultiModelInput(ctypes.Structure):
    _fields_ = [
        ("prompt", ctypes.c_char_p),
        ("image_embed", ctypes.POINTER(ctypes.c_float)),
        ("n_image_tokens", ctypes.c_size_t),
        ("n_image", ctypes.c_size_t),
        ("image_width", ctypes.c_size_t),
        ("image_height", ctypes.c_size_t),
    ]

class RKLLMInputUnion(ctypes.Union):
    _fields_ = [
        ("prompt_input", ctypes.c_char_p),
        ("embed_input", RKLLMEmbedInput),
        ("token_input", RKLLMTokenInput),
        ("multimodal_input", RKLLMMultiModelInput)
    ]

class RKLLMInput(ctypes.Structure):
    _fields_ = [
        ("input_type", ctypes.c_int),
        ("input_data", RKLLMInputUnion),
    ]

    # Backwards-compatibility: expose input_mode alias used by older code
    @property
    def input_mode(self):  # pragma: no cover
        return self.input_type

    @input_mode.setter
    def input_mode(self, value):  # pragma: no cover
        self.input_type = value

class RKLLMLoraParam(ctypes.Structure):
    _fields_ = [
        ("lora_adapter_name", ctypes.c_char_p)
    ]

class RKLLMPromptCacheParam(ctypes.Structure):
    _fields_ = [
        ("save_prompt_cache", ctypes.c_int),
        ("prompt_cache_path", ctypes.c_char_p)
    ]

class RKLLMInferParam(ctypes.Structure):
    _fields_ = [
        ("mode", RKLLMInferMode_t),
        ("lora_params", ctypes.POINTER(RKLLMLoraParam)),
        ("prompt_cache_params", ctypes.POINTER(RKLLMPromptCacheParam)),
        ("keep_history", ctypes.c_int),
    ]

class RKLLMResultLastHiddenLayer(ctypes.Structure):
    _fields_ = [
        ("hidden_states", ctypes.POINTER(ctypes.c_float)),
        ("embd_size", ctypes.c_int),
        ("num_tokens", ctypes.c_int)
    ]

class RKLLMResultLogits(ctypes.Structure):
    _fields_ = [
        ("logits", ctypes.POINTER(ctypes.c_float)),
        ("vocab_size", ctypes.c_int),
        ("num_tokens", ctypes.c_int),
    ]

class RKLLMResult(ctypes.Structure):
    _fields_ = [
        ("text", ctypes.c_char_p),
        ("token_id", ctypes.c_int32),
        ("last_hidden_layer", RKLLMResultLastHiddenLayer),
        ("logits", RKLLMResultLogits),
    ]

class LLMCallState:
    """Enumeration of callback states returned by the runtime."""
    RKLLM_RUN_NORMAL = RKLLM_RUN_NORMAL
    RKLLM_RUN_WAITING = RKLLM_RUN_WAITING
    RKLLM_RUN_FINISH = RKLLM_RUN_FINISH
    RKLLM_RUN_ERROR = RKLLM_RUN_ERROR
    # Retain legacy constant for projects that still reference it
    RKLLM_RUN_GET_LAST_HIDDEN_LAYER = 4

class RKLLMInputMode:  # Legacy alias – use RKLLMInputType going forward
    RKLLM_INPUT_PROMPT = RKLLM_INPUT_PROMPT
    RKLLM_INPUT_TOKEN = RKLLM_INPUT_TOKEN
    RKLLM_INPUT_EMBED = RKLLM_INPUT_EMBED
    RKLLM_INPUT_MULTIMODAL = RKLLM_INPUT_MULTIMODAL

class RKLLMInputType(RKLLMInputMode):
    """Preferred alias matching the C header (RKLLMInputType)."""
    pass

class RKLLMInferMode:
    RKLLM_INFER_GENERATE = RKLLM_INFER_GENERATE
    RKLLM_INFER_GET_LAST_HIDDEN_LAYER = RKLLM_INFER_GET_LAST_HIDDEN_LAYER
    RKLLM_INFER_GET_LOGITS = RKLLM_INFER_GET_LOGITS