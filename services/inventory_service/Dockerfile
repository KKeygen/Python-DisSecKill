FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY inventory_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY inventory_service/app ./app
COPY common/nacos_registry.py ./app/_nacos_common.py

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
