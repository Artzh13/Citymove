import io
import unittest
from unittest.mock import patch
import matplotlib
matplotlib.use("Agg")  # без вікон, щоб тести працювали в консолі

from src.citymove.domain import Stop, StopNotFoundError, Trip, Route, Bus, Metro, Network
from src.citymove.analytics import (
    stop_info_table,
    print_stop_info,
    departure_board_table,
    print_departures_board,
    print_depatrures_board,
    route_intervals_table,
    route_summary_table,
    print_route_summary,
    print_route_intervals,
    route_headways,
    busiest_stops,
    plot_headway_histogram,
    plot_busiest_stops,
    new_axes,
    add_legend,
    console_report_table,
    generate_console_report,
    PRIMARY_COLOR,
    SERIES_COLORS,
)


class TestAnalytics(unittest.TestCase):

    def test_empty_routes(self):
        """Тест перевірки виведення інформації про зупинку без маршрутів"""
        sample_stop = Stop(
            stop_id="111_S_111",
            name="Університет",
            lat=45.909,
            lon=44.333,
        )
        sample_routes_list = []
        board_text = stop_info_table(sample_stop, sample_routes_list)
        self.assertIn("Маршрутів немає", board_text)

    def test_stop_info_success(self):
        """Тест успішного створення таблиці інформації про зупинку"""
        sample_stop = Stop(
            stop_id="111_S_111",
            name="Університет",
            lat=45.909,
            lon=44.333,
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
            stops=["S10", "S20", "пл. Ринок"],
        )
        sample_trips = [
            Trip(trip_id="T1", route=sample_route, start_time=495, service_id="weekday", stop_times=[])
        ]

        board_text = departure_board_table("S10", sample_trips)
        self.assertIn("ТАБЛО ВІДПРАВЛЕНЬ", board_text)
        self.assertIn("3А", board_text)
        self.assertIn("08:15:00", board_text)

    def test_departure_board_stop_not_found_exception(self):
        """Тест викидання винятку StopNotFoundError із збереженням stop_id"""
        bus_unit = Bus()
        sample_route = Route(
            route_id="r_3a_1",
            short_name="3А",
            transport=bus_unit,
            stops=["S10", "S20"],
        )
        sample_trips = [
            Trip(trip_id="T1", route=sample_route, start_time=495, service_id="weekday", stop_times=[])
        ]

        with self.assertRaises(StopNotFoundError) as ctx:
            departure_board_table("Неіснуюча Зупинка", sample_trips)
        self.assertEqual(ctx.exception.stop_id, "Неіснуюча Зупинка")

    def test_metro_unit_props(self):
        """Тест характеристик класу Metro та спадкування від TransportUnit"""
        metro = Metro()
        self.assertEqual(metro.speed, 40.0)
        self.assertEqual(metro.capacity, 1000)
        self.assertEqual(metro.fare, 20.0)
        self.assertEqual(metro.name(), "Метро")

    def test_route_intervals_table_success(self):
        """Тест генерації таблиці інтервалів руху для маршруту"""
        bus_unit = Bus()
        sample_route = Route(route_id="r1", short_name="1", transport=bus_unit, stops=["S1"])
        trips = [
            Trip(trip_id="T1", route=sample_route, start_time=600, service_id="w", stop_times=[]),
            Trip(trip_id="T2", route=sample_route, start_time=615, service_id="w", stop_times=[]),
            Trip(trip_id="T3", route=sample_route, start_time=645, service_id="w", stop_times=[]),
        ]
        table = route_intervals_table("r1", trips)
        self.assertIn("ІНТЕРВАЛИ РУХУ", table)
        self.assertIn("15", table)  # Мін
        self.assertIn("30", table)  # Макс

    def test_route_intervals_table_insufficient_trips(self):
        """Межовий випадок: менше ніж 2 рейси для розрахунку інтервалів"""
        bus_unit = Bus()
        sample_route = Route(route_id="r1", short_name="1", transport=bus_unit, stops=["S1"])
        trips_single = [
            Trip(trip_id="T1", route=sample_route, start_time=600, service_id="w", stop_times=[])
        ]
        table_single = route_intervals_table("r1", trips_single)
        self.assertIn("Недостатньо рейсів", table_single)

        table_empty = route_intervals_table("r1", [])
        self.assertIn("Недостатньо рейсів", table_empty)

    def test_console_report_table_and_generate(self):
        """Тест створення підсумкового консольного звіту для демонстрації 1"""
        net = Network()
        net.stops = {
            "s1": Stop("s1", "Центр", 50.45, 30.52),
            "s2": Stop("s2", "Вокзал", 50.44, 30.48),
        }
        route = Route("r1", "1", Bus(), ["s1", "s2"])
        net.routes = {"r1": route}
        net.trips = {"t1": Trip("t1", route, 480, "w", [("s1", 480, 480), ("s2", 500, 500)])}

        report = console_report_table(net)
        self.assertIn("ПІДСУМКОВИЙ ЗВІТ", report)
        self.assertIn("Кількість зупинок:  2", report)
        self.assertIn("Кількість маршрутів: 1", report)
        self.assertIn("Кількість рейсів:   1", report)
        self.assertIn("Автобус", report)

        # Перевірка виклику generate_console_report та виведення в stdout
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            ret = generate_console_report(net)
            self.assertEqual(ret, report)
            self.assertIn("ПІДСУМКОВИЙ ЗВІТ", fake_out.getvalue())

    def test_console_report_empty_network(self):
        """Межовий випадок: звіт по порожній мережі"""
        net = Network()
        report = console_report_table(net)
        self.assertIn("Кількість зупинок:  0", report)
        self.assertIn("(Немає даних)", report)

    def test_print_helpers(self):
        """Тест допоміжних функцій виведення в консоль та аліаса print_depatrures_board"""
        sample_stop = Stop("s1", "Тест", 50.0, 30.0)
        route = Route("r1", "10", Bus(), ["s1"])
        trip = Trip("t1", route, 600, "w", [("s1", 600, 600)])

        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            print_stop_info(sample_stop, ["10"])
            print_departures_board("s1", [trip])
            print_depatrures_board("s1", [trip])  # перевірка аліаса
            print_route_intervals("r1", [trip])
            output = fake_out.getvalue()

        self.assertIn("ІНФОРМАЦІЯ ПРО ЗУПИНКУ", output)
        self.assertIn("ТАБЛО ВІДПРАВЛЕНЬ", output)
        self.assertIn("ІНТЕРВАЛИ РУХУ", output)



    def test_route_summary_table_and_print(self):
        """Тест генерації аналітичної картки маршруту та виведення в консоль"""
        bus = Bus()
        route = Route("r_10", "10", bus, ["s1", "s2", "s3"])
        trips = [
            Trip("t1", route, 480, "w", [("s1", 480, 480), ("s2", 490, 490), ("s3", 500, 500)]),
            Trip("t2", route, 510, "w", [("s1", 510, 510), ("s2", 520, 520), ("s3", 530, 530)]),
        ]
        card = route_summary_table(route, trips)
        self.assertIn("КАРТКА МАРШРУТУ 10", card)
        self.assertIn("Кількість зупинок:        3", card)
        self.assertIn("Кількість рейсів:         2", card)
        self.assertIn("08:00", card)
        self.assertIn("08:30", card)
        self.assertIn("30.0 хв", card)

        # Тест маршруту без рейсів
        empty_card = route_summary_table(route, [])
        self.assertIn("(немає даних про рейси)", empty_card)

        # Тест виклику print_route_summary
        with patch("sys.stdout", new=io.StringIO()) as fake_out:
            print_route_summary(route, trips)
            self.assertIn("КАРТКА МАРШРУТУ 10", fake_out.getvalue())


