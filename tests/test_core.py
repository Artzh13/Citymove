import unittest

from src.citymove.core import (
    build_graph,
    shortest_path_from,
    find_journey,
    INF,
    degree_centrality,
    network_diameter,
    average_shortest_path_length,
    calculate_network_metrics,
    TransportRouter,
)
from src.citymove.domain import (
    Stop,
    Bus,
    Route,
    Trip,
    Network,
    StopNotFoundError,
    RouteNotFoundError,
    DisconnectedNetworkError,
)


def make_network(trips: list[tuple[str, list[tuple[str, int, int]]]]) -> Network:
    """Створює синтетичну мережу із зупинками A, B, C, D та заданими рейсами."""
    net = Network()
    for i, stop_id in enumerate("ABCD"):
        net.add_node(Stop(stop_id, f"Зупинка {stop_id}", 50.0 + i / 100, 30.0 + i / 100))

    for trip_id, stop_times in trips:
        route = Route(f"r_{trip_id}", trip_id, Bus(), [s for s, _, _ in stop_times])
        net.routes[route.route_id] = route
        net.trips[trip_id] = Trip(trip_id, route, stop_times[0][2], "weekday", stop_times)
    return net


class TestCore(unittest.TestCase):

    def test_build_graph(self):
        """Ребра у форматі (dep, travel, trip_idx, next_idx), відсортовані за відправленням."""
        net = make_network([
            ("t1", [("A", 620, 620), ("B", 630, 630)]),
            ("t2", [("A", 600, 600), ("B", 605, 606), ("C", 615, 615)]),
        ])
        stop_to_idx, M, graph = build_graph(net)

        self.assertEqual(M, 2)
        self.assertEqual(len(graph), 4)

        a, b, c = stop_to_idx["A"], stop_to_idx["B"], stop_to_idx["C"]
        # Ребра з A відсортовані: спочатку t2 (600), потім t1 (620)
        self.assertEqual(graph[a], [(600.0, 5.0, 1, b), (620.0, 10.0, 0, b)])
        self.assertEqual(graph[b], [(606.0, 9.0, 1, c)])
        self.assertEqual(graph[c], [])

    def test_build_graph_skips_unknown_stops(self):
        """Ребра до зупинок, яких немає в мережі, пропускаються."""
        net = make_network([("t1", [("A", 600, 600), ("X", 610, 610)])])
        _, _, graph = build_graph(net)
        self.assertTrue(all(edges == [] for edges in graph))

    def test_direct_trip(self):
        """Прямий рейс без пересадок: час прибуття на кінцеву зупинку."""
        net = make_network([("t1", [("A", 600, 600), ("B", 610, 611), ("C", 620, 620)])])
        self.assertEqual(shortest_path_from(net, "A", "C", 590.0), 620.0)

    def test_same_trip_no_penalty(self):
        """Проїзд кількох зупинок одним рейсом не отримує штраф за пересадку."""
        net = make_network([("t1", [("A", 600, 600), ("B", 610, 611), ("C", 620, 620)])])
        self.assertEqual(shortest_path_from(net, "A", "C", 590.0, penalty=100), 620.0)

    def test_missed_departure_waits_next(self):
        """Якщо пасажир спізнився на рейс, береться наступний."""
        net = make_network([
            ("t1", [("A", 600, 600), ("B", 610, 610)]),
            ("t2", [("A", 630, 630), ("B", 640, 640)]),
        ])
        self.assertEqual(shortest_path_from(net, "A", "B", 605.0), 640.0)

    def test_transfer_penalty(self):
        """При пересадці між рейсами додається штраф."""
        net = make_network([
            ("t1", [("A", 600, 600), ("B", 610, 610)]),
            ("t2", [("B", 615, 615), ("C", 625, 625)]),
        ])
        self.assertEqual(shortest_path_from(net, "A", "C", 600.0), 625.0)
        self.assertEqual(shortest_path_from(net, "A", "C", 600.0, penalty=5), 630.0)

    def test_penalty_changes_best_route(self):
        """Зі штрафом вигідніше обрати повільніший прямий рейс замість пересадки."""
        net = make_network([
            ("t1", [("A", 600, 600), ("B", 610, 610)]),
            ("t2", [("B", 615, 615), ("C", 625, 625)]),
            ("t3", [("A", 600, 600), ("C", 628, 628)]),
        ])
        self.assertEqual(shortest_path_from(net, "A", "C", 600.0, penalty=0), 625.0)
        self.assertEqual(shortest_path_from(net, "A", "C", 600.0, penalty=5), 628.0)

    def test_stop_not_found(self):
        """Неіснуюча зупинка має кидати StopNotFoundError."""
        net = make_network([("t1", [("A", 600, 600), ("B", 610, 610)])])
        with self.assertRaises(StopNotFoundError):
            shortest_path_from(net, "A", "Z", 600.0)
        with self.assertRaises(StopNotFoundError):
            shortest_path_from(net, "Z", "A", 600.0)

    def test_route_not_found(self):
        """Немає шляху (недосяжна зупинка або всі рейси вже відійшли) — RouteNotFoundError."""
        net = make_network([("t1", [("A", 600, 600), ("B", 610, 610)])])
        with self.assertRaises(RouteNotFoundError):
            shortest_path_from(net, "A", "D", 590.0)
        with self.assertRaises(RouteNotFoundError):
            shortest_path_from(net, "A", "B", 700.0)

    def test_inf_constant(self):
        """INF значно більший за будь-який реальний час у хвилинах."""
        self.assertGreater(INF, 48 * 60)

    def test_penalty_does_not_block_same_trip(self):
        """Після пересадки зі штрафом можна їхати тим самим рейсом далі (регресія)."""
        net = make_network([
            ("t1", [("A", 600, 600), ("B", 610, 610)]),
            ("t2", [("B", 615, 615), ("C", 625, 625), ("D", 635, 635)]),
        ])
        journey = find_journey(net, "A", "D", 600.0, penalty=5)
        self.assertEqual(journey.arrival, 635.0)
        self.assertEqual(journey.cost, 640.0)

    def test_journey_legs_and_transfers(self):
        """Перегони одного рейсу об'єднуються в одну ділянку, пересадки рахуються."""
        net = make_network([
            ("t1", [("A", 600, 600), ("B", 610, 611), ("C", 620, 620)]),
            ("t2", [("C", 622, 622), ("D", 630, 630)]),
        ])
        journey = find_journey(net, "A", "D", 590.0, penalty=3)
        self.assertEqual(journey.transfers, 1)
        self.assertEqual(journey.legs, [
            ("t1", "A", "C", 600.0, 620.0),
            ("t2", "C", "D", 622.0, 630.0),
        ])
        self.assertEqual((journey.arrival, journey.cost), (630.0, 633.0))

    def test_large_penalty_prefers_fewer_transfers(self):
        """Великий штраф змушує обрати маршрут без пересадок, навіть якщо він довший."""
        net = make_network([
            ("t1", [("A", 600, 600), ("B", 605, 605)]),
            ("t2", [("B", 606, 606), ("D", 610, 610)]),
            ("t3", [("A", 600, 600), ("C", 630, 630), ("D", 660, 660)]),
        ])
        self.assertEqual(find_journey(net, "A", "D", 600.0, penalty=0).legs[0][0], "t1")
        journey = find_journey(net, "A", "D", 600.0, penalty=100)
        self.assertEqual(journey.transfers, 0)
        self.assertEqual(journey.legs, [("t3", "A", "D", 600.0, 660.0)])

    def test_same_start_and_end(self):
        """Межовий випадок: початкова й кінцева зупинки збігаються — поїздка не потрібна."""
        net = make_network([("t1", [("A", 600, 600), ("B", 610, 610)])])
        journey = find_journey(net, "A", "A", 590.0, penalty=5)
        self.assertEqual((journey.arrival, journey.cost, journey.transfers), (590.0, 590.0, 0))
        self.assertEqual(journey.legs, [])

    def test_degree_centrality_linear_network(self):
        """Ступенева центральність для лінійної мережі A-B-C-D."""
        net = make_network([("t1", [("A", 600, 600), ("B", 610, 610), ("C", 620, 620), ("D", 630, 630)])])
        centrality = degree_centrality(net, normalized=True)
        # N=4: крайні мають 1 сусіда (1/3), внутрішні - 2 сусідів (2/3)
        self.assertAlmostEqual(centrality["A"], 1 / 3)
        self.assertAlmostEqual(centrality["B"], 2 / 3)
        self.assertAlmostEqual(centrality["C"], 2 / 3)
        self.assertAlmostEqual(centrality["D"], 1 / 3)

        raw_centrality = degree_centrality(net, normalized=False)
        self.assertEqual(raw_centrality["A"], 1.0)
        self.assertEqual(raw_centrality["B"], 2.0)

    def test_degree_centrality_star_network(self):
        """Ступенева центральність для зіркової мережі з центральним хабом B."""
        net = Network()
        for s in "ABCD":
            net.add_node(Stop(s, f"Зупинка {s}", 50.0, 30.0))
        # B з'єднаний з A, C, D
        for target in ["A", "C", "D"]:
            r = Route(f"r_{target}", f"B-{target}", Bus(), ["B", target])
            net.routes[r.route_id] = r
            net.trips[f"t_{target}"] = Trip(f"t_{target}", r, 600, "w", [("B", 600, 600), (target, 610, 610)])

        centrality = degree_centrality(net, normalized=True)
        self.assertAlmostEqual(centrality["B"], 1.0)  # B з'єднаний з усіма іншими 3 вузлами: 3/3 = 1.0
        self.assertAlmostEqual(centrality["A"], 1 / 3)
        self.assertAlmostEqual(centrality["C"], 1 / 3)
        self.assertAlmostEqual(centrality["D"], 1 / 3)

    def test_network_diameter_linear(self):
        """Діаметр лінійної мережі A-B-C-D дорівнює 3 перегонам."""
        net = make_network([("t1", [("A", 600, 600), ("B", 610, 610), ("C", 620, 620), ("D", 630, 630)])])
        self.assertEqual(network_diameter(net), 3)

    def test_network_diameter_disconnected(self):
        """Діаметр незв'язної мережі за замовчуванням повертає inf, а з ignore_disconnected - макс. компонент."""
        net = Network()
        for s in "ABCD":
            net.add_node(Stop(s, f"Зупинка {s}", 50.0, 30.0))
        # Дві ізольовані пари: A-B та C-D
        r1 = Route("r1", "1", Bus(), ["A", "B"])
        r2 = Route("r2", "2", Bus(), ["C", "D"])
        net.routes["r1"] = r1
        net.routes["r2"] = r2
        net.trips["t1"] = Trip("t1", r1, 600, "w", [("A", 600, 600), ("B", 610, 610)])
        net.trips["t2"] = Trip("t2", r2, 600, "w", [("C", 600, 600), ("D", 610, 610)])

        self.assertEqual(network_diameter(net), float('inf'))
        self.assertEqual(network_diameter(net, ignore_disconnected=True), 1)

    def test_average_shortest_path_length_linear(self):
        """Середня довжина найкоротшого шляху для A-B-C-D дорівнює 5/3 (1.666...)."""
        net = make_network([("t1", [("A", 600, 600), ("B", 610, 610), ("C", 620, 620), ("D", 630, 630)])])
        # Пари: A-B(1), A-C(2), A-D(3), B-C(1), B-D(2), C-D(1) -> всього 10 для 6 пар -> 10/6 = 5/3
        self.assertAlmostEqual(average_shortest_path_length(net), 5 / 3)

    def test_average_shortest_path_length_disconnected_raises(self):
        """Для незв'язної мережі без прапорця ignore_disconnected викидається DisconnectedNetworkError."""
        net = Network()
        for s in ["A", "B", "C"]:
            net.add_node(Stop(s, f"Зупинка {s}", 50.0, 30.0))
        # З'єднані лише A і B, C ізольована
        r1 = Route("r1", "1", Bus(), ["A", "B"])
        net.routes["r1"] = r1
        net.trips["t1"] = Trip("t1", r1, 600, "w", [("A", 600, 600), ("B", 610, 610)])

        with self.assertRaises(DisconnectedNetworkError):
            average_shortest_path_length(net)

        # З ignore_disconnected рахується для досяжної пари A-B
        self.assertEqual(average_shortest_path_length(net, ignore_disconnected=True), 1.0)

    def test_metrics_empty_and_single_node(self):
        """Межові випадки: порожня мережа та мережа з однією зупинкою."""
        net_empty = Network()
        self.assertEqual(degree_centrality(net_empty), {})
        self.assertEqual(network_diameter(net_empty), 0)
        self.assertEqual(average_shortest_path_length(net_empty), 0.0)

        net_single = Network()
        net_single.add_node(Stop("A", "Зупинка A", 50.0, 30.0))
        self.assertEqual(degree_centrality(net_single), {"A": 0.0})
        self.assertEqual(network_diameter(net_single), 0)
        self.assertEqual(average_shortest_path_length(net_single), 0.0)

    def test_calculate_network_metrics_and_router_wrapper(self):
        """Перевірка комплексної функції calculate_network_metrics та методів TransportRouter."""
        net = Network()
        for i, stop_id in enumerate("ABC"):
            net.add_node(Stop(stop_id, f"Зупинка {stop_id}", 50.0 + i / 100, 30.0 + i / 100))
        r = Route("r1", "1", Bus(), ["A", "B", "C"])
        net.routes["r1"] = r
        net.trips["t1"] = Trip("t1", r, 600, "w", [("A", 600, 600), ("B", 610, 610), ("C", 620, 620)])

        metrics = calculate_network_metrics(net)

        self.assertIn("degree_centrality", metrics)
        self.assertIn("diameter", metrics)
        self.assertIn("average_path_length", metrics)
        self.assertEqual(metrics["diameter"], 2)
        self.assertAlmostEqual(metrics["average_path_length"], 4 / 3)

        # Тест виклику через TransportRouter
        router = TransportRouter(net)
        self.assertEqual(router.network_diameter(), 2)
        self.assertAlmostEqual(router.average_shortest_path_length(), 4 / 3)
        self.assertEqual(router.network_metrics()["diameter"], 2)


if __name__ == '__main__':
    unittest.main()
