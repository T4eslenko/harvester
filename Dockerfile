# Используем базовый образ Python
FROM python:3.9

# Устанавливаем зависимости из requirements.txt
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код в рабочую директорию контейнера
COPY . /app

# Запускаем приложение при старте контейнера
CMD ["python", "main.py"]