class TestCharts(unittest.TestCase):

    def test_route_headways(self):
        """Інтервали лише для вибраних service_id, нічна перерва (> max_gap) відкидається"""
        route = Route(route_id="r1", short_name="3А", transport=Bus(), stops=["S1"])
        trips = [
            Trip(f"T{start}{service}", route, start, service, [("S1", start, start)])
            for start, service in [(480, "wd"), (490, "wd"), (505, "wd"), (480, "we"), (900, "wd")]
        ]
        self.assertEqual(sorted(route_headways(trips, service_ids={"wd"})), [10, 15])

    def test_route_headways_all_services(self):
        """Інтервали для всіх рейсів, коли service_ids=None"""
        route = Route(route_id="r1", short_name="3А", transport=Bus(), stops=["S1"])
        trips = [
            Trip(f"T{start}", route, start, "w", [("S1", start, start)])
            for start in [480, 490, 505]
        ]
        self.assertEqual(route_headways(trips, service_ids=None), [10, 15])

    def test_busiest_stops(self):
        """Платформи з однаковою назвою сумуються, результат відсортований за спаданням"""
        network = Network()
        network.stops = {
            "A1": Stop("A1", "Вокзал", 50.4, 30.5),
            "A2": Stop("A2", "Вокзал", 50.4, 30.5),
            "B": Stop("B", "Парк", 50.5, 30.6),
        }
        network.edges = {
            "A1": [("B", 480, 5, "T1")],
            "A2": [("B", 490, 5, "T2")],
            "B": [("A1", 500, 5, "T3")] * 3,
        }
        self.assertEqual(busiest_stops(network), [("Парк", 3), ("Вокзал", 2)])

    def test_busiest_stops_top_limit(self):
        """Параметр top обмежує кількість повернутих зупинок"""
        network = Network()
        network.stops = {
            "s1": Stop("s1", "З1", 50.0, 30.0),
            "s2": Stop("s2", "З2", 50.1, 30.1),
            "s3": Stop("s3", "З3", 50.2, 30.2),
        }
        network.edges = {
            "s1": [("s2", 1, 1, "t1")],
            "s2": [("s3", 1, 1, "t1")],
            "s3": [],
        }
        self.assertEqual(len(busiest_stops(network, top=1)), 1)

    def test_busiest_stops_ignores_quotes(self):
        """Одна зупинка, записана з лапками й без, рахується як одна"""
        network = Network()
        network.stops = {
            "L1": Stop("L1", 'ст.м. "Лісова"', 50.4, 30.6),
            "L2": Stop("L2", "ст.м. Лісова", 50.4, 30.6),
        }
        network.edges = {
            "L1": [("L2", 480, 1, "T1")] * 2,
            "L2": [("L1", 490, 1, "T2")],
        }
        self.assertEqual(busiest_stops(network), [("ст.м. Лісова", 3)])

    def test_add_legend_style(self):
        """Шаблон для команди: серії беруть кольори SERIES_COLORS по порядку, легенда без рамки"""
        fig, ax = new_axes("Тест", "x", "y")
        first, = ax.plot([1, 2], [1, 2], label="a")
        second, = ax.plot([1, 2], [2, 1], label="b")
        self.assertEqual([first.get_color(), second.get_color()], SERIES_COLORS[:2])
        self.assertFalse(add_legend(ax).get_frame_on())

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


if __name__ == "__main__":
    unittest.main()
