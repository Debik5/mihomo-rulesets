# mihomo-rulesets

Автоматическая ежедневная сборка оптимизированных бинарных правил маршрутизации в форматах **MRS** (для mihomo / Clash Meta), **SRS** (для sing-box), а также в формате **YAML**-payload.

Сборка осуществляется с помощью утилиты [ULG (Universal Lists Generator)](https://github.com/Debik5/ULG).

## Источники данных

1. **whitelist.txt** — российские мобильные домены (мобильный интернет) из репозитория [russia-mobile-internet-whitelist](https://github.com/hxehex/russia-mobile-internet-whitelist).
2. **geosite.dat** — категории `private`, `category-ru`, `ru-available-only-inside`, `category-games-!cn`, `supercell` из репозитория [russia-blocked-geosite](https://github.com/runetfreedom/russia-blocked-geosite).
3. **geoip.dat** — категории `ru`, `ru-whitelist`, `private` из репозитория [russia-blocked-geoip](https://github.com/runetfreedom/russia-blocked-geoip).
4. **Re-filter** — базы доменов и IP из проекта [Re-filter-lists](https://github.com/1andrevich/Re-filter-lists).
5. **Tranco** — топ-100 000 популярных доменов для оптимизации списков обхода из [Tranco List](https://tranco-list.eu/).
6. **HaGeZi TIF** — список вредоносных доменов из репозитория [dns-blocklists](https://github.com/hagezi/dns-blocklists) (используется для фильтрации).
7. **OISD** — список рекламы и трекеров [OISD Big](https://oisd.nl/) (используется для фильтрации).
8. **AdGuard DNS Filter** — список блокировки рекламы [AdGuard SDNS Filter](https://github.com/AdguardTeam/AdguardSDNSFilter) (используется для фильтрации).


---

## Список файлов в `dist/`

Для каждого набора правил генерируются три формата: `.mrs` (mihomo), `.srs` (sing-box) и `.yaml` (YAML-payload).

| Имя файла | Тип правил (behavior) | Форматы | Описание |
|---|---|---|---|
| `ru-whitelist-domains` | `domain` | MRS / SRS / YAML | Белый список доменов российских мобильных операторов |
| `runetfreedom-ru-domains` | `domain` | MRS / SRS / YAML | Широкий список доменов RU-сегмента (бывший category-ru) |
| `runetfreedom-private-domains` | `domain` | MRS / SRS / YAML | Локальные и приватные домены (бывший geosite-private) |
| `runetfreedom-ru-available-only-inside` | `domain` | MRS / SRS / YAML | Домены, доступные только изнутри РФ |
| `runetfreedom-category-games` | `domain` | MRS / SRS / YAML | Игровые домены (за вычетом Supercell) |
| `refilter-optimized-domains` | `domain` | MRS / SRS / YAML | Оптимизированный Топ-100 доменов Re-filter для обхода блокировок |
| `refilter-optimized-ips` | `ipcidr` | MRS / SRS / YAML | Оптимизированные IP-диапазоны Re-filter |
| `runetfreedom-ru-ips` | `ipcidr` | MRS / SRS / YAML | Диапазоны IP-адресов РФ (бывший ip-ru) |
| `ru-whitelist-ips` | `ipcidr` | MRS / SRS / YAML | Доверенные IP-диапазоны РФ (бывший ip-ru-whitelist) |
| `runetfreedom-private-ips` | `ipcidr` | MRS / SRS / YAML | Приватные диапазоны IP (бывший ip-private) |
| `runetfreedom-private-domains-mrs-extra.yaml` | `classical` | YAML | Ключевые слова и regex для приватных доменов |
| `runetfreedom-category-games-mrs-extra.yaml` | `classical` | YAML | Ключевые слова и regex для игровых доменов |

---

## Использование в mihomo (Clash Meta)

Добавьте следующие блоки в ваш конфигурационный файл (замените `Debik5/mihomo-rulesets` на название вашего репозитория, если вы сделали форк):

```yaml
rule-providers:
  ru-whitelist-domains:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/ru-whitelist-domains.mrs"
    interval: 86400

  runetfreedom-private-domains:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-private-domains.mrs"
    interval: 86400

  runetfreedom-ru-domains:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-ru-domains.mrs"
    interval: 86400

  runetfreedom-ru-available-only-inside:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-ru-available-only-inside.mrs"
    interval: 86400

  runetfreedom-category-games:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-category-games.mrs"
    interval: 86400

  refilter-optimized-domains:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/refilter-optimized-domains.mrs"
    interval: 86400

  refilter-optimized-ips:
    type: http
    behavior: ipcidr
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/refilter-optimized-ips.mrs"
    interval: 86400

  runetfreedom-ru-ips:
    type: http
    behavior: ipcidr
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-ru-ips.mrs"
    interval: 86400

  ru-whitelist-ips:
    type: http
    behavior: ipcidr
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/ru-whitelist-ips.mrs"
    interval: 86400

  runetfreedom-private-ips:
    type: http
    behavior: ipcidr
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-private-ips.mrs"
    interval: 86400

rules:
  - RULE-SET,ru-whitelist-domains,DIRECT
  - RULE-SET,runetfreedom-private-domains,DIRECT
  - RULE-SET,runetfreedom-ru-domains,DIRECT
  - RULE-SET,runetfreedom-ru-available-only-inside,DIRECT
  - RULE-SET,runetfreedom-category-games,DIRECT
  - RULE-SET,refilter-optimized-domains,DIRECT
  - RULE-SET,refilter-optimized-ips,DIRECT
  - RULE-SET,runetfreedom-ru-ips,DIRECT
  - RULE-SET,ru-whitelist-ips,DIRECT
  - RULE-SET,runetfreedom-private-ips,DIRECT
```

---

## Использование в sing-box

Поскольку ULG автоматически генерирует бинарный формат `.srs`, вы можете использовать эти правила в клиенте **sing-box**:

```json
{
  "route": {
    "rule_set": [
      {
        "tag": "ru-whitelist-domains",
        "type": "remote",
        "format": "binary",
        "url": "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/ru-whitelist-domains.srs",
        "download_detour": "direct"
      },
      {
        "tag": "runetfreedom-ru-domains",
        "type": "remote",
        "format": "binary",
        "url": "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-ru-domains.srs",
        "download_detour": "direct"
      }
    ],
    "rules": [
      {
        "rule_set": "ru-whitelist-domains",
        "outbound": "direct"
      },
      {
        "rule_set": "runetfreedom-ru-domains",
        "outbound": "direct"
      }
    ]
  }
}
```
