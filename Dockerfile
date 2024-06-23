# Используем базовый образ Debian
FROM debian:bullseye-slim as build

# Устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    procps \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxrender1 \
    libxext6 \
    libfontconfig1 \
    libx11-6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копируем шрифты в контейнер
COPY no_image.png /app/no_image.png
    
# Устанавливаем зависимости из requirements.txt
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install --no-cache-dir -r requirements.txt

# Копируем исходный код в рабочую директорию контейнера
COPY . /app

# Устанавливаем права доступа к рабочей директории
RUN chown -R root:root /app && chmod -R 755 /app

# Запускаем приложение при старте контейнера
CMD ["python3", "main.py"]
