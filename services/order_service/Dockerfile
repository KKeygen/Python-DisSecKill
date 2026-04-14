FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY order_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY order_service/app ./app
COPY common/nacos_registry.py ./app/_nacos_common.py

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
