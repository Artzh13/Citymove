"""
Автоматичний прогін усіх тестів CityMove (працює на Windows, macOS і Linux).

    python run_tests.py          # усі тести з папки tests/
    python run_tests.py -v       # з детальним виводом
    python run_tests.py --e2e    # + наскрізний сценарій scripts/e2e_demo.py

Код завершення 0 означає «зелений стан» проєкту.
"""
import argparse
import logging
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Прогін тестів CityMove")
    parser.add_argument("-v", "--verbose", action="store_true", help="детальний вивід unittest")
    parser.add_argument("--e2e", action="store_true", help="також запустити наскрізний сценарій")
    args = parser.parse_args()

    # тести навмисно викликають помилки - не засмічуємо вивід логами
    logging.disable(logging.CRITICAL)
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))  # щоб працювали імпорти виду `from src.citymove...`
    sys.path.insert(1, str(ROOT / "src"))  # і виду `from citymove...`

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    ok = result.wasSuccessful()

    if args.e2e:
        ok = subprocess.run([sys.executable, str(ROOT / "scripts" / "e2e_demo.py")]).returncode == 0 and ok

    print("\nЗЕЛЕНИЙ СТАН" if ok else "\nЄ ПОМИЛКИ")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
