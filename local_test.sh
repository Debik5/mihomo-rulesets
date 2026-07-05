#!/bin/bash
set -e

# Определение директорий
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[+] Создание директории src..."
mkdir -p src

echo "[+] Скачивание исходных файлов..."
curl -L -o src/whitelist.txt https://raw.githubusercontent.com/hxehex/russia-mobile-internet-whitelist/main/whitelist.txt
curl -L -o src/geosite.dat https://raw.githubusercontent.com/runetfreedom/russia-blocked-geosite/release/geosite.dat
curl -L -o src/geoip.dat https://raw.githubusercontent.com/runetfreedom/russia-blocked-geoip/release/geoip.dat
curl -L -o src/refilter_geosite.dat https://github.com/1andrevich/Re-filter-lists/releases/latest/download/geosite.dat
curl -L -o src/refilter_geoip.dat https://github.com/1andrevich/Re-filter-lists/releases/latest/download/geoip.dat
if [ -f ../tranco_top_1m.zip ]; then
    echo "[+] Копирование локального tranco_top_1m.zip..."
    cp ../tranco_top_1m.zip src/
else
    echo "[+] Скачивание tranco_top_1m.zip..."
    curl -L -o src/tranco_top_1m.zip https://tranco-list.eu/top-1m.csv.zip
fi

echo "[+] Проверка наличия protoc..."
if ! command -v protoc &> /dev/null; then
    echo "[-] Ошибка: protoc не установлен. Установите его с помощью 'brew install protobuf' и запустите скрипт снова."
    exit 1
fi

# Зависимости Python (pyyaml, protobuf) уже должны быть установлены в системе

echo "[+] Компиляция geosite.proto..."
cd scripts
protoc --python_out=. geosite.proto
cd ..

echo "[+] Запуск парсеров..."
RUNETFREEDOM_GEOSITE_CATEGORIES="private category-ru ru-available-only-inside ru-blocked ru-blocked-all"
RUNETFREEDOM_GEOIP_CATEGORIES="ru ru-whitelist private"

cd scripts
python3 parse_geosite.py ../src/geosite.dat $RUNETFREEDOM_GEOSITE_CATEGORIES
python3 parse_geoip.py ../src/geoip.dat $RUNETFREEDOM_GEOIP_CATEGORIES
cd ..

echo "[+] Запуск build.py для генерации исключений..."
python3 scripts/build.py

echo "[+] Успешно! Сгенерированные файлы находятся в dist/:"
ls -lh dist/
