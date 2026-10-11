import unittest
from src.citymove.cli import create_parser


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


if __name__ == "__main__":
    unittest.main()