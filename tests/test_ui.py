import tkinter as tk
import unittest

from src.citymove.domain import Bus, Network, Route, Stop, Tram
from src.citymove.ui import MainWindow, NetworkCanvas


class TestNetworkCanvas(unittest.TestCase):
    """Тести для інтерактивного полотна NetworkCanvas та графічного вікна MainWindow."""

    def setUp(self) -> None:
        """Створює приховане кореневе вікно Tkinter перед кожним тестом."""
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError:
            self.skipTest("Tkinter недоступний у даному середовищі")

        self.net = Network()
        self.net.stops = {
            "s1": Stop("s1", "Центральна", 50.4500, 30.5000),
            "s2": Stop("s2", "Вокзальна", 50.4600, 30.5200),
            "s3": Stop("s3", "Університет", 50.4700, 30.5400),
        }
        self.net.routes = {
            "r1": Route("r1", "10", Bus(), ["s1", "s2", "s3"]),
            "r2": Route("r2", "3", Tram(), ["s2", "s3"]),
        }

    def tearDown(self) -> None:
        """Знищує вікно Tkinter після завершення тесту."""
        if hasattr(self, "root") and self.root:
            self.root.destroy()

    def test_canvas_draw_network_stops_and_routes(self) -> None:
        """Перевірка успішного відмальовування зупинок, ліній маршрутів та підписів."""
        canvas = NetworkCanvas(self.root, network=self.net, width=600, height=400)

        stops = canvas.find_withtag("stop")
        routes = canvas.find_withtag("route")
        labels = canvas.find_withtag("stop_label")

        self.assertEqual(len(stops), 3)
        self.assertEqual(len(routes), 2)
        self.assertEqual(len(labels), 3)

    def test_canvas_init_empty_network(self) -> None:
        """Межовий випадок: ініціалізація полотна з порожньою мережею."""
        empty_net = Network()
        canvas = NetworkCanvas(self.root, network=empty_net, width=500, height=400)

        stops = canvas.find_withtag("stop")
        routes = canvas.find_withtag("route")
        empty_msgs = canvas.find_withtag("empty_msg")

        self.assertEqual(len(stops), 0)
        self.assertEqual(len(routes), 0)
        self.assertEqual(len(empty_msgs), 1)

    def test_canvas_single_stop_network(self) -> None:
        """Межовий випадок: мережа, що містить лише одну зупинку."""
        single_net = Network()
        single_net.stops["s1"] = Stop("s1", "Єдина", 50.0, 30.0)
        canvas = NetworkCanvas(self.root, network=single_net, width=400, height=300)

        stops = canvas.find_withtag("stop")
        self.assertEqual(len(stops), 1)
        x, y = canvas.geo_to_canvas(30.0, 50.0)
        self.assertAlmostEqual(x, 200.0, delta=50.0)
        self.assertAlmostEqual(y, 150.0, delta=50.0)

    def test_zoom_scaling_and_invalid_factor(self) -> None:
        """Тест масштабування полотна та реакції на некоректний коефіцієнт (помилкові дані)."""
        canvas = NetworkCanvas(self.root, network=self.net, width=600, height=400)
        initial_scale = canvas.scale

        # Збільшення масштабу
        canvas.zoom_in()
        self.assertGreater(canvas.scale, initial_scale)

        # Зменшення масштабу
        canvas.zoom_out()
        self.assertAlmostEqual(canvas.scale, initial_scale, places=5)

        # Помилкові дані: недодатний коефіцієнт масштабування
        with self.assertRaises(ValueError):
            canvas.zoom(0.0)

        with self.assertRaises(ValueError):
            canvas.zoom(-1.5)

    def test_pan_offsets(self) -> None:
        """Тест панорамування: зсув координат при перетягуванні полотна."""
        canvas = NetworkCanvas(self.root, network=self.net, width=600, height=400)
        x0, y0 = canvas.geo_to_canvas(30.5000, 50.4500)

        canvas.pan(25.0, -15.0)
        self.assertEqual(canvas.offset_x, 25.0)
        self.assertEqual(canvas.offset_y, -15.0)

        x1, y1 = canvas.geo_to_canvas(30.5000, 50.4500)
        self.assertAlmostEqual(x1, x0 + 25.0)
        self.assertAlmostEqual(y1, y0 - 15.0)

    def test_toggle_labels(self) -> None:
        """Тест показу та приховування підписів зупинок."""
        canvas = NetworkCanvas(self.root, network=self.net, width=600, height=400)
        self.assertTrue(canvas.show_labels)

        # Приховуємо підписи
        state = canvas.toggle_labels(False)
        self.assertFalse(state)
        self.assertFalse(canvas.show_labels)
        for label_id in canvas.find_withtag("stop_label"):
            self.assertEqual(canvas.itemcget(label_id, "state"), tk.HIDDEN)

        # Показуємо назад
        state = canvas.toggle_labels(True)
        self.assertTrue(state)
        self.assertTrue(canvas.show_labels)
        for label_id in canvas.find_withtag("stop_label"):
            self.assertEqual(canvas.itemcget(label_id, "state"), tk.NORMAL)

    def test_coordinate_roundtrip(self) -> None:
        """Тест двостороннього перетворення: geo -> canvas -> geo."""
        canvas = NetworkCanvas(self.root, network=self.net, width=800, height=600)
        orig_lon, orig_lat = 30.5123, 50.4567

        x, y = canvas.geo_to_canvas(orig_lon, orig_lat)
        recovered_lon, recovered_lat = canvas.canvas_to_geo(x, y)

        self.assertAlmostEqual(recovered_lon, orig_lon, places=5)
        self.assertAlmostEqual(recovered_lat, orig_lat, places=5)

    def test_transport_filter(self) -> None:
        """Тест фільтрації маршрутів за видами транспорту."""
        canvas = NetworkCanvas(self.root, network=self.net, width=600, height=400)
        self.assertEqual(len(canvas.find_withtag("route")), 2)

        # Залишаємо лише трамваї
        canvas.set_transport_filter({"Трамвай"})
        self.assertEqual(len(canvas.find_withtag("route")), 1)

        # Вимикаємо всі
        canvas.set_transport_filter(set())
        self.assertEqual(len(canvas.find_withtag("route")), 0)

    def test_stop_selection(self) -> None:
        """Тест вибору зупинки та оновлення стану полотна."""
        canvas = NetworkCanvas(self.root, network=self.net, width=600, height=400)
        canvas.selected_stop_id = "s1"
        canvas.draw_network()
        self.assertEqual(canvas.selected_stop_id, "s1")

    def test_main_window_creation(self) -> None:
        """Тест коректного створення головного вікна MainWindow з елементами керування."""
        app = MainWindow(network=self.net)
        app.withdraw()
        try:
            self.assertIsNotNone(app.canvas)
            self.assertEqual(len(app.canvas.find_withtag("stop")), 3)
            self.assertIn("Зупинок: 3", app.status.cget("text"))
        finally:
            app.destroy()


if __name__ == "__main__":
    unittest.main()

