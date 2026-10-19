import heapq
from citymove import domain

INF: float = 1e18

class TransportRouter:
    """Клас для побудови графа та пошуку найкоротшого шляху на основі моделей з domain.py."""
    
    def __init__(self, network: domain.Network, transfer_penalty: float = 5.0) -> None:
        self.network = network
        self.transfer_penalty = transfer_penalty
        
        # Отримуємо всі зупинки та створюємо мапінг назва/ID -> індекс для швидкого доступу
        self.stop_ids = list(network.stops.keys())
        self.stop_to_idx = {stop_id: idx for idx, stop_id in enumerate(self.stop_ids)}
        self.N = len(self.stop_ids)
        
        # Індексація рейсів (Trip) для використання у станах Дейкстри
        self.trip_ids = list(network.trips.keys())
        self.trip_to_idx = {trip_id: idx for idx, trip_id in enumerate(self.trip_ids)}
        self.M = len(self.trip_ids)
        
        # Масив суміжності графа: graph[cur_idx] = [(departure_time, travel_time, trip_idx, next_stop_idx), ...]
        self.graph = [[] for _ in range(self.N)]
        self.build_graph()

    def build_graph(self) -> None:
        """Будує граф пересадок та поїздок на основі рейсів (Trip) з мережі."""
        for trip_id, trip in self.network.trips.items():
            trip_idx = self.trip_to_idx[trip_id]
            stop_times = trip.stop_times  # list[tuple[str, int, int]] -> (stop_id, arrival_min, departure_min)
            
            for j in range(len(stop_times) - 1):
                cur_stop_id, _, dep_cur = stop_times[j]
                next_stop_id, arr_next, _ = stop_times[j + 1]
                
                if cur_stop_id not in self.stop_to_idx or next_stop_id not in self.stop_to_idx:
                    continue
                
                cur_idx = self.stop_to_idx[cur_stop_id]
                next_idx = self.stop_to_idx[next_stop_id]
                
                # Час у дорозі між зупинками рейсу
                travel_min = arr_next - dep_cur
                
                # Додаємо ребро до графа
                edge = (float(dep_cur), float(travel_min), trip_idx, next_idx)
                self.graph[cur_idx].append(edge)
        
        # Сортуємо ребра для кожної зупинки за часом відправлення
        for i in range(self.N):
            self.graph[i].sort(key=lambda x: x[0])

    def shortest_path_from(self, start_stop_id: str, end_stop_id: str, time_0: float, penalty: float = 0) -> float:
        """
        Знаходить найкоротший час прибуття з урахуванням розкладу рейсів та пересадок.
        """
        if start_stop_id not in self.stop_to_idx or end_stop_id not in self.stop_to_idx:
            raise domain.StopNotFoundError("Одна з зупинок не знайдена в мережі.")
            
        st = self.stop_to_idx[start_stop_id]
        en = self.stop_to_idx[end_stop_id]
        
        # M - спеціальний початковий стан (коли пасажир ще не сіл на жоден рейс)
        initial_state = self.M
        dist = [[INF] * (self.M + 1) for _ in range(self.N)]
        
        dist[st][initial_state] = time_0 
        queue = []
        heapq.heappush(queue, (time_0, st, initial_state))

        while queue:
            cur_time, stop, idx = heapq.heappop(queue)

            if idx != initial_state and cur_time > dist[stop][idx]:
                continue

            for dep_time, travel_time, trip_idx, nxt in self.graph[stop]:
                # Якщо транспорт вже відійшов до того, як ми прибули на зупинку
                if dep_time < cur_time:
                    continue

                # Якщо це той самий рейс — пересадка не потрібна, інакше додаємо штраф за пересадку
                if trip_idx == idx or idx == initial_state:
                    new_dist = dep_time + travel_time
                else:
                    new_dist = dep_time + travel_time + penalty

                if new_dist < dist[nxt][trip_idx]:
                    dist[nxt][trip_idx] = new_dist
                    heapq.heappush(queue, (new_dist, nxt, trip_idx))

        mini = INF
        for j in range(self.M + 1):
            mini = min(mini, dist[en][j])

        if mini == INF:
            raise domain.RouteNotFoundError("Шляху між заданими зупинками не знайдено.")

        return mini