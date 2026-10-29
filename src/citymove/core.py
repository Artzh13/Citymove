import heapq
from dataclasses import dataclass, field
from . import domain

INF: float = 1e18

# graph[cur_idx] = [(departure_time, travel_time, trip_idx, next_stop_idx), ...]
Graph = list[list[tuple[float, float, int, int]]]


def build_graph(network: domain.Network) -> tuple[dict[str, int], int, Graph]:
    """
    Будує граф пересадок та поїздок на основі рейсів (Trip) з мережі.

    Повертає кортеж (stop_to_idx, M, graph), де:
        stop_to_idx - мапінг ID зупинки -> індекс,
        M - кількість рейсів,
        graph - масив суміжності:
            graph[cur_idx] = [(departure_time, travel_time, trip_idx, next_stop_idx), ...]
    """
    # Отримуємо всі зупинки та створюємо мапінг назва/ID -> індекс для швидкого доступу
    stop_ids = list(network.stops.keys())
    stop_to_idx = {stop_id: idx for idx, stop_id in enumerate(stop_ids)}
    N = len(stop_ids)

    # Індексація рейсів (Trip) для використання у станах Дейкстри
    trip_ids = list(network.trips.keys())
    trip_to_idx = {trip_id: idx for idx, trip_id in enumerate(trip_ids)}
    M = len(trip_ids)

    # Масив суміжності графа (формат описаний у Graph)
    graph: Graph = [[] for _ in range(N)]

    for trip_id, trip in network.trips.items():
        trip_idx = trip_to_idx[trip_id]
        # list[tuple[str, int, int]] -> (stop_id, arrival_min, departure_min)
        stop_times = trip.stop_times

        for j in range(len(stop_times) - 1):
            cur_stop_id, _, dep_cur = stop_times[j]
            next_stop_id, arr_next, _ = stop_times[j + 1]

            if cur_stop_id not in stop_to_idx or next_stop_id not in stop_to_idx:
                continue

            cur_idx = stop_to_idx[cur_stop_id]
            next_idx = stop_to_idx[next_stop_id]

            # Час у дорозі між зупинками рейсу
            travel_min = arr_next - dep_cur

            # Додаємо ребро до графа
            edge = (float(dep_cur), float(travel_min), trip_idx, next_idx)
            graph[cur_idx].append(edge)

    # Сортуємо ребра для кожної зупинки за часом відправлення
    for i in range(N):
        graph[i].sort(key=lambda x: x[0])

    return stop_to_idx, M, graph


@dataclass
class Journey:
    """
    Результат пошуку маршруту.

    Атрибути:
        cost: узагальнений час = фактичне прибуття + штрафи за всі пересадки (хв).
        arrival: фактичний час прибуття на кінцеву зупинку (хв від опівночі).
        transfers: кількість пересадок між рейсами.
        legs: ділянки поїздки одним рейсом у форматі
            (trip_id, from_stop_id, to_stop_id, departure_min, arrival_min).
    """
    cost: float
    arrival: float
    transfers: int
    legs: list[tuple[str, str, str, float, float]] = field(default_factory=list)


# Стан Дейкстри: (індекс зупинки, індекс рейсу); індекс рейсу M - "ще не сів у транспорт"
State = tuple[int, int]


def find_journey(network: domain.Network, start_stop_id: str, end_stop_id: str,
                 time_0: float, penalty: float = 0) -> Journey:
    """
    Дейкстра за розкладом зі штрафом `penalty` хвилин за кожну пересадку між рейсами.

    Штраф впливає лише на вартість (cost), а можливість сісти на рейс перевіряється
    за фактичним часом перебування на зупинці. Тому після пересадки можна їхати
    тим самим рейсом далі, а оптимальний шлях мінімізує "час + штрафи".

    Винятки:
        ValueError: якщо штраф від'ємний.
        StopNotFoundError: якщо зупинки немає в мережі.
        RouteNotFoundError: якщо кінцева зупинка недосяжна.
    """
    if penalty < 0:
        raise ValueError("Штраф за пересадку не може бути від'ємним.")

    stop_to_idx, M, graph = build_graph(network)
    if start_stop_id not in stop_to_idx or end_stop_id not in stop_to_idx:
        raise domain.StopNotFoundError("Одна з зупинок не знайдена в мережі.")

    idx_to_stop = list(stop_to_idx)
    trip_ids = list(network.trips)
    st, en = stop_to_idx[start_stop_id], stop_to_idx[end_stop_id]

    # Словники замість матриці N x (M + 1): на реальному GTFS матриця не влазить у пам'ять
    best: dict[State, float] = {(st, M): time_0}
    # parent[стан] = (попередній стан, час відправлення, час прибуття)
    parent: dict[State, tuple[State, float, float]] = {}
    # (cost, фактичний час, зупинка, рейс)
    queue: list[tuple[float, float, int, int]] = [(time_0, time_0, st, M)]

    while queue:
        cost, now, stop, trip = heapq.heappop(queue)
        if cost > best.get((stop, trip), INF):
            continue
        if stop == en:
            return _build_journey(parent, (stop, trip), cost, now, idx_to_stop, trip_ids)

        for dep_time, travel_time, trip_idx, nxt in graph[stop]:
            # Транспорт уже відійшов або некоректні дані (від'ємний час у дорозі)
            if dep_time < now or travel_time < 0:
                continue

            arrive = dep_time + travel_time
            is_transfer = trip != M and trip_idx != trip
            new_cost = cost + (arrive - now) + (penalty if is_transfer else 0)

            state = (nxt, trip_idx)
            if new_cost < best.get(state, INF):
                best[state] = new_cost
                parent[state] = ((stop, trip), dep_time, arrive)
                heapq.heappush(queue, (new_cost, arrive, nxt, trip_idx))

    raise domain.RouteNotFoundError("Шляху між заданими зупинками не знайдено.")


