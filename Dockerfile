# Используем образ из архива
FROM debian:bullseye-slim AS base

ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    procps

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip3 install --target=/app/dependencies -r requirements.txt

# Шаг 2: Сборка окончательного образа
FROM base AS release

RUN useradd -m apprunner
USER apprunner

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="${PYTHONPATH}:/app/dependencies"

WORKDIR /app
COPY --chown=apprunner: . /app
RUN chmod +x setup.sh

ARG PORT=8000
EXPOSE ${PORT}

CMD ["python3", "main.py"]
