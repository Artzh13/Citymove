import unittest
from citymove.cli import create_parser
import logging
import time
from citymove.infra import timed, log_call, logger

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
        self.assertEqual(args.time, "09:00")

    def test_stats_arguments_parsing(self) -> None:
        """2. Перевірка розбору аргументів для команди stats"""
        args = self.parser.parse_args(["stats", "--feed", "data/gtfs.zip"])
        self.assertEqual(args.command, "stats")
        self.assertEqual(args.feed, "data/gtfs.zip")

    def test_route_missing_required_argument_error(self) -> None:
        """3. Перевірка помилки, якщо не передано обов'язковий аргумент --to"""
        with self.assertRaises(SystemExit):
            # argparse має завершити програму через відсутність обов'язкового прапорця
            self.parser.parse_args(["route", "--from", "Політехніка", "--time", "09:00"])




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


if __name__ == "__main__":
    unittest.main()