def _build_journey(parent: dict[State, tuple[State, float, float]], state: State,
                   cost: float, arrival: float, idx_to_stop: list[str],
                   trip_ids: list[str]) -> Journey:
    """Відновлює шлях за масивом предків і групує перегони одного рейсу в ділянки (legs)."""
    hops = []
    while state in parent:
        prev, dep_time, arr_time = parent[state]
        hops.append((trip_ids[state[1]], idx_to_stop[prev[0]], idx_to_stop[state[0]], dep_time, arr_time))
        state = prev
    hops.reverse()

    legs: list[tuple[str, str, str, float, float]] = []
    for trip_id, frm, to, dep_time, arr_time in hops:
        if legs and legs[-1][0] == trip_id:
            legs[-1] = (trip_id, legs[-1][1], to, legs[-1][3], arr_time)
        else:
            legs.append((trip_id, frm, to, dep_time, arr_time))

    return Journey(cost=cost, arrival=arrival, transfers=max(len(legs) - 1, 0), legs=legs)


def shortest_path_from(network: domain.Network, start_stop_id: str, end_stop_id: str,
                       time_0: float, penalty: float = 0) -> float:
    """
    Знаходить найкращий час прибуття з урахуванням розкладу рейсів та пересадок.

    Повертає узагальнений час (прибуття + penalty * кількість пересадок).
    Деталі маршруту доступні через find_journey().
    """
    return find_journey(network, start_stop_id, end_stop_id, time_0, penalty).cost


def get_network_topology(network: domain.Network, directed: bool = False) -> dict[str, set[str]]:
    """
    Побудова топологічного графа суміжності зупинок на основі рейсів, маршрутів та ребер.

    :param network: екземпляр Network.
    :param directed: чи зберігати напрямок руху (орієнтований граф).
    :return: словник {stop_id: set_of_neighbor_stop_ids}.
    """
    adj: dict[str, set[str]] = {stop_id: set() for stop_id in network.stops}

    # Збираємо сусідні зупинки з рейсів (Trips)
    for trip in network.trips.values():
        stop_times = trip.stop_times
        for j in range(len(stop_times) - 1):
            u = stop_times[j][0]
            v = stop_times[j + 1][0]
            if u in adj and v in adj:
                adj[u].add(v)
                if not directed:
                    adj[v].add(u)

    # Збираємо сусідні зупинки з маршрутів (Routes)
    for route in network.routes.values():
        stops = route.stops
        for j in range(len(stops) - 1):
            u = stops[j]
            v = stops[j + 1]
            if u in adj and v in adj:
                adj[u].add(v)
                if not directed:
                    adj[v].add(u)

    # Збираємо сусідні зупинки зі списку ребер Network.edges
    for u, edges in network.edges.items():
        if u not in adj:
            continue
        for edge in edges:
            v = edge[0]
            if v in adj:
                adj[u].add(v)
                if not directed:
                    adj[v].add(u)

    return adj


def degree_centrality(network: domain.Network, normalized: bool = True,
                      directed: bool = False) -> dict[str, float]:
    """
    Розраховує ступеневу центральність (degree centrality) для кожної зупинки в мережі.

    :param network: екземпляр Network.
    :param normalized: якщо True, ділить степінь вершини на (N - 1).
    :param directed: чи враховувати граф як орієнтований.
    :return: словник {stop_id: centrality_score}.
    """
    adj = get_network_topology(network, directed=directed)
    n = len(adj)
    if n <= 1:
        return {stop_id: 0.0 for stop_id in adj}

    denom = float(n - 1) if normalized else 1.0
    return {stop_id: len(neighbors) / denom for stop_id, neighbors in adj.items()}


