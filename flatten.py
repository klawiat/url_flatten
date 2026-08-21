#!/usr/bin/env python3
"""
Скрипт разворачивает include-ссылки в репозитории v2fly/domain-list-community
в плоские списки доменов. Удаляет комментарии и пустые строки.
"""

import os
import sys
from pathlib import Path

# Путь к клону v2fly/domain-list-community
SOURCE_DIR = Path("v2fly-domain-list-community/data")
OUTPUT_DIR = Path("output")


def parse_file(filepath: Path, visited: set = None) -> list:
    """
    Рекурсивно читает файл, разворачивает include: ссылки.
    Возвращает список строк без комментариев и пустых строк.
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
                include_name = line[len("include:"):].strip()
                include_path = SOURCE_DIR / include_name
                included_lines = parse_file(include_path, visited.copy())
                result.extend(included_lines)
            else:
                result.append(line)

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
            # Если список пустой — файл останется пустым

        print(f"[OK] {entry.name} -> {len(flat_lines)} строк")

    print(f"\nГотово. Результаты в: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
