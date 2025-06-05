FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 # Рекомендуется для логов в Docker
WORKDIR /app
# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    # psycopg2-binary может требовать libpq-dev, если используется, но здесь asyncpg
    && rm -rf /var/lib/apt/lists/*
# Копирование requirements
COPY requirements.txt .
# Рекомендуется использовать --no-cache-dir для уменьшения размера образа
RUN pip install --no-cache-dir -r requirements.txt
# Копирование кода
COPY . .
# Создание директории для логов, если она еще не создана
RUN mkdir -p /app/logs
# Точка входа
CMD ["python", "main.py"]