def network_diameter(network: domain.Network, directed: bool = False,
                     ignore_disconnected: bool = False) -> int | float:
    """
    Розраховує діаметр мережі — максимальну найкоротшу топологічну відстань між парою зупинок.

    :param network: екземпляр Network.
    :param directed: чи розраховувати як орієнтований граф.
    :param ignore_disconnected: якщо True, обчислює максимальний діаметр серед зв'язних компонент.
                                 Якщо False, для незв'язної мережі повертає float('inf').
    :return: діаметр мережі (кількість перегонів).
    """
    adj = get_network_topology(network, directed=directed)
    n = len(adj)
    if n <= 1:
        return 0

    max_dist = 0
    total_reachable_pairs = 0

    for start_node in adj:
        visited = {start_node: 0}
        queue = [start_node]

        while queue:
            curr = queue.pop(0)
            d = visited[curr]
            for nxt in adj[curr]:
                if nxt not in visited:
                    visited[nxt] = d + 1
                    queue.append(nxt)

        total_reachable_pairs += (len(visited) - 1)

        for target_node, d in visited.items():
            if target_node != start_node and d > max_dist:
                max_dist = d

    is_connected = (total_reachable_pairs == n * (n - 1))
    if not is_connected and not ignore_disconnected:
        return float('inf')

    return max_dist


def average_shortest_path_length(network: domain.Network, directed: bool = False,
                                 ignore_disconnected: bool = False) -> float:
    """
    Розраховує середню довжину найкоротшого шляху (у перегонах) між усіма парами зупинок.

    :param network: екземпляр Network.
    :param directed: чи розраховувати як орієнтований граф.
    :param ignore_disconnected: якщо True, рахує середню довжину лише для досяжних пар.
                                 Якщо False, для незв'язної мережі викидає DisconnectedNetworkError.
    :return: середня довжина найкоротшого шляху.
    :raises DisconnectedNetworkError: якщо мережа незв'язна та ignore_disconnected=False.
    """
    adj = get_network_topology(network, directed=directed)
    n = len(adj)
    if n <= 1:
        return 0.0

    total_dist = 0
    total_pairs = 0

    for start_node in adj:
        visited = {start_node: 0}
        queue = [start_node]

        while queue:
            curr = queue.pop(0)
            d = visited[curr]
            for nxt in adj[curr]:
                if nxt not in visited:
                    visited[nxt] = d + 1
                    queue.append(nxt)

        for target_node, d in visited.items():
            if target_node != start_node:
                total_dist += d
                total_pairs += 1

    expected_pairs = n * (n - 1)
    if total_pairs < expected_pairs and not ignore_disconnected:
        raise domain.DisconnectedNetworkError(
            f"Мережа незв'язна: знайдено лише {total_pairs} з {expected_pairs} можливих шляхів."
        )

    if total_pairs == 0:
        return 0.0

    return total_dist / total_pairs


def calculate_network_metrics(network: domain.Network) -> dict[str, float | dict[str, float]]:
    """
    Обчислює комплексні топологічні метрики мережі:
    ступеневу центральність зупинок, діаметр та середню довжину шляху.
    """
    centr = degree_centrality(network)
    diam = network_diameter(network, ignore_disconnected=True)
    avg_len = average_shortest_path_length(network, ignore_disconnected=True)

    return {
        "degree_centrality": centr,
        "diameter": diam,
        "average_path_length": avg_len,
    }


class TransportRouter:
    """Клас для роботи з графом та пошуку найкоротшого шляху на основі мережі."""

    def __init__(self, network: domain.Network, transfer_penalty: float = 5.0) -> None:
        self.network = network
        self.transfer_penalty = transfer_penalty

    def shortest_path_from(self, start_stop_id: str, end_stop_id: str,
                           time_0: float, penalty: float | None = None) -> float:
        eff_penalty = self.transfer_penalty if penalty is None else penalty
        return shortest_path_from(self.network, start_stop_id, end_stop_id, time_0, eff_penalty)

    def degree_centrality(self, normalized: bool = True, directed: bool = False) -> dict[str, float]:
        return degree_centrality(self.network, normalized=normalized, directed=directed)

    def network_diameter(self, directed: bool = False, ignore_disconnected: bool = False) -> int | float:
        return network_diameter(self.network, directed=directed, ignore_disconnected=ignore_disconnected)

    def average_shortest_path_length(self, directed: bool = False, ignore_disconnected: bool = False) -> float:
        return average_shortest_path_length(self.network, directed=directed, ignore_disconnected=ignore_disconnected)

    def network_metrics(self) -> dict[str, float | dict[str, float]]:
        return calculate_network_metrics(self.network)