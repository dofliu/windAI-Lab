FROM python:3.11-slim AS base

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# 安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製原始碼
COPY src/ src/
COPY configs/ configs/
COPY pyproject.toml .

EXPOSE 5800

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "5800"]
