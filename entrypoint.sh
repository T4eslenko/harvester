#!/bin/sh
# Копируем файлы проекта в монтируемую папку, исключая саму папку data
rsync -av --exclude 'data' /app/ /app/data/
# Запускаем приложение
exec "$@"
