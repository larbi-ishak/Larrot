FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY larrot/ larrot/

RUN pip install --no-cache-dir fastapi uvicorn pydantic

# Containers must bind 0.0.0.0 for port mapping to reach the app
ENV SIM_HOST=0.0.0.0

EXPOSE 8200 8201

CMD ["python", "-m", "larrot"]
