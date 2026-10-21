import unittest
from src.citymove.domain import (
    Stop,
    Bus,
    Route,
    Trip,
    Passenger,
    Network, 
    StopNotFoundError, 
    DisconnectedNetworkError
)

class TestDomain(unittest.TestCase):

    def test_bus_props(self):
        bus = Bus()
        self.assertEqual(bus.speed, 20.0)
        self.assertEqual(bus.name(), "Автобус")
        
        with self.assertRaises(AttributeError):
            bus.fare = 10.0

    def test_stop_validation(self):
        stop = Stop("s1", "Центр", 49.8, 24.0)
        self.assertEqual(stop.name, "Центр")

        with self.assertRaises(ValueError):
            Stop("s2", "Помилка", 95.0, 24.0)

        with self.assertRaises(ValueError):
            Stop("s3", "Помилка", 49.8, -200.0)

        with self.assertRaises(ValueError):
            Stop("s4", "   ", 49.8, 24.0)

    def test_trip_creation(self):
        bus = Bus()
        route = Route("r1", "114", bus, ["s1", "s2"])
        
        stop_times = [("s1", 480, 480), ("s2", 490, 495)]
        trip = Trip("t1", route, 480, "weekday", stop_times)
        
        self.assertEqual(trip.route.short_name, "114")
        self.assertEqual(len(trip.stop_times), 2)

        with self.assertRaises(ValueError):
            Trip("t2", route, -5, "weekday", stop_times)
        
    def test_network_add_and_remove_node(self):
        """Тест додавання вузлів та перевірки дублікатів у Network."""
        net = Network()
        stop1 = Stop("s1", "Головна", 49.8, 24.0)
        stop2 = Stop("s2", "Ринок", 49.85, 24.02)

        net.add_node(stop1)
        net.add_node(stop2)

        self.assertIn("s1", net.stops)
        self.assertIn("s2", net.stops)

        # Перевірка помилки при додаванні дубліката
        with self.assertRaises(ValueError):
            net.add_node(Stop("s1", "Дублікат", 49.0, 24.0))

    def test_network_stop_not_found(self):
        """Тест викидання винятку StopNotFoundError при видаленні неіснуючої зупинки."""
        net = Network()
        with self.assertRaises(StopNotFoundError):
            net.remove_node("non_existent_id")

    def test_network_disconnected_error(self):
        """Тест викидання DisconnectedNetworkError, якщо видалення вузла розриває зв'язність."""
        net = Network()
        s1 = Stop("s1", "А", 49.0, 24.0)
        s2 = Stop("s2", "Б", 49.1, 24.1)
        s3 = Stop("s3", "В", 49.2, 24.2)

        net.add_node(s1)
        net.add_node(s2)
        net.add_node(s3)

        # Формуємо ланцюжок ребер s1 -> s2 -> s3
        net.edges["s1"] = [("s2", 10, 15, "t1")]
        net.edges["s2"] = [("s3", 20, 25, "t1")]

        # Спроба видалити проміжну зупинку 's2', яка є єдиним містком між s1 та s3
        with self.assertRaises(DisconnectedNetworkError):
            net.remove_node("s2")

if __name__ == '__main__':
    unittest.main()