import argparse
import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from src.citymove.cli import create_parser, main, parse_time, format_time, DEFAULT_FEED, DEFAULT_PENALTY, CONFIG
from src.citymove.infra import timed, log_call, memoize

MINI_FEED = str(Path(__file__).parent / "fixtures" / "mini_gtfs")


def run_cli(*argv: str) -> tuple[int, str, str]:
    """запускає main() і повертає (код виходу, stdout, stderr)"""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()

class TestCityMoveCLI(unittest.TestCase):
    """модульні тести для перевірки CLI"""

    def setUp(self) -> None:
        """створюємо об'єкт парсера перед кожним тестом"""
        self.parser = create_parser()

    def test_route_arguments_parsing(self) -> None:
        """1. Перевірка правильного розбору аргументів для команди route"""
        args = self.parser.parse_args(["route", "--from", "Політехніка", "--to", "Центр", "--time", "09:00"])
        self.assertEqual(args.command, "route")
        self.assertEqual(args.from_stop, "Політехніка")
        self.assertEqual(args.to_stop, "Центр")
        self.assertEqual(args.time, 540.0)

    def test_stats_arguments_parsing(self) -> None:
        """2. Перевірка розбору аргументів для команди stats"""
        args = self.parser.parse_args(["stats", "--feed", "data/gtfs.zip"])
        self.assertEqual(args.command, "stats")
        self.assertEqual(args.feed, "data/gtfs.zip")

    def test_route_missing_required_argument_error(self) -> None:
        """3. Перевірка помилки, якщо не передано обов'язковий аргумент --to"""
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            # argparse має завершити програму через відсутність обов'язкового прапорця
            self.parser.parse_args(["route", "--from", "Політехніка", "--time", "09:00"])

    def test_route_time_is_parsed_to_minutes(self) -> None:
        """--time перетворюється на хвилини, --feed і --penalty мають значення за замовчуванням"""
        args = self.parser.parse_args(["route", "--from", "A", "--to", "B", "--time", "09:00"])
        self.assertEqual(args.time, 540.0)
        self.assertEqual(args.feed, "data/gtfs_static")
        self.assertEqual(args.penalty, 5.0)

    def test_defaults_come_from_config(self) -> None:
        """значення за замовчуванням --feed і --penalty беруться з config.json"""
        self.assertEqual(DEFAULT_FEED, CONFIG["default_feed_path"])
        self.assertEqual(DEFAULT_PENALTY, float(CONFIG["transfer_penalty_min"]))
        self.assertTrue(Path(DEFAULT_FEED).is_absolute() or (Path(__file__).parent.parent / DEFAULT_FEED).exists())

    def test_draw_arguments_parsing(self) -> None:
        """Перевірка розбору аргументів для команди draw"""
        args = self.parser.parse_args(["draw", "--out", "map.png"])
        self.assertEqual(args.command, "draw")
        self.assertEqual(args.out, "map.png")

    def test_route_invalid_time_format(self) -> None:
        """Невірний формат часу відхиляється ще на етапі розбору аргументів"""
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.parser.parse_args(["route", "--from", "A", "--to", "B", "--time", "invalid_time"])


class TestTimeHelpers(unittest.TestCase):

    def test_parse_time_valid(self) -> None:
        self.assertEqual(parse_time("07:55"), 475.0)
        self.assertEqual(parse_time("25:10"), 1510.0)

    def test_parse_time_invalid(self) -> None:
        """межові та некоректні значення часу"""
        for bad in ("9", "aa:bb", "09:60", "-1:00"):
            with self.subTest(bad=bad), self.assertRaises(argparse.ArgumentTypeError):
                parse_time(bad)

    def test_format_time(self) -> None:
        self.assertEqual(format_time(520), "08:40")
        self.assertEqual(format_time(1510), "25:10")


