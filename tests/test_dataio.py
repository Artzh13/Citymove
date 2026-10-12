import os
import tempfile
import unittest

from src.citymove.dataio import time_to_minutes, fix_midnight, load_network
from src.citymove.domain import ScheduleError, Tram

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


if __name__ == '__main__':
    unittest.main()
