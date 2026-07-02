#!/usr/bin/env python3
import sys
import os
import json
import yaml

# Определение директорий
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

DIST_DIR = os.path.join(REPO_ROOT, "dist")
SRC_DIR = os.path.join(REPO_ROOT, "src")

os.makedirs(DIST_DIR, exist_ok=True)

def write_domain_outputs(name, exact_domains=None, suffix_domains=None):
    exact = sorted(list(set(exact_domains or [])))
    suffix = sorted(list(set(suffix_domains or [])))

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

    # Запись .txt (для mihomo convert-ruleset, все без префиксов)
    txt_path = os.path.join(DIST_DIR, f"{name}.txt")
    all_domains = sorted(list(set(exact + suffix)))
    with open(txt_path, "w", encoding="utf-8") as f:
        for d in all_domains:
            f.write(f"{d}\n")

    print(f"[+] Записаны {name}.yaml и {name}.txt (точных: {len(exact)}, суффиксов: {len(suffix)})")

def write_ipcidr_outputs(name, cidrs):
    sorted_cidrs = sorted(list(set(cidrs or [])))

    if not sorted_cidrs:
        print(f"[!] Предупреждение: Нет IP/CIDR для {name}, файлы не будут созданы.")
        return

    # Запись .yaml
    yaml_path = os.path.join(DIST_DIR, f"{name}.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"payload": sorted_cidrs}, f, default_flow_style=False, allow_unicode=True)

    # Запись .txt
    txt_path = os.path.join(DIST_DIR, f"{name}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for cidr in sorted_cidrs:
            f.write(f"{cidr}\n")

    print(f"[+] Записаны {name}.yaml и {name}.txt (IP диапазонов: {len(sorted_cidrs)})")

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
            # все домены из whitelist.txt трактуем как suffix-match
            domains.append(line)

    write_domain_outputs("ru-whitelist-domains", suffix_domains=domains)

def build_runetfreedom_categories():
    rf_dir = os.path.join(SRC_DIR, "runetfreedom")
    if not os.path.exists(rf_dir):
        print(f"[!] Предупреждение: Директория {rf_dir} не найдена. Пропуск geosite категорий.")
        return

    for filename in os.listdir(rf_dir):
        if filename.endswith(".json"):
            category = filename[:-5]
            json_path = os.path.join(rf_dir, filename)
            
            with open(json_path, "r", encoding="utf-8") as f:
                try:
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

            # Вывод доменных правил
            write_domain_outputs(
                f"runetfreedom-{category}",
                exact_domains=exact_domains,
                suffix_domains=suffix_stripped
            )

            # Вывод классических правил (keyword / regex), если они есть
            if keyword_domains or regex_domains:
                write_classical_yaml(
                    f"runetfreedom-{category}",
                    keyword_domains=keyword_domains,
                    regex_domains=regex_domains
                )

            # Вывод IP-правил, если вдруг они прокрались в geosite
            if ip_cidr:
                write_ipcidr_outputs(f"runetfreedom-{category}-ip", ip_cidr)

def build_runetfreedom_ip_categories():
    rf_ip_dir = os.path.join(SRC_DIR, "runetfreedom-ip")
    if not os.path.exists(rf_ip_dir):
        print(f"[!] Предупреждение: Директория {rf_ip_dir} не найдена. Пропуск geoip категорий.")
        return

    for filename in os.listdir(rf_ip_dir):
        if filename.endswith(".json"):
            category = filename[:-5]
            json_path = os.path.join(rf_ip_dir, filename)

            with open(json_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    print(f"[-] Ошибка при чтении {json_path}: {e}")
                    continue

            ip_cidr = data.get("ip_cidr", [])
            write_ipcidr_outputs(f"runetfreedom-ip-{category}", ip_cidr)

def main():
    print("[+] Начало генерации файлов в dist/...")
    build_own_whitelist()
    build_runetfreedom_categories()
    build_runetfreedom_ip_categories()
    print("[+] Генерация файлов успешно завершена!")

if __name__ == "__main__":
    main()
