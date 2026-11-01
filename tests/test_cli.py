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

    def test_draw_arguments_parsing(self) -> None:
        """4. Перевірка розбору аргументів для команди draw"""
        args = self.parser.parse_args(["draw", "--out", "map.png"])
        self.assertEqual(args.command, "draw")
        self.assertEqual(args.out, "map.png")

    def test_route_invalid_time_format(self) -> None:
        """5. Перевірка відпрацювання помилки формату часу (не перериває виконання в CLI, але генерує повідомлення)"""
        args = self.parser.parse_args(["route", "--from", "A", "--to", "B", "--time", "invalid_time"])
        self.assertEqual(args.time, "invalid_time")
        # Помилка обробляється всередині handle_route




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
        res1 = expensive_computation(4)
        self.assertEqual(res1, 16)
        self.assertEqual(call_count, 1)

        # Другий виклик з тими ж аргументами (має повернути з кешу)
        res2 = expensive_computation(4)
        self.assertEqual(res2, 16)
        self.assertEqual(call_count, 1)
            


if __name__ == "__main__":
    unittest.main()