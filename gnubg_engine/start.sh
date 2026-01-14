#!/bin/bash
# Получаем полный путь к этой папке (например /home/vater/gnubg_v1)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Запускаю GNUBG из папки: $DIR"

# Указываем программе этот полный путь
export GNUBG="$DIR"

# Запускаем
"$DIR/gnubg" -t
