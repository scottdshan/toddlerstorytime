# Toddler Storyteller

A bedtime story generation application that creates personalized stories for toddlers using AI.

## Features

- Generate personalized bedtime stories for toddlers
- Select from various themes, settings, and characters
- Include the child's name in the story
- Text-to-speech narration of stories using multiple voice providers
- Save stories for future reading

## Technologies Used

- Python 3.12
- FastAPI for the backend API
- SQLAlchemy for database interaction
- Pydantic for data validation
- Multiple LLM providers (OpenAI, Anthropic Claude, Azure OpenAI)
- Multiple TTS providers (ElevenLabs, Amazon Polly)
- SQLite for database storage

## Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/scottdshan/toddlerstorytime.git
cd toddlerstorytime
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (create a .env file):
```
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

## Usage

1. Navigate to http://localhost:8000 in your web browser
2. Use the story builder to create personalized stories
3. Listen to the narrated story or read it on screen
4. Save favorite stories for future reading

## API Endpoints

- `POST /api/stories/generate`: Generate a new story
- `GET /api/stories/recent`: Get recently generated stories
- `POST /api/audio/generate`: Generate audio for a story
- `GET /api/audio/voices`: Get available voices for a TTS provider

## Project Structure

- `app/core/`: Core story generation functionality
- `app/db/`: Database models and operations
- `app/endpoints/`: API endpoint definitions
- `app/llm/`: LLM provider implementations
- `app/tts/`: Text-to-speech provider implementations
- `app/templates/`: HTML templates for the web interface
- `app/static/`: Static assets including generated audio files 