class TestCliEndToEnd(unittest.TestCase):
    """наскрізні тести команд на мініатюрному фіді tests/fixtures/mini_gtfs"""

    def test_route_with_transfer(self) -> None:
        """Вокзал -> Парк о 07:55: автобус до Площі, пересадка на трамвай, прибуття 08:40"""
        code, out, _ = run_cli("route", "--feed", MINI_FEED, "--from", "Вокзал", "--to", "D", "--time", "07:55")
        self.assertEqual(code, 0)
        self.assertIn("Автобус №1: Вокзал (08:00) -> Площа (08:20)", out)
        self.assertIn("Трамвай №2: Площа (08:30) -> Парк (08:40)", out)
        self.assertIn("Прибуття:        08:40", out)
        self.assertIn("Пересадок:       1", out)

    def test_route_unknown_stop_returns_error(self) -> None:
        code, _, err = run_cli("route", "--feed", MINI_FEED, "--from", "A", "--to", "Неіснуюча", "--time", "08:00")
        self.assertEqual(code, 1)
        self.assertIn("Неіснуюча", err)

    def test_route_unreachable_returns_error(self) -> None:
        """після останнього рейсу шляху немає"""
        code, _, err = run_cli("route", "--feed", MINI_FEED, "--from", "A", "--to", "D", "--time", "23:00")
        self.assertEqual(code, 1)
        self.assertIn("Помилка", err)

    def test_route_bad_time_exits(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["route", "--feed", MINI_FEED, "--from", "A", "--to", "D", "--time", "8 ранку"])

    def test_stats(self) -> None:
        code, out, _ = run_cli("stats", "--feed", MINI_FEED)
        self.assertEqual(code, 0)
        self.assertIn("Усього зупинок:   4", out)
        self.assertIn("Усього рейсів:    3", out)
        self.assertIn("Europe/Kyiv", out)

    def test_stats_missing_feed(self) -> None:
        code, _, err = run_cli("stats", "--feed", "немає_такої_папки")
        self.assertEqual(code, 1)
        self.assertIn("stops.txt", err)

    def test_draw_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "map.png")
            code, _, _ = run_cli("draw", "--feed", MINI_FEED, "--out", out_path)
            self.assertEqual(code, 0)
            self.assertGreater(os.path.getsize(out_path), 0)




class TestInfraDecorators(unittest.TestCase):

    def test_timed_decorator_success(self):
        """Перевіряємо, чи успішно виконується функція з декоратором @timed."""
        @timed
        def sample_func(x, y):
            return x + y

        result = sample_func(2, 3)
        self.assertEqual(result, 5)

    def test_timed_decorator_raises_exception(self):
        """Перевіряємо, чи `@timed` коректно прокидує помилку далі, якщо функція падає."""
        @timed
        def failing_func():
            raise ValueError("Test error")

        with self.assertRaises(ValueError):
            failing_func()

    def test_log_call_decorator_success(self):
        """Перевіряємо, чи `@log_call` не ламає логіку та повертає правильний результат."""
        @log_call
        def multiply(a, b):
            return a * b

        result = multiply(4, 5)
        self.assertEqual(result, 20)

    def test_log_call_decorator_raises_exception(self):
        """Перевіряємо, чи `@log_call` коректно логує та прокидує винятки."""
        @log_call
        def bad_func():
            raise ZeroDivisionError("Division by zero")

        with self.assertRaises(ZeroDivisionError):
            bad_func()

    def test_memoize_decorator(self):
        """Перевіряємо, чи `@memoize` дійсно кешує результат і не викликає функцію вдруге."""
        call_count = 0

        @memoize
        def expensive_computation(x):
            nonlocal call_count
            call_count += 1
            return x * x

        # Перший виклик (функція має виконатися)
        self.assertEqual(expensive_computation(4), 16)
        self.assertEqual(call_count, 1)

        # Другий виклик з тими ж аргументами (має повернути з кешу)
        self.assertEqual(expensive_computation(4), 16)
        self.assertEqual(call_count, 1)

        # Після cache_clear функція виконується знову
        expensive_computation.cache_clear()
        expensive_computation(4)
        self.assertEqual(call_count, 2)


if __name__ == "__main__":
    unittest.main()