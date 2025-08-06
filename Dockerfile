# Dockerfile pentru backend Python
FROM python:3.12-slim

# Setează directorul de lucru
WORKDIR /app

# Copiază fișierele necesare
COPY requirements.txt ./
COPY Script ./Script
COPY data/ /app/data/

# Instalează ffmpeg pentru procesarea audio
RUN apt-get update && apt-get install -y ffmpeg

# Instalează dependențele
RUN pip install --no-cache-dir -r requirements.txt

# Setează variabila de mediu pentru Python
ENV PYTHONPATH="/app/Script"

# Instalează modelul spaCy pentru limba română
RUN python -m spacy download en_core_web_sm

# Expune portul
EXPOSE 8000

# Rulează backend-ul cu Uvicorn
CMD ["uvicorn", "Script.backend:app", "--host", "0.0.0.0", "--port", "8000"]
