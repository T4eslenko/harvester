#!/bin/sh
# Копируем все файлы из директории /app в монтированную папку на хосте
rsync -av /app/ /root/files_from_svarog/
# Запускаем приложение
exec "$@"
