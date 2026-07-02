#!/usr/bin/env python3
import sys
import os
import json

# Определение директорий
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

# Добавляем путь к скриптам в sys.path, чтобы импортировать сгенерированный geosite_pb2
sys.path.append(SCRIPT_DIR)

try:
    import geosite_pb2
except ImportError:
    print("[-] Ошибка: Не удалось импортировать geosite_pb2. Сначала скомпилируйте geosite.proto с помощью protoc.")
    sys.exit(1)

def parse_geosite(dat_path, categories):
    if not os.path.exists(dat_path):
        print(f"[-] Ошибка: Файл {dat_path} не найден.")
        sys.exit(1)

    print(f"[+] Чтение {dat_path}...")
    with open(dat_path, "rb") as f:
        data = f.read()

    site_list = geosite_pb2.GeoSiteList()
    try:
        site_list.ParseFromString(data)
    except Exception as e:
        print(f"[-] Ошибка при парсинге protobuf: {e}")
        sys.exit(1)

    categories_lower = {c.lower(): c for c in categories}
    parsed_data = {c: {
        "domain": [],
        "domain_suffix": [],
        "domain_keyword": [],
        "domain_regex": []
    } for c in categories}

    print(f"[+] Поиск категорий: {', '.join(categories)}")
    found_categories = set()

    for entry in site_list.entry:
        code_lower = entry.country_code.lower()
        if code_lower in categories_lower:
            orig_category = categories_lower[code_lower]
            found_categories.add(orig_category)
            cat_data = parsed_data[orig_category]

            for d in entry.domain:
                val = d.value.strip()
                if not val:
                    continue

                # Типы доменов:
                # Plain = 0 -> keyword
                # Regex = 1 -> regex
                # Domain = 2 -> RootDomain (домен + все поддомены)
                # Full = 3 -> точное совпадение
                if d.type == 0:  # Plain / Keyword
                    cat_data["domain_keyword"].append(val)
                elif d.type == 1:  # Regex
                    cat_data["domain_regex"].append(val)
                elif d.type == 2:  # Domain (RootDomain)
                    # Если в значении есть точка: добавляет в domain (exact)
                    if "." in val:
                        cat_data["domain"].append(val)
                    # Всегда добавляет в domain_suffix с ведущей точкой (.example.com)
                    if not val.startswith("."):
                        cat_data["domain_suffix"].append(f".{val}")
                    else:
                        cat_data["domain_suffix"].append(val)
                elif d.type == 3:  # Full / Exact
                    cat_data["domain"].append(val)

    # Запись результатов в файлы
    output_dir = os.path.join(REPO_ROOT, "src", "runetfreedom")
    os.makedirs(output_dir, exist_ok=True)

    for cat, data_dict in parsed_data.items():
        # Сортировка и дедупликация
        for k in data_dict:
            data_dict[k] = sorted(list(set(data_dict[k])))

        output_path = os.path.join(output_dir, f"{cat}.json")
        output_json = {
            "version": 1,
            "rules": [data_dict]
        }
        with open(output_path, "w", encoding="utf-8") as out_f:
            json.dump(output_json, out_f, indent=2, ensure_ascii=False)
        print(f"[+] Записан {output_path} (доменов: {len(data_dict['domain'])}, суффиксов: {len(data_dict['domain_suffix'])})")

    missing = set(categories) - found_categories
    if missing:
        print(f"[!] Предупреждение: Категории не найдены в geosite.dat: {', '.join(missing)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python3 parse_geosite.py <путь_к_geosite.dat> <категория1> [категория2 ...]")
        sys.exit(1)

    dat_path = sys.argv[1]
    categories = sys.argv[2:]
    parse_geosite(dat_path, categories)
