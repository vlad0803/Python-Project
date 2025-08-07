# Energy Consumption Analyzer – FastAPI Microservice


This application is available as a Docker image and can be run directly as a container. It analyzes energy consumption data for household devices (e.g., washing machine, dishwasher) and provides usage recommendations based on detected usage patterns and estimated solar production.

The system receives commands as text (e.g., "turn on washing machine"), detects the target device, logs the command, performs cycle detection, trains basic ML models, and generates optimal usage suggestions. It also supports Whisper-based audio transcription. All data is saved under `/app/data` inside the container.


## Project structure and main files

### Script directory (`Script/`)
- `backend.py` – Main FastAPI application
- `pattern.py` – Pattern analysis logic
- `history.py` – Saves and loads device command history
- `devices.py` – Detects devices from input text using NLP (spaCy)
- `recommendations.py` – Generates device usage recommendations using ML
- `cycle_detection.py` – Detects consumption cycles in data
- `solar_production_simulation.py` – Simulates solar production
- `recommendation_trainer.py` – Trains RandomForest recommendation models
- `models.py` – Pydantic schemas for API requests and responses

### Root files
- `front.html` – Basic UI for interacting with the API

### Data directory (`data/`)
- Contains CSV consumption data, AI stats JSON, model pickles, and `istoric_comenzi.jsonl` command log

## Project requirements

- Python 3.12+
- All dependencies from `requirements.txt` (automatically installed in Docker):
- `ffmpeg` (automatically installed in the container for audio processing)
- spaCy English language model (`en_core_web_sm`, automatically installed in the container)

## How to run locally

```sh
uvicorn backend:app
```

#### You can test the API using the interactive Swagger interface at: [http://localhost:8000/docs](http://localhost:8000/docs)

## How to use the Docker image

**Pull the image from Docker Hub:**
```sh
docker pull vlad08/backend-energy:latest
```

**Run the container:**
```sh
docker run -d --name backend-energy-container -p 8000:8000 vlad08/backend-energy:latest
```

**View container logs:**
```sh
docker logs -f backend-energy-container
```

#### The API docs will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

## HTML Web Interface – `front.html`

The application includes a simple HTML-based frontend (`front.html`) that allows users to interact with the backend directly from the browser.

This interface supports both text and **live voice commands**.

With this frontend, you can:

  - Submit commands as plain text (e.g., "turn on washing machine")
- Use your microphone to record voice commands
- Trigger device detection, pattern analysis, and recommendation generation
- View analysis results, scores, and recommendations directly in the interface

#### Open `front.html` in your browser

#### Interact using:
   - Text input – send typed commands
   - Voice input – click the microphone button to record and submit a vocal command

#### View results: pattern analysis, predicted usage times, and AI-generated recommendations

#### Voice commands are transcribed on the backend using OpenAI Whisper.

