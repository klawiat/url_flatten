#!/usr/bin/env python3
"""
Скрипт разворачивает include-ссылки в репозитории v2fly/domain-list-community
в плоские списки доменов, удаляет атрибуты v2ray (@ads, @cn и т.д.),
комментарии и пустые строки.
"""

import os
import sys
import re
from pathlib import Path

# Путь к клону v2fly/domain-list-community
SOURCE_DIR = Path("v2fly-domain-list-community/data")
OUTPUT_DIR = Path("output")


def clean_line(line: str) -> str:
    """Очищает строку от атрибутов v2ray (@) и конвертирует regexp в wildcard."""
    # Удаляем атрибуты v2ray (@ads, @cn и т.д.)
    if "@" in line:
        line = line.split("@")[0]
    line = line.strip()

    if not line:
        return ""

    # Если это регулярное выражение
    if line.startswith("regexp:"):
        pattern = line[len("regexp:"):].strip()
        
        # Убираем символы начала/конца строки ^ и $
        pattern = pattern.lstrip("^").rstrip("$")
        
        # Экранированные точки \. заменяем на обычные .
        pattern = pattern.replace(r"\.", ".")
        
        # Преобразуем регулярные спецсимволы .* или .*? в единичный wildcard *
        pattern = re.sub(r"\.\*[\?]*", "*", pattern)
        
        # Удаляем лишние повторяющиеся звёздочки (например, ** -> *)
        pattern = re.sub(r"\*+", "*", pattern)
        
        # Очищаем оставшиеся слэши и спецсимволы регулярных выражений, если есть
        pattern = pattern.replace("\\", "")

        # Заворачиваем в AdGuard-формат wildcard rules
        # Если паттерн начинается с точки или звёздочки (например, .example.com)
        if pattern.startswith(".") or pattern.startswith("*"):
            pattern = pattern.lstrip(".*")
            return f"||{pattern}"
        
        return f"||*{pattern}*"

    # Обработка стандартных префиксов v2ray (full:, keyword:, domain:)
    if line.startswith("full:"):
        return line[len("full:"):].strip()
    if line.startswith("domain:"):
        return line[len("domain:"):].strip()
    if line.startswith("keyword:"):
        kw = line[len("keyword:"):].strip()
        return f"||*{kw}*"

    return line


def parse_file(filepath: Path, visited: set = None) -> list:
    """
    Рекурсивно читает файл, разворачивает include: ссылки.
    Возвращает список чистых доменов без атрибутов, комментариев и пустых строк.
    """
    if visited is None:
        visited = set()

    abs_path = filepath.resolve()
    if abs_path in visited:
        # Защита от циклических include
        return []
    visited.add(abs_path)

    if not filepath.exists():
        print(f"[WARN] Файл не найден: {filepath}", file=sys.stderr)
        return []

    result = []
    with open(filepath, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            # Пропускаем пустые строки и комментарии
            if not line or line.startswith("#"):
                continue

            if line.startswith("include:"):
                # Обработка include: Name @attr
                include_target = line[len("include:"):].strip()
                # Удаляем атрибуты из самой команды include, если они есть
                include_name = clean_line(include_target)
                
                include_path = SOURCE_DIR / include_name
                included_lines = parse_file(include_path, visited.copy())
                result.extend(included_lines)
            else:
                # Очищаем домен от атрибутов (@ads, @cn и т.д.)
                cleaned = clean_line(line)
                if cleaned:
                    result.append(cleaned)

    return result


def dedup_preserve_order(lines: list) -> list:
    """Удаляет дубликаты, сохраняя порядок первого появления."""
    seen = set()
    out = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def main():
    if not SOURCE_DIR.exists():
        print(f"[ERROR] Директория не найдена: {SOURCE_DIR}", file=sys.stderr)
        print("Убедитесь, что репозиторий v2fly/domain-list-community клонирован в поддиректорию.", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Обрабатываем все файлы из data/
    for entry in sorted(SOURCE_DIR.iterdir()):
        if not entry.is_file():
            continue

        flat_lines = parse_file(entry)
        flat_lines = dedup_preserve_order(flat_lines)

        out_path = OUTPUT_DIR / entry.name
        with open(out_path, "w", encoding="utf-8") as f:
            if flat_lines:
                f.write("\n".join(flat_lines) + "\n")

        print(f"[OK] {entry.name} -> {len(flat_lines)} строк")

    print(f"\nГотово. Результаты в: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()