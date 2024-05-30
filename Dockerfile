# Используем базовый образ Debian
FROM debian:bullseye-slim as build

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости из requirements.txt
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install --no-cache-dir -r requirements.txt

# Копируем исходный код в рабочую директорию контейнера
COPY . /app

# Запускаем приложение при старте контейнера
CMD ["python3", "main.py"]
