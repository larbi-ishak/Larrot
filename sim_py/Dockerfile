FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY larrot/ larrot/

RUN pip install --no-cache-dir fastapi uvicorn pydantic

EXPOSE 8200 8201

CMD ["python", "-m", "larrot"]
