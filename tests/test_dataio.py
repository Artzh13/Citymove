import os
import tempfile
import unittest

from src.citymove.dataio import (
    fix_midnight, get_timezone, load_agency_timezone, load_network,
    time_to_minutes, validate_feed,
)
from src.citymove.domain import (
    RouteNotFoundError, ScheduleError, StopNotFoundError, Tram,
)

FEED = {
    'stops.txt': "stop_id,stop_name,stop_lat,stop_lon\n"
                 "A,Зупинка А,50.40,30.50\n"
                 "B,Зупинка Б,50.41,30.51\n",
    'routes.txt': "route_id,route_short_name,route_type\n"
                  "r1,5,0\n",
    'trips.txt': "route_id,service_id,trip_id\n"
                 "r1,weekday,t1\n"
                 "r_unknown,weekday,t2\n",
    'stop_times.txt': "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                      "t1,08:10:00,08:10:00,B,2\n"
                      "t1,08:00:00,08:00:00,A,1\n"
                      "t2,09:00:00,09:00:00,A,1\n",
}


class TestDataio(unittest.TestCase):

    def test_time_to_minutes(self):
        """Звичайний час і час після опівночі (межовий випадок GTFS)."""
        self.assertEqual(time_to_minutes("08:30:00"), 510)
        self.assertEqual(time_to_minutes("25:10:00"), 1510)

    def test_time_to_minutes_invalid(self):
        """Некоректний формат часу має кидати ScheduleError."""
        for bad in ("8:30", "aa:bb:cc", ""):
            with self.assertRaises(ScheduleError):
                time_to_minutes(bad)

    def test_fix_midnight(self):
        """Час, що «стрибає назад» після опівночі, отримує +1440 хв."""
        schedule = [("A", 1430, 1430), ("B", 5, 5)]
        self.assertEqual(fix_midnight(schedule), [("A", 1430, 1430), ("B", 1445, 1445)])

    def test_load_network(self):
        """Повне завантаження: сутності зіставлені за ключами, рейс без маршруту пропущено."""
        with tempfile.TemporaryDirectory() as folder:
            for name, content in FEED.items():
                with open(os.path.join(folder, name), 'w', encoding='utf-8') as file:
                    file.write(content)
            network = load_network(folder)

        route = network.routes['r1']
        self.assertEqual(route.stops, ["A", "B"])
        self.assertIsInstance(route.transport, Tram)

        trip = network.trips['t1']
        self.assertIs(trip.route, route)
        self.assertEqual(trip.start_time, 480)
        self.assertNotIn('t2', network.trips)

        self.assertEqual(network.edges['A'], [("B", 480, 10, "t1")])
        self.assertEqual(network.timezone, "UTC")

    def test_load_agency_timezone_valid(self):
        """Коректне завантаження та парсинг часової зони з agency.txt."""
        with tempfile.TemporaryDirectory() as folder:
            agency_file = os.path.join(folder, 'agency.txt')
            with open(agency_file, 'w', encoding='utf-8') as f:
                f.write("agency_name,agency_url,agency_timezone\n"
                        "KyivPastrans,https://kpt.kyiv.ua,Europe/Kyiv\n")

            tz = load_agency_timezone(agency_file)
            self.assertEqual(tz, "Europe/Kyiv")
            tz_obj = get_timezone(tz)
            self.assertEqual(tz_obj.key, "Europe/Kyiv")

    def test_load_agency_timezone_invalid(self):
        """Помилкові та межові дані: невідома часова зона або відсутнє поле."""
        with tempfile.TemporaryDirectory() as folder:
            agency_file = os.path.join(folder, 'agency.txt')
            # Невідома часова зона
            with open(agency_file, 'w', encoding='utf-8') as f:
                f.write("agency_name,agency_url,agency_timezone\n"
                        "KyivPastrans,https://kpt.kyiv.ua,Unknown/Timezone_123\n")

            with self.assertRaises(ScheduleError):
                load_agency_timezone(agency_file)

            # Порожнє поле
            with open(agency_file, 'w', encoding='utf-8') as f:
                f.write("agency_name,agency_url,agency_timezone\n"
                        "KyivPastrans,https://kpt.kyiv.ua,\n")

            with self.assertRaises(ScheduleError):
                load_agency_timezone(agency_file)

    def test_validate_feed_valid_with_agency(self):
        """Валідація коректного фіда: повертає FeedValidationReport без помилок."""
        feed = dict(FEED)
        feed['agency.txt'] = ("agency_name,agency_url,agency_timezone\n"
                              "KyivPastrans,https://kpt.kyiv.ua,Europe/Kyiv\n")
        with tempfile.TemporaryDirectory() as folder:
            for name, content in feed.items():
                with open(os.path.join(folder, name), 'w', encoding='utf-8') as f:
                    f.write(content)

            report = validate_feed(folder)
            
            self.assertFalse(report.is_valid)
            self.assertTrue(any("r_unknown" in err for err in report.errors))
            
            clean_feed = dict(FEED)
            clean_feed['trips.txt'] = "route_id,service_id,trip_id\nr1,weekday,t1\n"
            clean_feed['stop_times.txt'] = (
                "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                "t1,08:00:00,08:00:00,A,1\n"
                "t1,08:10:00,08:10:00,B,2\n"
            )
            clean_feed['agency.txt'] = feed['agency.txt']

            with tempfile.TemporaryDirectory() as clean_folder:
                for name, content in clean_feed.items():
                    with open(os.path.join(clean_folder, name), 'w', encoding='utf-8') as f:
                        f.write(content)
                clean_report = validate_feed(clean_folder)
                self.assertTrue(clean_report.is_valid)
                self.assertEqual(len(clean_report.errors), 0)

    def test_validate_feed_missing_column_and_integrity(self):
        """Тест на помилкові дані: відсутня обов'язкова колонка та порушення цілісності."""
        bad_feed = {
            'stops.txt': "stop_id,stop_name\nA,Зупинка А\n", 
            'routes.txt': "route_id,route_short_name,route_type\nr1,5,0\n",
            'trips.txt': "route_id,service_id,trip_id\nr1,weekday,t1\n",
            'stop_times.txt': "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                              "t1,08:00:00,08:00:00,GHOST_STOP,1\n",
        }
        with tempfile.TemporaryDirectory() as folder:
            for name, content in bad_feed.items():
                with open(os.path.join(folder, name), 'w', encoding='utf-8') as f:
                    f.write(content)

            report = validate_feed(folder)
            self.assertFalse(report.is_valid)
            self.assertTrue(any("stop_lat" in err for err in report.errors))

            with self.assertRaises(ScheduleError):
                validate_feed(folder, strict=True)

    def test_load_network_with_agency_timezone(self):
        """load_network зчитує agency.txt і встановлює timezone для Network."""
        feed = dict(FEED)
        feed['agency.txt'] = ("agency_name,agency_url,agency_timezone\n"
                              "KPT,https://kpt.ua,Europe/Kyiv\n")
        with tempfile.TemporaryDirectory() as folder:
            for name, content in feed.items():
                with open(os.path.join(folder, name), 'w', encoding='utf-8') as f:
                    f.write(content)

            network = load_network(folder)
            self.assertEqual(network.timezone, "Europe/Kyiv")
            
    def test_validate_feed_missing_files(self):
        """Перевірка реакції валідатора на повністю порожню папку або відсутність файлів."""
        with tempfile.TemporaryDirectory() as folder:
            report = validate_feed(folder)
            self.assertFalse(report.is_valid)
            #перевіряємо, що у звіті є помилки про відсутність обов'язкових файлів
            self.assertTrue(any("відсутній" in err for err in report.errors))
            
            #в strict-режимі має кидати помилку ScheduleError
            with self.assertRaises(ScheduleError):
                validate_feed(folder, strict=True)


if __name__ == '__main__':
    unittest.main()
