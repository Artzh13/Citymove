"""
Наскрізний консольний сценарій CityMove (Демонстрація 1).

Послідовно запускає CLI як окремий процес: stats -> route -> draw -> route з помилкою,
і перевіряє коди завершення. Запуск із кореня репозиторію:

    python scripts/e2e_demo.py                      # мініатюрний фід tests/fixtures/mini_gtfs
    python scripts/e2e_demo.py --feed data/gtfs_static \\
        --from "ст. Старовокзальна" --to "Мих Борщагівка" --time 06:00
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_step(title: str, cli_args: list[str], expected_code: int) -> bool:
    """запускає `python -m src.citymove.cli <cli_args>` і порівнює код завершення з очікуваним"""
    print(f"\n>>> {title}")
    print(f"$ citymove {' '.join(cli_args)}", flush=True)
    # stderr перехоплюємо: там лог із infra.py, у сценарії показуємо лише повідомлення про помилку
    result = subprocess.run([sys.executable, "-m", "src.citymove.cli", *cli_args], cwd=ROOT,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8")
    ok = result.returncode == expected_code
    for line in result.stderr.splitlines():
        if not ok or line.startswith("Помилка"):
            print(line)
    print(f"[{'OK' if ok else 'FAIL'}] код завершення {result.returncode} (очікувався {expected_code})", flush=True)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Наскрізний сценарій CityMove")
    parser.add_argument("--feed", default="tests/fixtures/mini_gtfs")
    parser.add_argument("--from", dest="from_stop", default="Вокзал")
    parser.add_argument("--to", dest="to_stop", default="Парк")
    parser.add_argument("--time", default="07:55")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        map_path = str(Path(tmp) / "map.png")
        results = [
            run_step("1. Статистика фіда", ["stats", "--feed", args.feed], 0),
            run_step("2. Пошук маршруту", ["route", "--feed", args.feed, "--from", args.from_stop,
                                           "--to", args.to_stop, "--time", args.time], 0),
            run_step("3. Карта мережі", ["draw", "--feed", args.feed, "--out", map_path], 0),
            run_step("4. Обробка помилки: невідома зупинка", ["route", "--feed", args.feed, "--from",
                                                              "Неіснуюча", "--to", args.to_stop, "--time", args.time], 1),
        ]

    passed = sum(results)
    print(f"\n=== Сценарій завершено: {passed}/{len(results)} кроків успішно ===")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
