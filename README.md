# mihomo-rulesets

Автоматическая ежедневная сборка оптимизированных бинарных правил маршрутизации (`.mrs` в формате Mihomo Ruleset) и YAML-правил для клиента **mihomo (Clash Meta)**.

## Источники данных

1. **whitelist.txt** — российские мобильные домены (мобильный интернет) из репозитория [hxehex/russia-mobile-internet-whitelist](https://github.com/hxehex/russia-mobile-internet-whitelist).
2. **geosite.dat** — категории `private`, `category-ru`, `ru-available-only-inside` из репозитория [runetfreedom/russia-blocked-geosite](https://github.com/runetfreedom/russia-blocked-geosite).
3. **geoip.dat** — категории `ru`, `ru-whitelist`, `private` из репозитория [runetfreedom/russia-blocked-geoip](https://github.com/runetfreedom/russia-blocked-geoip).

---

## Список файлов в `dist/`

| Имя файла | Тип правил (behavior) | Формат | Описание |
|---|---|---|---|
| `ru-whitelist-domains.mrs` / `.yaml` | `domain` | MRS (бинарный) / YAML | Белый список доменов российских мобильных операторов |
| `runetfreedom-private.mrs` / `.yaml` | `domain` | MRS (бинарный) / YAML | Локальные и приватные домены (бывший geosite-private) |
| `runetfreedom-category-ru.mrs` / `.yaml` | `domain` | MRS (бинарный) / YAML | Широкий список доменов RU-сегмента |
| `runetfreedom-ru-available-only-inside.mrs` / `.yaml` | `domain` | MRS (бинарный) / YAML | Домены, доступные только изнутри РФ |
| `runetfreedom-ip-ru.mrs` / `.yaml` | `ipcidr` | MRS (бинарный) / YAML | Диапазоны IP-адресов РФ |
| `runetfreedom-ip-ru-whitelist.mrs` / `.yaml` | `ipcidr` | MRS (бинарный) / YAML | Доверенные IP-диапазоны РФ |
| `runetfreedom-ip-private.mrs` / `.yaml` | `ipcidr` | MRS (бинарный) / YAML | Приватные диапазоны IP |
| `runetfreedom-category-ru-extra.yaml` | `classical` | YAML | Ключевые слова (keyword) и регулярные выражения (regex) |

---

## Использование в mihomo (Clash Meta)

Добавьте следующие блоки в ваш конфигурационный файл (замените `<repo>` на название вашего репозитория, если вы сделали форк, или используйте напрямую `Debik5/mihomo-rulesets`):

```yaml
rule-providers:
  ru-whitelist-domains:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/ru-whitelist-domains.mrs"
    interval: 86400

  runetfreedom-private:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-private.mrs"
    interval: 86400

  runetfreedom-category-ru:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-category-ru.mrs"
    interval: 86400

  runetfreedom-ru-available-only-inside:
    type: http
    behavior: domain
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-ru-available-only-inside.mrs"
    interval: 86400

  runetfreedom-ip-ru:
    type: http
    behavior: ipcidr
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-ip-ru.mrs"
    interval: 86400

  runetfreedom-ip-ru-whitelist:
    type: http
    behavior: ipcidr
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-ip-ru-whitelist.mrs"
    interval: 86400

  runetfreedom-ip-private:
    type: http
    behavior: ipcidr
    format: mrs
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-ip-private.mrs"
    interval: 86400

  # Подключать только если файл появился в dist/ (содержит keyword/regex)
  runetfreedom-category-ru-extra:
    type: http
    behavior: classical
    format: yaml
    url: "https://raw.githubusercontent.com/Debik5/mihomo-rulesets/main/dist/runetfreedom-category-ru-extra.yaml"
    interval: 86400

rules:
  - RULE-SET,ru-whitelist-domains,DIRECT
  - RULE-SET,runetfreedom-private,DIRECT
  - RULE-SET,runetfreedom-category-ru,DIRECT
  - RULE-SET,runetfreedom-ru-available-only-inside,DIRECT
  - RULE-SET,runetfreedom-ip-ru,DIRECT
  - RULE-SET,runetfreedom-ip-ru-whitelist,DIRECT
  - RULE-SET,runetfreedom-ip-private,DIRECT
```

---

## Настройка автоматического обновления

Для коммита результатов работы скрипта обратно в репозиторий, GitHub Actions требуются права на запись.

Перейдите в **Settings -> Actions -> General -> Workflow permissions** и выберите **Read and write permissions**, после чего сохраните настройки.
