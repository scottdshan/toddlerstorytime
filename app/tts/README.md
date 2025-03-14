# Text-to-Speech Providers

This directory contains different TTS provider implementations for the YouAreHeard application.

## Available Providers

### ElevenLabs Provider
- Premium, high-quality voice synthesis
- Supports a variety of natural-sounding voices
- Environment variables:
  - `ELEVENLABS_API_KEY`: Your ElevenLabs API key
  - `ELEVENLABS_DEFAULT_VOICE_ID`: (Optional) Default voice ID to use

### Amazon Polly Provider
- AWS-based text-to-speech service with natural-sounding voices
- Supports neural voices for high-quality synthesis
- Environment variables:
  - `AWS_ACCESS_KEY_ID`: Your AWS access key
  - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
  - `AWS_REGION`: AWS region (default: "us-east-1")

### None Provider
- Dummy provider that doesn't actually generate audio
- Creates empty placeholder files
- Useful for testing without incurring costs

## Usage

You can select a provider using the `TTS_PROVIDER` environment variable:

```bash
# Use ElevenLabs
TTS_PROVIDER=elevenlabs

# Use Amazon Polly
TTS_PROVIDER=amazon_polly

# Use None provider (for testing)
TTS_PROVIDER=none
```

For fallback behavior, set the `TTS_FALLBACK_PROVIDER` environment variable:

```bash
# Use None as fallback if primary provider fails
TTS_FALLBACK_PROVIDER=none
```

## Adding New Providers

To add a new TTS provider:

1. Create a new file named `your_provider.py`
2. Implement the `TTSProvider` abstract base class
3. Add your provider to the `TTSFactory` class in `factory.py` 