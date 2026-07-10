#!/usr/bin/env python3
import sys
import os
import json
import time
import yaml
import shutil
import urllib.request
import zipfile
import ipaddress
import re
from google.protobuf.descriptor_pb2 import FileDescriptorProto, FieldDescriptorProto
from google.protobuf.descriptor_pool import DescriptorPool
from google.protobuf.message_factory import GetMessageClass

# Определение директорий
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

DIST_DIR = os.path.join(REPO_ROOT, "dist")
SRC_DIR = os.path.join(REPO_ROOT, "src")

# ─────────────────────────────────────────────────────────────────────────────
# КОНСТАНТЫ
# ─────────────────────────────────────────────────────────────────────────────

# Максимальный возраст кэшированных вспомогательных файлов (hagezi, oisd, adguard).
# Если файл старше этого порога — он будет перескачан при следующем запуске сборки.
MAX_CACHE_AGE_DAYS = 1

# Количество топовых доменов в refilter-optimized (по рейтингу Tranco).
# Меньше = быстрее матчинг правил в mihomo, больше = полнее покрытие.
TOP_REFILTER_DOMAINS = 100

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM_DOMAIN_RULESETS — декларативный список кастомных категорий
# ─────────────────────────────────────────────────────────────────────────────
# Каждый элемент описывает один выходной файл в dist/:
#
#   output  — имя выходного файла (без расширения .yaml/.mrs)
#   source  — имя JSON в src/runetfreedom/ (без .json), из которого берутся домены
#   exclude — список имён JSON в src/runetfreedom/ для вычитания (без .json)
#
# Как добавить новую категорию:
#   1. Убедись что категория есть в RUNETFREEDOM_GEOSITE_CATEGORIES в local_test.sh
#      и sync-and-build.yml — чтобы parse_geosite.py извлёк её из geosite.dat.
#   2. Добавь строку в список ниже.
#   3. Добавь rule-provider и правило в clashmeta-generator.py.
#
# Пример:
#   {"output": "runetfreedom-streaming", "source": "category-streaming", "exclude": []},
# ─────────────────────────────────────────────────────────────────────────────
CUSTOM_DOMAIN_RULESETS = [
    {
        "output":  "runetfreedom-category-games",  # dist/runetfreedom-category-games.yaml
        "source":  "category-games-!cn",            # src/runetfreedom/category-games-!cn.json
        "exclude": ["supercell"],                   # вычесть src/runetfreedom/supercell.json
    },
    # Добавляй новые категории сюда ↓
]

# Очистка и пересоздание директории dist перед сборкой
if os.path.exists(DIST_DIR):
    shutil.rmtree(DIST_DIR)
os.makedirs(DIST_DIR, exist_ok=True)

# Инициализация динамического Protobuf-парсера для geosite.dat и geoip.dat
file_proto = FileDescriptorProto()
file_proto.name = "geodata.proto"
file_proto.package = "geodat"

# message Domain
domain_desc = file_proto.message_type.add()
domain_desc.name = "Domain"
type_enum = domain_desc.enum_type.add()
type_enum.name = "Type"
for name, number in [("Plain", 0), ("Regex", 1), ("Domain", 2), ("Full", 3)]:
    val = type_enum.value.add()
    val.name = name
    val.number = number

f1 = domain_desc.field.add()
f1.name = "type"
f1.number = 1
f1.label = FieldDescriptorProto.LABEL_OPTIONAL
f1.type = FieldDescriptorProto.TYPE_ENUM
f1.type_name = ".geodat.Domain.Type"

f2 = domain_desc.field.add()
f2.name = "value"
f2.number = 2
f2.label = FieldDescriptorProto.LABEL_OPTIONAL
f2.type = FieldDescriptorProto.TYPE_STRING

# message GeoSite
geosite_desc = file_proto.message_type.add()
geosite_desc.name = "GeoSite"
f1 = geosite_desc.field.add()
f1.name = "country_code"
f1.number = 1
f1.label = FieldDescriptorProto.LABEL_OPTIONAL
f1.type = FieldDescriptorProto.TYPE_STRING

