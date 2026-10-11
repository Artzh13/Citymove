import unittest
from src.citymove.domain import Stop, Bus, Route, Trip, Passenger

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

if __name__ == '__main__':
    unittest.main()