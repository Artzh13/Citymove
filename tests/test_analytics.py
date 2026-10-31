import unittest
import matplotlib
matplotlib.use("Agg")  # без вікон, щоб тести працювали в консолі
from src.citymove.domain import Stop, StopNotFoundError, Trip, Route, Bus, Metro, Network
from src.citymove.analytics import (stop_info_table, departure_board_table, route_headways, busiest_stops,
                                    plot_headway_histogram, plot_busiest_stops, PRIMARY_COLOR)

class TestAnalytics(unittest.TestCase):

    def test_empty_routes(self):
            """Тест перевірки наявності маршрутів"""
            sample_stop = Stop(
                  stop_id = "111_S_111",
                  name = "Університет",
                  lat = 45.909,
                  lon = 44.333
            )
            sample_routes_list = [] 
    
            board_text = stop_info_table(sample_stop, sample_routes_list)
    
            self.assertIn("Маршрутів немає", board_text)

    def test_stop_info_success(self):
        """Тест успішного створення таблиці інформації про зупинку"""
        sample_stop = Stop(
            stop_id = "111_S_111",
            name = "Університет",
            lat = 45.909,
            lon = 44.333
        )
        sample_routes_list = ["3A", "48", "53"] 
        board_text = stop_info_table(sample_stop, sample_routes_list)

        self.assertIn("Назва:", board_text)
        self.assertIn("ID:", board_text)
        self.assertIn("Координати:", board_text)
        self.assertIn("Маршрути:", board_text)
                      


    def test_departure_board_success(self):
            """Тест успішного створення табло відправлень для існуючої зупинки"""
            bus_unit = Bus()
            sample_route = Route(
                route_id="r_3a_1",
                short_name="3А",
                transport=bus_unit,
                stops=["S10", "S20", "пл. Ринок"]
            )
            sample_trips = [
                Trip(trip_id="T1", route=sample_route, start_time=495, service_id="weekday", stop_times=[])
            ]
            
            board_text = departure_board_table("S10", sample_trips)
            self.assertIn("ТАБЛО ВІДПРАВЛЕНЬ", board_text)
            self.assertIn("3А", board_text)
            self.assertIn("08:15:00", board_text)

    def test_departure_board_stop_not_found_exception(self):
            """Тест викидання винятку StopNotFoundError, якщо зупинки немає в жодному маршруті"""
            bus_unit = Bus()
            sample_route = Route(
                route_id="r_3a_1",
                short_name="3А",
                transport=bus_unit,
                stops=["S10", "S20"]
            )
            sample_trips = [
                Trip(trip_id="T1", route=sample_route, start_time=495, service_id="weekday", stop_times=[])
            ]
            
            with self.assertRaises(StopNotFoundError):
                departure_board_table("Неіснуюча Зупинка", sample_trips)

    def test_metro_unit_props(self):
            """Тест характеристик класу Metro та спадкування від TransportUnit"""
            metro = Metro()
            self.assertEqual(metro.speed, 40.0)
            self.assertEqual(metro.capacity, 1000)
            self.assertEqual(metro.fare, 20.0)
            self.assertEqual(metro.name(), "Метро")

    


class TestCharts(unittest.TestCase):

    def test_route_headways(self):
        """Інтервали лише для вибраних service_id, нічна перерва (> max_gap) відкидається"""
        route = Route(route_id="r1", short_name="3А", transport=Bus(), stops=["S1"])
        trips = [Trip(f"T{start}{service}", route, start, service, [("S1", start, start)])
                 for start, service in [(480, "wd"), (490, "wd"), (505, "wd"), (480, "we"), (900, "wd")]]
        self.assertEqual(sorted(route_headways(trips, service_ids={"wd"})), [10, 15])

    def test_busiest_stops(self):
        """Платформи з однаковою назвою сумуються, результат відсортований за спаданням"""
        network = Network()
        network.stops = {"A1": Stop("A1", "Вокзал", 50.4, 30.5), "A2": Stop("A2", "Вокзал", 50.4, 30.5),
                         "B": Stop("B", "Парк", 50.5, 30.6)}
        network.edges = {"A1": [("B", 480, 5, "T1")], "A2": [("B", 490, 5, "T2")], "B": [("A1", 500, 5, "T3")] * 3}
        self.assertEqual(busiest_stops(network), [("Парк", 3), ("Вокзал", 2)])

    def test_charts_common_style(self):
        """Обидва графіки в єдиному стилі: колір стовпців PRIMARY_COLOR і заголовок зліва"""
        for fig in [plot_headway_histogram([10, 15, 20]), plot_busiest_stops([("Парк", 3)])]:
            ax = fig.axes[0]
            self.assertEqual(matplotlib.colors.to_hex(ax.patches[0].get_facecolor()), PRIMARY_COLOR)
            self.assertTrue(ax.get_title(loc="left"))

    def test_charts_empty_data(self):
        """Межові дані: порожні дані для графіків викликають ValueError"""
        with self.assertRaises(ValueError):
            plot_headway_histogram([])
        with self.assertRaises(ValueError):
            plot_busiest_stops([])


if __name__ == '__main__':
    unittest.main()