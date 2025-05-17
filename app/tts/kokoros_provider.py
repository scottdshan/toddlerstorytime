import os
import logging
import asyncio
import uuid
from typing import Optional, List, Dict, Any, AsyncGenerator
import sounddevice as sd # Dependency for kokoro-onnx stream playback, might not be needed just for yielding bytes
import numpy as np
import io
import wave

from app.tts.base import TTSProvider
from app.config import AUDIO_DIR
from kokoro_onnx import Kokoro

logger = logging.getLogger(__name__)

# Default paths for model and voice files
DEFAULT_MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "kokoro"))
DEFAULT_KOKORO_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, "kokoro-v1.0_uint8fp16.onnx")
DEFAULT_KOKORO_VOICES_PATH = os.path.join(DEFAULT_MODEL_DIR, "voices-v1.0.bin")

class KokorosProvider(TTSProvider):
    """
    TTS provider implementation using the kokoro-onnx library.
    Uses the library's streaming API based on the ONNX model.
    Library: https://github.com/thewh1teagle/kokoro-onnx
    Model: https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX
    """

    def __init__(self, voice_id: Optional[str] = None, 
                 model_path: Optional[str] = None, 
                 voices_path: Optional[str] = None):
        """
        Initialize the Kokoros ONNX provider.

        Args:
            voice_id: Default voice ID to use (e.g., "af_sky"). Defaults to "af_sky".
            model_path: Path to the Kokoro ONNX model file.
            voices_path: Path to the Kokoro voices binary file.
        """
        if Kokoro is None:
            raise RuntimeError("kokoro-onnx library is not installed. Cannot initialize KokorosProvider.")

        # Default to a known good voice if none provided
        self.default_voice_id = voice_id or os.environ.get("KOKOROS_DEFAULT_VOICE_ID", "af_sky") 
        
        # Determine model and voices paths
        self.model_path = os.path.expanduser(model_path or os.environ.get("KOKORO_MODEL_PATH", DEFAULT_KOKORO_MODEL_PATH))
        self.voices_path = os.path.expanduser(voices_path or os.environ.get("KOKORO_VOICES_PATH", DEFAULT_KOKORO_VOICES_PATH))

        # Validate paths
        if not os.path.exists(self.model_path):
            logger.error(f"Kokoro ONNX model not found at: {self.model_path}")
            raise FileNotFoundError(f"Kokoro ONNX model not found at: {self.model_path}")
        if not os.path.exists(self.voices_path):
            logger.error(f"Kokoro voices file not found at: {self.voices_path}")
            raise FileNotFoundError(f"Kokoro voices file not found at: {self.voices_path}")

        # Load the Kokoro model
        try:
            # Assuming Kokoro constructor doesn't block significantly.
            # If it does, consider lazy loading or running in a thread.
            self.kokoro = Kokoro(self.model_path, self.voices_path)
        except Exception as e:
            logger.error(f"Failed to load Kokoro model from {self.model_path} and voices {self.voices_path}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to load Kokoro model: {e}")
            
        self.output_dir = AUDIO_DIR
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(f"Initialized Kokoros ONNX Provider with model: {self.model_path}, voices: {self.voices_path}, default voice: {self.default_voice_id}")

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get a list of available voices.
        NOTE: kokoro-onnx library doesn't seem to have a public API for this.
        Returning a static list based on known voices.
        """
        # TODO: Check if kokoro-onnx adds a voice listing feature or parse voices.bin?
        logger.warning("Kokoros ONNX voice listing is currently static.")
        # Based on https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX#voicessamples
        return [
            # American Female
            {"voice_id": "af_heart", "name": "Heart (American Female)"},
            {"voice_id": "af_alloy", "name": "Alloy (American Female)"},
            {"voice_id": "af_aoede", "name": "Aoede (American Female)"},
            {"voice_id": "af_bella", "name": "Bella (American Female)"},
            {"voice_id": "af_jessica", "name": "Jessica (American Female)"},
            {"voice_id": "af_kore", "name": "Kore (American Female)"},
            {"voice_id": "af_nicole", "name": "Nicole (American Female)"},
            {"voice_id": "af_nova", "name": "Nova (American Female)"},
            {"voice_id": "af_river", "name": "River (American Female)"},
            {"voice_id": "af_sarah", "name": "Sarah (American Female)"},
            {"voice_id": "af_sky", "name": "Sky (American Female)"},
            # American Male
            {"voice_id": "am_adam", "name": "Adam (American Male)"},
            {"voice_id": "am_echo", "name": "Echo (American Male)"},
            {"voice_id": "am_eric", "name": "Eric (American Male)"},
            {"voice_id": "am_fenrir", "name": "Fenrir (American Male)"},
            {"voice_id": "am_liam", "name": "Liam (American Male)"},
            {"voice_id": "am_michael", "name": "Michael (American Male)"},
            {"voice_id": "am_onyx", "name": "Onyx (American Male)"},
            {"voice_id": "am_puck", "name": "Puck (American Male)"},
            {"voice_id": "am_santa", "name": "Santa (American Male)"},
            # British Female
            {"voice_id": "bf_alice", "name": "Alice (British Female)"},
            {"voice_id": "bf_emma", "name": "Emma (British Female)"},
            {"voice_id": "bf_isabella", "name": "Isabella (British Female)"},
            {"voice_id": "bf_lily", "name": "Lily (British Female)"},
            # British Male
            {"voice_id": "bm_daniel", "name": "Daniel (British Male)"},
            {"voice_id": "bm_fable", "name": "Fable (British Male)"},
            {"voice_id": "bm_george", "name": "George (British Male)"},
            {"voice_id": "bm_lewis", "name": "Lewis (British Male)"},
        ]

    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the Kokoros ONNX service.
        """
        voices = self.get_available_voices()
        return {
            'service': 'Kokoros (Local ONNX)',
            'description': 'Kokoros TTS using the kokoro-onnx library and ONNX runtime.',
            'voices_available': len(voices),
            'default_voice': self.default_voice_id,
            'model_path': self.model_path,
            'voices_path': self.voices_path,
            'library': 'https://github.com/thewh1teagle/kokoro-onnx'
        }

    async def generate_audio_streaming(self, text: str, 
                                      voice_id: Optional[str] = None, 
                                      story_info: Optional[Dict[str, Any]] = None) -> AsyncGenerator[bytes, None]:
        """
        Generate WAV audio data from text in a streaming fashion using kokoro-onnx.

        Args:
            text: The text to convert to speech.
            voice_id: Optional voice ID to use (e.g., "af_sky").
            story_info: Optional dictionary (not currently used).

        Returns:
            Async generator yielding chunks of raw PCM audio data (as bytes).
        """
        if not self.kokoro:
             logger.error("Kokoro ONNX model not loaded. Cannot generate audio.")
             yield b"" # Yield empty to avoid breaking caller
             return
             
        selected_voice_id = voice_id or self.default_voice_id
        # Speed parameter could be added if needed
        speed = 1.0 
        # Language - assuming 'en-us' for now based on example, might need adjustment
        lang = "en-us" 
        
        logger.info(f"Starting Kokoros ONNX stream for voice: {selected_voice_id}, lang: {lang}")
        
        try:
            # The create_stream is async, perfect for our use case.
            stream = self.kokoro.create_stream(
                text,
                voice=selected_voice_id,
                speed=speed,
                lang=lang,
            )

            async for samples, sample_rate in stream:
                # samples is likely a numpy array of float32. Convert to bytes (PCM16 for wide compatibility).
                # Ensure data is in the range [-1, 1] before scaling
                samples = np.clip(samples, -1.0, 1.0)
                # Scale to 16-bit integer range
                int_samples = (samples * 32767).astype(np.int16)
                yield int_samples.tobytes()
            
            logger.info(f"Kokoros ONNX streaming finished successfully.")

        except Exception as e:
            logger.error(f"Error during Kokoros ONNX streaming: {e}", exc_info=True)
            # Yield empty chunk on error to potentially prevent breaking consumer?
            yield b""

    def _generate_wav_file(self, samples: np.ndarray, sample_rate: int, file_path: str):
        """Helper to save numpy audio samples to a WAV file."""
        # Scale to 16-bit integer range
        int_samples = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
        
        with wave.open(file_path, 'wb') as wf:
            wf.setnchannels(1)  # Assuming mono audio
            wf.setsampwidth(2)  # 2 bytes for int16
            wf.setframerate(sample_rate)
            wf.writeframes(int_samples.tobytes())

    def generate_audio(self, text: str, voice_id: Optional[str] = None, story_info: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate audio to a file (non-streaming) using kokoro-onnx.
        This synthesizes the full audio first, then saves it.
        
        Args:
            text: The text to convert to speech.
            voice_id: Optional voice ID.
            story_info: Optional dictionary for filename generation.

        Returns:
            Path (URL) to the generated audio file or None if generation failed.
        """
        if not self.kokoro:
             logger.error("Kokoro ONNX model not loaded. Cannot generate audio.")
             return None
             
        selected_voice_id = voice_id or self.default_voice_id
        speed = 1.0
        lang = "en-us"

        # Create a unique filename
        filename_base = f"kokoros_onnx_audio_{uuid.uuid4()}"
        output_filename = f"{filename_base}.wav"
        output_filepath = os.path.join(self.output_dir, output_filename)

        logger.info(f"Generating Kokoros ONNX audio file for voice: {selected_voice_id}, lang: {lang}")

        try:
            # Run generation (this might be blocking, consider thread if slow)
            # The 'generate' method seems to be synchronous in the library
            # If it exists and works like the stream example suggests.
            # Assuming a generate method similar to the stream exists or can be adapted.
            # Let's simulate it by collecting stream output for now.
            
            # --- Simulation using stream --- 
            all_samples = []
            sample_rate = 24000 # Assume default sample rate from example
            
            async def collect_audio():
                nonlocal all_samples, sample_rate
                stream = self.kokoro.create_stream(text, voice=selected_voice_id, speed=speed, lang=lang)
                first_chunk = True
                async for samples_chunk, rate_chunk in stream:
                    if first_chunk:
                        sample_rate = rate_chunk
                        first_chunk = False
                    all_samples.append(samples_chunk)
            
            # Run the async stream collector synchronously
            try:
                asyncio.run(collect_audio())
            except RuntimeError as e:
                 # Handle case where asyncio event loop is already running (e.g., in FastAPI)
                 if "cannot run loop" in str(e):
                      logger.warning("Asyncio loop already running. Using existing loop for Kokoro audio generation.")
                      # Get the current event loop
                      loop = asyncio.get_event_loop()
                      # Run the coroutine in the existing loop
                      loop.run_until_complete(collect_audio())
                 else:
                      raise e # Re-raise other RuntimeErrors
            
            if not all_samples:
                logger.error("Kokoro ONNX generation produced no audio samples.")
                return None
                
            # Concatenate all sample chunks
            full_audio = np.concatenate(all_samples)
            # --- End Simulation --- 
            
            # Save the concatenated audio to a WAV file
            self._generate_wav_file(full_audio, sample_rate, output_filepath)

            logger.info(f"Kokoros ONNX generated audio file: {output_filepath}")
            
            # Return the web-accessible path
            relative_path = f"/static/audio/{output_filename}"
            return relative_path

        except Exception as e:
            logger.error(f"Error generating audio file with Kokoros ONNX: {e}", exc_info=True)
            return None 