#!/bin/sh
# Копируем файлы проекта в монтируемую папку
cp -r /app/* /app/data/
# Запускаем приложение
exec "$@"