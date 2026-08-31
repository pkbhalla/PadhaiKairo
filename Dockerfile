FROM python:3.11-slim

WORKDIR /app

# Install build essentials for native packages if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Set environment defaults for Cloud Run & Vertex AI
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV USE_VERTEX_AI=true
ENV VERTEX_AI_LOCATION=us-central1
ENV GOOGLE_CLOUD_PROJECT=project-925dcd70-fea8-462c-b7a
ENV MODEL=gemini-2.5-flash

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