f2 = geosite_desc.field.add()
f2.name = "domain"
f2.number = 2
f2.label = FieldDescriptorProto.LABEL_REPEATED
f2.type = FieldDescriptorProto.TYPE_MESSAGE
f2.type_name = ".geodat.Domain"

# message GeoSiteList
gsl_desc = file_proto.message_type.add()
gsl_desc.name = "GeoSiteList"
f1 = gsl_desc.field.add()
f1.name = "entry"
f1.number = 1
f1.label = FieldDescriptorProto.LABEL_REPEATED
f1.type = FieldDescriptorProto.TYPE_MESSAGE
f1.type_name = ".geodat.GeoSite"

# message CIDR
cidr_desc = file_proto.message_type.add()
cidr_desc.name = "CIDR"
f1 = cidr_desc.field.add()
f1.name = "ip"
f1.number = 1
f1.label = FieldDescriptorProto.LABEL_OPTIONAL
f1.type = FieldDescriptorProto.TYPE_BYTES

f2 = cidr_desc.field.add()
f2.name = "prefix"
f2.number = 2
f2.label = FieldDescriptorProto.LABEL_OPTIONAL
f2.type = FieldDescriptorProto.TYPE_UINT32

# message GeoIP
geoip_desc = file_proto.message_type.add()
geoip_desc.name = "GeoIP"
f1 = geoip_desc.field.add()
f1.name = "country_code"
f1.number = 1
f1.label = FieldDescriptorProto.LABEL_OPTIONAL
f1.type = FieldDescriptorProto.TYPE_STRING

f2 = geoip_desc.field.add()
f2.name = "cidr"
f2.number = 2
f2.label = FieldDescriptorProto.LABEL_REPEATED
f2.type = FieldDescriptorProto.TYPE_MESSAGE
f2.type_name = ".geodat.CIDR"

# message GeoIPList
gipl_desc = file_proto.message_type.add()
gipl_desc.name = "GeoIPList"
f1 = gipl_desc.field.add()
f1.name = "entry"
f1.number = 1
f1.label = FieldDescriptorProto.LABEL_REPEATED
f1.type = FieldDescriptorProto.TYPE_MESSAGE
f1.type_name = ".geodat.GeoIP"

# Регистрация в пуле дескрипторов и создание классов
pool = DescriptorPool()
pool.Add(file_proto)
GeoSiteList = GetMessageClass(pool.FindMessageTypeByName("geodat.GeoSiteList"))
GeoIPList = GetMessageClass(pool.FindMessageTypeByName("geodat.GeoIPList"))

def deduplicate_domains(exact_domains, suffix_domains, sort_exact=True):
    # 1. Дедупликация суффиксов
    sorted_suffixes = sorted(list(set(suffix_domains or [])), key=len)
    unique_suffixes = set()
    for suf in sorted_suffixes:
        parts = suf.split('.')
        is_redundant = False
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in unique_suffixes:
                is_redundant = True
                break
        if not is_redundant:
            unique_suffixes.add(suf)

    # 2. Дедупликация точных совпадений относительно суффиксов
    unique_exact = set()
    for d in set(exact_domains or []):
        parts = d.split('.')
        is_redundant = False
        for i in range(len(parts)):
            suf = ".".join(parts[i:])
            if suf in unique_suffixes:
                is_redundant = True
                break
        if not is_redundant:
            unique_exact.add(d)

    if sort_exact:
        return sorted(list(unique_exact)), sorted(list(unique_suffixes))
    else:
        # Сохраняем исходный порядок exact_domains (например, сортировку по Tranco)
        ordered_exact = []
        for d in exact_domains:
            if d in unique_exact and d not in ordered_exact:
                ordered_exact.append(d)
        return ordered_exact, sorted(list(unique_suffixes))

