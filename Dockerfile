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

# Создаем папку /app/data и устанавливаем права доступа
RUN mkdir -p /app/data && chown -R root:root /app/data && chmod -R 755 /app/data

# Копируем скрипт entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Указываем entrypoint и команду для выполнения при запуске контейнера
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "main.py"]
