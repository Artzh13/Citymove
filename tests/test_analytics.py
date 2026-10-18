import unittest
from src.citymove.domain import Stop, StopNotFoundError, Trip, Route, Bus, Metro
from src.citymove.analytics import stop_info_table, departure_board_table

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

    


if __name__ == '__main__':
    unittest.main()