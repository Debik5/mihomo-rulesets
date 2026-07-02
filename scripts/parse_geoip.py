#!/usr/bin/env python3
import sys
import os
import json
import ipaddress

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

def parse_geoip(dat_path, categories):
    if not os.path.exists(dat_path):
        print(f"[-] Ошибка: Файл {dat_path} не найден.")
        sys.exit(1)

    print(f"[+] Чтение {dat_path}...")
    with open(dat_path, "rb") as f:
        data = f.read()

    geoip_list = geosite_pb2.GeoIPList()
    try:
        geoip_list.ParseFromString(data)
    except Exception as e:
        print(f"[-] Ошибка при парсинге protobuf: {e}")
        sys.exit(1)

    categories_lower = {c.lower(): c for c in categories}
    parsed_data = {c: [] for c in categories}

    print(f"[+] Поиск IP категорий: {', '.join(categories)}")
    found_categories = set()

    for entry in geoip_list.entry:
        code_lower = entry.country_code.lower()
        if code_lower in categories_lower:
            orig_category = categories_lower[code_lower]
            found_categories.add(orig_category)
            ip_list = parsed_data[orig_category]

            for cidr in entry.cidr:
                try:
                    ip_addr = ipaddress.ip_address(cidr.ip)
                    ip_list.append(f"{ip_addr}/{cidr.prefix}")
                except Exception as ex:
                    print(f"[-] Ошибка конвертации IP из байт {cidr.ip.hex()}: {ex}")

    # Запись результатов в файлы
    output_dir = os.path.join(REPO_ROOT, "src", "runetfreedom-ip")
    os.makedirs(output_dir, exist_ok=True)

    for cat, ip_list in parsed_data.items():
        # Сортировка и дедупликация без вызова TypeError при смешивании IPv4/IPv6
        def ip_sort_key(cidr_str):
            try:
                net = ipaddress.ip_network(cidr_str)
                return (net.version, net.network_address.packed, net.prefixlen)
            except Exception:
                return (99, cidr_str.encode('utf-8'), 0)

        sorted_ips = sorted(list(set(ip_list)), key=ip_sort_key)
        sorted_ips = [str(ip) for ip in sorted_ips]

        output_path = os.path.join(output_dir, f"{cat}.json")
        output_json = {
            "ip_cidr": sorted_ips
        }
        with open(output_path, "w", encoding="utf-8") as out_f:
            json.dump(output_json, out_f, indent=2, ensure_ascii=False)
        print(f"[+] Записан {output_path} (IP диапазонов: {len(sorted_ips)})")

    missing = set(categories) - found_categories
    if missing:
        print(f"[!] Предупреждение: Категории не найдены в geoip.dat: {', '.join(missing)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python3 parse_geoip.py <путь_к_geoip.dat> <категория1> [категория2 ...]")
        sys.exit(1)

    dat_path = sys.argv[1]
    categories = sys.argv[2:]
    parse_geoip(dat_path, categories)
