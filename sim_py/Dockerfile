FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY huawei_sim/ huawei_sim/

RUN pip install --no-cache-dir fastapi uvicorn pydantic

EXPOSE 8200 8201

CMD ["python", "-m", "huawei_sim"]