def write_domain_outputs(name, exact_domains=None, suffix_domains=None, sort_exact=True):
    exact, suffix = deduplicate_domains(exact_domains, suffix_domains, sort_exact)

    if not exact and not suffix:
        print(f"[!] Предупреждение: Нет доменов для {name}, файлы не будут созданы.")
        return

    # Запись .yaml
    yaml_path = os.path.join(DIST_DIR, f"{name}.yaml")
    payload = []
    for d in exact:
        payload.append(d)
    for d in suffix:
        payload.append(f"+.{d}")

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"payload": payload}, f, default_flow_style=False, allow_unicode=True)

    print(f"[+] Записан {name}.yaml (точных: {len(exact)}, суффиксов: {len(suffix)})")

def write_ipcidr_outputs(name, cidrs):
    sorted_cidrs = sorted(list(set(cidrs or [])))

    if not sorted_cidrs:
        print(f"[!] Предупреждение: Нет IP/CIDR для {name}, файлы не будут созданы.")
        return

    # Запись .yaml
    yaml_path = os.path.join(DIST_DIR, f"{name}.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"payload": sorted_cidrs}, f, default_flow_style=False, allow_unicode=True)

    print(f"[+] Записан {name}.yaml (IP диапазонов: {len(sorted_cidrs)})")

def write_classical_yaml(name, keyword_domains=None, regex_domains=None):
    keywords = sorted(list(set(keyword_domains or [])))
    regexes = sorted(list(set(regex_domains or [])))

    if not keywords and not regexes:
        return

    payload = []
    for kw in keywords:
        payload.append(f"DOMAIN-KEYWORD,{kw}")
    for rx in regexes:
        payload.append(f"DOMAIN-REGEX,{rx}")

    yaml_path = os.path.join(DIST_DIR, f"{name}-extra.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"payload": payload}, f, default_flow_style=False, allow_unicode=True)

    print(f"[+] Записан классический {name}-extra.yaml (keywords: {len(keywords)}, regexes: {len(regexes)})")

def build_own_whitelist():
    whitelist_path = os.path.join(SRC_DIR, "whitelist.txt")
    if not os.path.exists(whitelist_path):
        print(f"[!] Предупреждение: {whitelist_path} не найден. Пропуск whitelist.")
        return

    domains = []
    with open(whitelist_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            domains.append(line)

    write_domain_outputs("ru-whitelist-domains", suffix_domains=domains)

def build_runetfreedom_categories():
    rf_dir = os.path.join(SRC_DIR, "runetfreedom")
    if not os.path.exists(rf_dir):
        print(f"[!] Предупреждение: Директория {rf_dir} не найдена. Пропуск geosite категорий.")
        return

    # Собираем категории, которые не нужно выводить как самостоятельные списки:
    # 1. Захардкоженные (ru-blocked, ru-blocked-all)
    # 2. Те, которые используются как "source" или "exclude" в CUSTOM_DOMAIN_RULESETS
    skip_categories = {"ru-blocked", "ru-blocked-all"}
    for rule in CUSTOM_DOMAIN_RULESETS:
        skip_categories.add(rule["source"])
        skip_categories.update(rule.get("exclude", []))

    for filename in os.listdir(rf_dir):
        if filename.endswith(".json"):
            category = filename[:-5]
            if category in skip_categories:
                continue
            json_path = os.path.join(rf_dir, filename)
            
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[-] Ошибка при чтении {json_path}: {e}")
                continue

            rules = data.get("rules", [])
            exact_domains = []
            suffix_domains = []
            keyword_domains = []
            regex_domains = []
            ip_cidr = []

            for r in rules:
                exact_domains.extend(r.get("domain", []))
                suffix_domains.extend(r.get("domain_suffix", []))
                keyword_domains.extend(r.get("domain_keyword", []))
                regex_domains.extend(r.get("domain_regex", []))
                ip_cidr.extend(r.get("ip_cidr", []))

            # domain_suffix после lstrip(".") у suffix
            suffix_stripped = [d.lstrip(".") for d in suffix_domains if d]

            # Переименование категорий под новый стандарт
            output_name = f"runetfreedom-{category}"
            if category == "category-ru":
                output_name = "runetfreedom-ru-domains"
            elif category == "private":
                output_name = "runetfreedom-private-domains"

            # Вывод доменных правил
            write_domain_outputs(
                output_name,
                exact_domains=exact_domains,
                suffix_domains=suffix_stripped
            )

            # Вывод классических правил (keyword / regex), если они есть
            if keyword_domains or regex_domains:
                write_classical_yaml(
                    output_name,
                    keyword_domains=keyword_domains,
                    regex_domains=regex_domains
                )

            # Вывод IP-правил, если вдруг они прокрались в geosite
            if ip_cidr:
                write_ipcidr_outputs(f"{output_name}-ip", ip_cidr)

def build_runetfreedom_ip_categories():
    rf_ip_dir = os.path.join(SRC_DIR, "runetfreedom-ip")
    if not os.path.exists(rf_ip_dir):
        print(f"[!] Предупреждение: Директория {rf_ip_dir} не найдена. Пропуск geoip категорий.")
        return

    for filename in os.listdir(rf_ip_dir):
        if filename.endswith(".json"):
            category = filename[:-5]
            json_path = os.path.join(rf_ip_dir, filename)

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[-] Ошибка при чтении {json_path}: {e}")
                continue

            ip_cidr = data.get("ip_cidr", [])
            
            # Переименование IP-категорий под новый стандарт
            output_name = f"runetfreedom-ip-{category}"
            if category == "ru-whitelist":
                output_name = "ru-whitelist-ips"
            elif category == "private":
                output_name = "runetfreedom-private-ips"
            elif category == "ru":
                output_name = "runetfreedom-ru-ips"

            write_ipcidr_outputs(output_name, ip_cidr)

# Программные функции парсинга Protobuf (.dat файлов) для оптимизации
def load_geosite_proto(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    geosite_list = GeoSiteList()
    geosite_list.ParseFromString(data)
    
    categories = {}
    for entry in geosite_list.entry:
        code = entry.country_code.upper()
        categories[code] = [(d.type, d.value) for d in entry.domain]
    return categories

def load_geoip_proto_as_ranges(filepath):
    with open(filepath, "rb") as f:
        data = f.read()
    geoip_list = GeoIPList()
    geoip_list.ParseFromString(data)
    
    categories = {}
    for entry in geoip_list.entry:
        code = entry.country_code.upper()
        ranges = []
        for c in entry.cidr:
            ip_bytes = c.ip
            prefix = c.prefix
            is_ipv6 = len(ip_bytes) == 16
            ip_int = int.from_bytes(ip_bytes, byteorder='big')
            
            bits = 128 if is_ipv6 else 32
            mask = ((1 << bits) - 1) ^ ((1 << (bits - prefix)) - 1) if prefix > 0 else 0
            start_int = ip_int & mask
            end_int = start_int + (1 << (bits - prefix)) - 1
            
            ranges.append((start_int, end_int, is_ipv6))
        categories[code] = ranges
    return categories

# Функции группировки сетей и диапазонов для быстрого пересечения
def group_ranges(ranges):
    grouped_v4 = {}
    grouped_v6 = []
    for start, end, is_ipv6 in ranges:
        if is_ipv6:
            grouped_v6.append((start, end))
        else:
            first_byte = start >> 24
            last_byte_start = end >> 24
            for byte in range(first_byte, last_byte_start + 1):
                if byte not in grouped_v4:
                    grouped_v4[byte] = []
                grouped_v4[byte].append((start, end))
    return grouped_v4, grouped_v6

def range_overlaps_any(target_range, grouped_v4, grouped_v6):
    start, end, is_ipv6 = target_range
    if is_ipv6:
        for s, e in grouped_v6:
            if start <= e and s <= end:
                return True
        return False
    else:
        first_byte = start >> 24
        last_byte = end >> 24
        for byte in range(first_byte, last_byte + 1):
            if byte in grouped_v4:
                for s, e in grouped_v4[byte]:
                    if start <= e and s <= end:
                        return True
        return False

def format_range_to_cidrs(r):
    """Конвертирует IP-диапазон (start, end, is_ipv6) в список CIDR-строк.

    Использует ipaddress.summarize_address_range() вместо ручного вычисления,
    что корректно обрабатывает любые диапазоны, включая нестандартные
    (не кратные степени двойки).
    """
    start, end, _ = r
    start_addr = ipaddress.ip_address(start)
    end_addr   = ipaddress.ip_address(end)
    return [str(net) for net in ipaddress.summarize_address_range(start_addr, end_addr)]

def parse_adguard(filepath):
    domains = set()
    pattern = re.compile(r"^\|\|([a-zA-Z0-9-._]+)\^")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("!"):
                    continue
                match = pattern.match(line)
                if match:
                    domains.add(match.group(1).lower())
    return domains

def parse_plain_domains(filepath):
    domains = set()
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                if " #" in line:
                    line = line.split(" #")[0].strip()
                parts = line.split()
                if len(parts) > 1 and (parts[0] == "0.0.0.0" or parts[0] == "127.0.0.1"):
                    domain = parts[1].lower()
                else:
                    domain = parts[0].lower()
                domains.add(domain)
    return domains

# Сборка оптимизированных списков Re-filter
def build_refilter_optimized():
    print("[+] Сборка оптимизированных списков на базе Re-filter-lists...")
    
    # Пути к файлам
    refilter_geosite_path = os.path.join(SRC_DIR, "refilter_geosite.dat")
    refilter_geoip_path = os.path.join(SRC_DIR, "refilter_geoip.dat")
    runet_geosite_path = os.path.join(SRC_DIR, "geosite.dat")
    runet_geoip_path = os.path.join(SRC_DIR, "geoip.dat")
    
    hagezi_path = os.path.join(SRC_DIR, "hagezi_tif.txt")
    oisd_path = os.path.join(SRC_DIR, "oisd_big.txt")
    adguard_path = os.path.join(SRC_DIR, "adguard_dns.txt")
    whitelist_path = os.path.join(SRC_DIR, "whitelist.txt")
    tranco_csv_path = os.path.join(SRC_DIR, "tranco_top_1m.csv")

    # Проверка наличия обязательных локальных баз
    if not all(os.path.exists(p) for p in [refilter_geosite_path, refilter_geoip_path, runet_geosite_path, runet_geoip_path]):
        print("[!] Пропуск сборки refilter-optimized: не все исходные .dat файлы найдены.")
        return

    # Скачивание вспомогательных баз блокировок в src/.
    # Файл перескачивается если он отсутствует ИЛИ старше MAX_CACHE_AGE_DAYS суток.
    def ensure_download(url, path):
        needs_download = not os.path.exists(path)
        if not needs_download:
            age_days = (time.time() - os.path.getmtime(path)) / 86400
            if age_days > MAX_CACHE_AGE_DAYS:
                print(f"[+] {os.path.basename(path)} устарел ({age_days:.1f} д.), обновление...")
                needs_download = True
        if needs_download:
            print(f"[+] Скачивание {url}...")
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                print(f"[-] Ошибка при скачивании {url}: {e}")

    ensure_download("https://raw.githubusercontent.com/hagezi/dns-blocklists/main/domains/tif.txt", hagezi_path)
    ensure_download("https://big.oisd.nl/domainswild2", oisd_path)
    ensure_download("https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt", adguard_path)
    ensure_download("https://tranco-list.eu/download/64WGX/100000", tranco_csv_path)

    # 1. Загрузка вредоносных баз
    bad_domains = set()
    bad_domains.update(parse_plain_domains(hagezi_path))
    bad_domains.update(parse_plain_domains(oisd_path))
    bad_domains.update(parse_adguard(adguard_path))

    # 2. Загрузка баз geosite
    refilter_geosite = load_geosite_proto(refilter_geosite_path)
    runet_geosite = load_geosite_proto(runet_geosite_path)

    # 3. Извлечение правил category-ru
    cat_ru_rules = runet_geosite.get("CATEGORY-RU", [])
    exact_rules = set()
    suffix_rules = set()
    for dtype, val in cat_ru_rules:
        val_lower = val.lower().strip()
        if dtype == 3:
            exact_rules.add(val_lower)
        elif dtype == 2:
            exact_rules.add(val_lower)
            suffix_rules.add(val_lower.lstrip('.'))

    def matches_cat_ru(domain):
        if domain in exact_rules:
            return True
        parts = domain.split('.')
        for i in range(len(parts)):
            suf = ".".join(parts[i:])
            if suf in suffix_rules:
                return True
        return False

    def matches_bad_domains(domain):
        if domain in bad_domains:
            return True
        parts = domain.split('.')
        for i in range(len(parts)):
            suf = ".".join(parts[i:])
            if suf in bad_domains:
                return True
        return False

    # 4. Извлечение остальных списков исключений
    def extract_domains_set(rules_list):
        s = set()
        for dtype, val in rules_list:
            s.add(val.lower().lstrip('.'))
        return s

    private_domains = extract_domains_set(runet_geosite.get("PRIVATE", []))
    inside_domains = extract_domains_set(runet_geosite.get("RU-AVAILABLE-ONLY-INSIDE", []))
    whitelist_domains = parse_plain_domains(whitelist_path)

    # 5. Сжатие доменов Re-filter
    refilter_raw_domains = refilter_geosite.get("REFILTER", [])
    
    # Шаг 1: пересечение с category-ru
    step1_domains = []
    for dtype, val in refilter_raw_domains:
        val_clean = val.lower().lstrip('.')
        if matches_cat_ru(val_clean):
            step1_domains.append(val_clean)
    step1_domains = sorted(list(set(step1_domains)))

    # Шаги 2-5: вычитание bad, private, inside, whitelist
    filtered_domains = []
    for d in step1_domains:
        if matches_bad_domains(d):
            continue
        
        is_private = False
        parts = d.split('.')
        for i in range(len(parts)):
            if ".".join(parts[i:]) in private_domains:
                is_private = True
                break
        if is_private:
            continue
            
        is_inside = False
        for i in range(len(parts)):
            if ".".join(parts[i:]) in inside_domains:
                is_inside = True
                break
        if is_inside:
            continue

        is_whitelist = False
        for i in range(len(parts)):
            if ".".join(parts[i:]) in whitelist_domains:
                is_whitelist = True
                break
        if is_whitelist:
            continue

        filtered_domains.append(d)

    # Шаг 6: Фильтрация по Tranco Top 1M
    tranco_ranks = {}
    if os.path.exists(tranco_csv_path):
        with open(tranco_csv_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                parts = line_str.split(',')
                if len(parts) == 2:
                    try:
                        rank = int(parts[0])
                        domain = parts[1].lower().strip()
                        if rank <= 1000000:
                            tranco_ranks[domain] = rank
                    except ValueError:
                        continue

    def get_tranco_rank(domain):
        candidates = [domain]
        if domain.startswith("www."):
            candidates.append(domain[4:])
        else:
            candidates.append(f"www.{domain}")
            
        best_rank = float('inf')
        for cand in candidates:
            if cand in tranco_ranks:
                best_rank = min(best_rank, tranco_ranks[cand])
        
        return best_rank if best_rank != float('inf') else None

    # Отбираем домены, которые есть в Tranco, и сохраняем их ранг
    matched_domains = []
    for d in filtered_domains:
        rank = get_tranco_rank(d)
        if rank is not None:
            matched_domains.append((d, rank))

    # Сортируем по популярности (от меньшего ранга к большему) и берём топ TOP_REFILTER_DOMAINS.
    matched_domains_sorted = sorted(matched_domains, key=lambda x: x[1])
    top_domains = [d for d, rank in matched_domains_sorted[:TOP_REFILTER_DOMAINS]]

    # Запись доменного optimized файла в dist с алфавитной сортировкой
    write_domain_outputs("refilter-optimized-domains", exact_domains=top_domains, sort_exact=True)

    # 6. Фильтрация IP-адресов Re-filter
    refilter_geoip = load_geoip_proto_as_ranges(refilter_geoip_path)
    runet_geoip = load_geoip_proto_as_ranges(runet_geoip_path)

    refilter_raw_ips = refilter_geoip.get("REFILTER", [])
    ru_ips = runet_geoip.get("RU", [])
    private_ips = runet_geoip.get("PRIVATE", [])
    whitelist_ips = runet_geoip.get("RU-WHITELIST", [])

    ru_v4, ru_v6 = group_ranges(ru_ips)
    private_v4, private_v6 = group_ranges(private_ips)
    whitelist_v4, whitelist_v6 = group_ranges(whitelist_ips)

    final_ips = []
    for r in refilter_raw_ips:
        # Шаг 1: пересечение с RU IP
        if not range_overlaps_any(r, ru_v4, ru_v6):
            continue
        # Шаг 2: вычитание private
        if range_overlaps_any(r, private_v4, private_v6):
            continue
        # Шаг 3: вычитание whitelist
        if range_overlaps_any(r, whitelist_v4, whitelist_v6):
            continue
        final_ips.append(r)

    # Перевод в CIDR формат и запись в dist.
    # format_range_to_cidrs() возвращает список (один диапазон может давать несколько CIDR),
    # поэтому используем extend вместо append.
    final_ips_cidr = []
    for r in final_ips:
        final_ips_cidr.extend(format_range_to_cidrs(r))
    write_ipcidr_outputs("refilter-optimized-ips", final_ips_cidr)


def build_custom_rulesets():
    """
    Обрабатывает декларативный список CUSTOM_DOMAIN_RULESETS.

    Для каждой записи:
      1. Загружает source JSON из src/runetfreedom/.
      2. Загружает все exclude JSON и собирает множества доменов для вычитания.
      3. Фильтрует домены источника, убирая те что есть в исключениях.
      4. Записывает результат через write_domain_outputs().

    Чтобы добавить новую категорию — добавь запись в CUSTOM_DOMAIN_RULESETS вверху файла.
    """
    if not CUSTOM_DOMAIN_RULESETS:
        return

    print("[+] Сборка кастомных категорий из CUSTOM_DOMAIN_RULESETS...")

    for ruleset in CUSTOM_DOMAIN_RULESETS:
        output  = ruleset["output"]
        source  = ruleset["source"]
        exclude = ruleset.get("exclude", [])

        source_path = os.path.join(SRC_DIR, "runetfreedom", f"{source}.json")
        if not os.path.exists(source_path):
            print(f"[!] Предупреждение: {source}.json не найден, пропуск {output}.")
            continue

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                src_data = json.load(f)
        except Exception as e:
            print(f"[-] Ошибка чтения {source_path}: {e}")
            continue

        # Сбор доменов для вычитания из всех exclude-файлов
        exclude_exact  = set()
        exclude_suffix = set()
        for ex_name in exclude:
            ex_path = os.path.join(SRC_DIR, "runetfreedom", f"{ex_name}.json")
            if not os.path.exists(ex_path):
                print(f"[!] Предупреждение: файл исключения {ex_name}.json не найден, пропуск.")
                continue
            try:
                with open(ex_path, "r", encoding="utf-8") as f:
                    ex_data = json.load(f)
            except Exception as e:
                print(f"[-] Ошибка чтения {ex_path}: {e}")
                continue
            for r in ex_data.get("rules", []):
                for d in r.get("domain", []):
                    exclude_exact.add(d.lower())
                for d in r.get("domain_suffix", []):
                    exclude_suffix.add(d.lstrip(".").lower())

        # Фильтрация: вычитаем exclude-домены из источника
        exact_out  = []
        suffix_out = []
        for r in src_data.get("rules", []):
            for d in r.get("domain", []):
                if d.lower() not in exclude_exact:
                    exact_out.append(d)
            for d in r.get("domain_suffix", []):
                cleaned = d.lstrip(".")
                if cleaned.lower() not in exclude_suffix:
                    suffix_out.append(cleaned)

        if not exact_out and not suffix_out:
            print(f"[!] Предупреждение: после фильтрации {output} пуст.")
            continue

        write_domain_outputs(output, exact_domains=exact_out, suffix_domains=suffix_out)

def main():
    print("[+] Начало генерации файлов в dist/...")
    build_own_whitelist()
    build_runetfreedom_categories()
    build_custom_rulesets()
    build_refilter_optimized()
    build_runetfreedom_ip_categories()
    print("[+] Генерация файлов успешно завершена!")

if __name__ == "__main__":
    main()
