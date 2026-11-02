import unittest
from src.citymove.domain import (
    Stop,
    Bus,
    Route,
    Trip,
    Passenger,
    Network, 
    StopNotFoundError, 
    DisconnectedNetworkError,
    ScheduleError,
    Tram
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



    def setUp(self):
        self.network = Network()
        self.stop1 = Stop("s1", "Центр", 49.84, 24.03)
        self.stop2 = Stop("s2", "Ринок", 49.84, 24.02)
        self.bus = Bus()

    def test_add_duplicate_node_raises_value_error(self):
        """Захист від дублікатів: додавання зупинки з уже існуючим ID має викликати ValueError"""
        self.network.add_node(self.stop1)
        with self.assertRaises(ValueError):
            self.network.add_node(self.stop1)

    def test_stop_not_found_exception(self):
        """Видалення неіснуючої зупинки кидає StopNotFoundError із збереженням ID"""
        with self.assertRaises(StopNotFoundError) as ctx:
            self.network.remove_node("non_existent_id")
        self.assertEqual(ctx.exception.stop_id, "non_existent_id")

    def test_disconnected_network_protection(self):
        """Зв'язність графа: видалення зупинки, що розриває єдину мережу, викликає DisconnectedNetworkError."""
        self.network.add_node(Stop("s1", "А", 49.0, 24.0))
        self.network.add_node(Stop("s2", "Б", 49.1, 24.1))
        self.network.add_node(Stop("s3", "В", 49.2, 24.2))
        
    
        self.network.edges["s1"] = [("s2", 10, 5, "t1")]
        self.network.edges["s2"] = [("s1", 10, 5, "t1"), ("s3", 10, 5, "t2")]
        self.network.edges["s3"] = [("s2", 10, 5, "t2")]

        # Видалення центральної зупинки s2 залишить s1 та s3 розірваними
        with self.assertRaises(DisconnectedNetworkError):
            self.network.remove_node("s2")

    def test_step_by_step_removal_synchronization(self):
        """Синхронізація даних: видалення зупинки автоматично очищає пов'язані з нею маршрути та рейси"""
        self.network.add_node(self.stop1)
        route = Route("r1", "1", self.bus, ["s1"])
        trip = Trip("t1", route, 540, "WD", [("s1", 540, 541)])
        
        self.network.add_route(route)
        self.network.add_trip(trip)

        # Видалили зупинку
        self.network.remove_node("s1")

        # Перевіряємо поетапне очищення
        self.assertNotIn("r1", self.network.routes)
        self.assertNotIn("t1", self.network.trips)

    def test_transport_unit_properties_read_only(self):
        """Перевірка, що характеристики транспортного засобу не можна змінити напряму після створення."""
        tram = Tram()
        self.assertEqual(tram.capacity, 150)
        # Спроба змінити read-only властивість має викинути AttributeError
        with self.assertRaises(AttributeError):
            tram.capacity = 200
        with self.assertRaises(AttributeError):
            tram.speed = 25.0

    def test_passenger_name_update(self):
        """Перевірка встановлення та оновлення імені пасажира."""
        p = Passenger("p1", "Іван")
        self.assertEqual(p.name, "Іван")
        
        # Перевірка, що пусте ім'я замінюється на "Unknown"
        p.name = "   "
        self.assertEqual(p.name, "Unknown")
        
        p.name = "Олена"
        self.assertEqual(p.name, "Олена")

    def test_route_empty_stops_handling(self):
        """Перевірка поведінки маршруту, якщо він не містить зупинок."""
        bus = Bus()
        route = Route("r_empty", "0", bus, [])
        self.assertEqual(len(route.stops), 0)
        self.assertEqual(str(route), "Маршрут 0 [Автобус]: 0 зупинок")

    def test_network_add_trip_unregistered_route(self):
        """Перевірка додавання рейсу, маршрут якого відсутній у мережі."""
        net = Network()
        bus = Bus()
        route1 = Route("r1", "10", bus, ["s1"])
        
        # Створюємо рейс із маршрутом r1, але сам r1 не додаємо в net
        trip = Trip("t1", route1, 600, "WD", [("s1", 600, 601)])
        
        # Додавання такого рейсу має викликати ScheduleError
        with self.assertRaises(ScheduleError) as ctx:
            net.add_trip(trip)
        self.assertIn("не знайдено", str(ctx.exception))

    def test_network_remove_node_cascade_trips_multiple(self):
        """Перевірка, що видалення зупинки каскадно видаляє ВСІ пов'язані рейси та маршрути."""
        net = Network()
        stop_shared = Stop("s_shared", "Вузол", 49.0, 24.0)
        net.add_node(stop_shared)
        
        bus = Bus()
        # Два різні маршрути, що проходять через одну зупинку
        r1 = Route("r1", "1", bus, ["s_shared"])
        r2 = Route("r2", "2", bus, ["s_shared"])
        net.add_route(r1)
        net.add_route(r2)
        
        t1 = Trip("t1", r1, 100, "WD", [("s_shared", 100, 101)])
        t2 = Trip("t2", r2, 200, "WE", [("s_shared", 200, 201)])
        net.add_trip(t1)
        net.add_trip(t2)
        
        # Видаляємо спільну зупинку
        net.remove_node("s_shared")
        
        # Обидва маршрути та обидва рейси мають бути видалені
        self.assertEqual(len(net.routes), 0)
        self.assertEqual(len(net.trips), 0)

if __name__ == '__main__':
    unittest.main()