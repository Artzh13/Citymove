"""
Об'єктна модель транспортної мережі «МістоРух» (роль A).

Модуль описує сутності предметної області (Stop, Route, Trip, Passenger),
ієрархію транспорту (TransportUnit -> Bus, Tram, Trolleybus, Metro),
агрегат Network, який відповідає за цілісність графа, та ієрархію винятків.
"""
from abc import ABC, abstractmethod
from bisect import insort
from collections import deque
from typing import Iterator

__all__ = [
    "NetworkError", "StopNotFoundError", "RouteNotFoundError", "DisconnectedNetworkError",
    "ScheduleError", "DuplicateEntityError",
    "Stop", "TransportUnit", "Bus", "Tram", "Trolleybus", "Metro",
    "Route", "Passenger", "Trip", "Network",
]

# Ребро графа: (to_stop_id, departure_min, travel_min, trip_id)
Edge = tuple[str, int, int, str]
# Рядок розкладу: (stop_id, arrival_min, departure_min)
StopTime = tuple[str, int, int]


# ───────────────────────────── Винятки ─────────────────────────────

class NetworkError(Exception):
    """Базовий клас для всіх помилок транспортної мережі."""


class StopNotFoundError(NetworkError):
    """Виняток, що викидається, якщо зупинку не знайдено в мережі."""
    def __init__(self, stop_id: str):
        super().__init__(f"Зупинку з ID {stop_id} не знайдено!")
        self.stop_id = stop_id


class RouteNotFoundError(NetworkError):
    """Виняток, що викидається, якщо маршрут не знайдено в мережі."""
    def __init__(self, from_stop_or_msg: str, to_stop: str = ""):
        if to_stop:
            super().__init__(f"Не вдалося знайти маршрут від {from_stop_or_msg} до {to_stop}!")
            self.from_stop = from_stop_or_msg
            self.to_stop = to_stop
        else:
            super().__init__(from_stop_or_msg)
            self.from_stop = ""
            self.to_stop = ""


class DisconnectedNetworkError(NetworkError):
    """Виняток, що викидається, якщо видалення вузла призведе до розриву мережі."""
    def __init__(self, message: str = "Операція призводить до розриву звʼязності транспортної системи!"):
        super().__init__(message)


class ScheduleError(NetworkError):
    """Виняток, що викидається при помилках у розкладі (наприклад, некоректний час)."""
    def __init__(self, message: str = "Виявлено помилку у часі або розкладі рейсів!"):
        super().__init__(message)


class DuplicateEntityError(NetworkError, ValueError):
    """
    Виняток, що викидається при спробі додати в мережу об'єкт з уже наявним ID.
    Успадковується також від ValueError, щоб не ламати код, який перехоплює ValueError.
    """
    def __init__(self, entity: str, entity_id: str):
        super().__init__(f"{entity} з ID '{entity_id}' вже існує в мережі.")
        self.entity = entity
        self.entity_id = entity_id



class Stop:
    """
    Представляє фізичну зупинку в транспортній мережі.
    Зупинки — сутності: дві зупинки рівні, якщо мають однаковий stop_id.

    Атрибути:
        stop_id (str): Унікальний ідентифікатор зупинки (лише для читання).
        name (str): Назва зупинки.
        lat (float): Географічна широта в градусах.
        lon (float): Географічна довгота в градусах.
    """

    def __init__(self, stop_id: str, name: str, lat: float, lon: float) -> None:
        self._stop_id = stop_id
        self.name = name
        self.lat = lat
        self.lon = lon

    @property
    def stop_id(self) -> str:
        """Повертає ідентифікатор зупинки."""
        return self._stop_id

    @property
    def name(self) -> str:
        """Повертає назву зупинки."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """
        Встановлює назву зупинки.

        Винятки:
            ValueError: Якщо передано порожній рядок.
        """
        if not value.strip():
            raise ValueError("Назва зупинки не може бути порожньою.")
        self._name = value

    @property
    def lat(self) -> float:
        """Повертає географічну широту зупинки."""
        return self._lat

    @lat.setter
    def lat(self, value: float) -> None:
        """
        Встановлює географічну широту.

        Винятки:
            ValueError: Якщо значення виходить за межі [-90.0; 90.0].
        """
        if not (-90.0 <= value <= 90.0):
            raise ValueError(f"Некоректна широта: {value}")
        self._lat = value

    @property
    def lon(self) -> float:
        """Повертає географічну довготу зупинки."""
        return self._lon

    @lon.setter
    def lon(self, value: float) -> None:
        """
        Встановлює географічну довготу.

        Винятки:
            ValueError: Якщо значення виходить за межі [-180.0; 180.0].
        """
        if not (-180.0 <= value <= 180.0):
            raise ValueError(f"Некоректна довгота: {value}")
        self._lon = value

    def __str__(self) -> str:
        """Повертає текстове представлення зупинки."""
        return f"Зупинка '{self.name}' ({self.stop_id})"

    def __repr__(self) -> str:
        """Повертає однозначне представлення, з якого можна відтворити об'єкт."""
        return f"Stop({self.stop_id!r}, {self.name!r}, {self.lat!r}, {self.lon!r})"

    def __eq__(self, other: object) -> bool:
        """Зупинки рівні, якщо мають однаковий stop_id (назва та координати не враховуються)."""
        if not isinstance(other, Stop):
            return NotImplemented
        return self.stop_id == other.stop_id

    def __hash__(self) -> int:
        """Хеш за незмінним stop_id, щоб Stop можна було класти в set і використовувати як ключ dict."""
        return hash(self.stop_id)


class TransportUnit(ABC):
    """
    Абстрактний базовий клас для всіх видів транспорту.
    Усі характеристики є незмінними після створення.

    Атрибути:
        speed (float): Середня швидкість руху.
        capacity (int): Максимальна місткість пасажирів.
        fare (float): Вартість проїзду.
    """

    def __init__(self, speed: float, capacity: int, fare: float) -> None:
        self._speed = speed
        self._capacity = capacity
        self._fare = fare

    @property
    def speed(self) -> float:
        """Повертає середню швидкість транспорту."""
        return self._speed

    @property
    def capacity(self) -> int:
        """Повертає максимальну місткість транспорту."""
        return self._capacity

    @property
    def fare(self) -> float:
        """Повертає вартість проїзду."""
        return self._fare

    @abstractmethod
    def name(self) -> str:
        """Повертає назву виду транспорту, реалізується у класах-нащадках."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


class Bus(TransportUnit):
    """Клас автобуса із захардкодженими характеристиками (швидкість 20.0, місткість 80, тариф 15.0)."""
    def __init__(self) -> None:
        super().__init__(speed=20.0, capacity=80, fare=15.0)

    def name(self) -> str:
        return "Автобус"


class Tram(TransportUnit):
    """Клас трамвая із захардкодженими характеристиками (швидкість 16.0, місткість 150, тариф 8.0)."""
    def __init__(self) -> None:
        super().__init__(speed=16.0, capacity=150, fare=8.0)

    def name(self) -> str:
        return "Трамвай"


class Trolleybus(TransportUnit):
    """Клас тролейбуса із захардкодженими характеристиками (швидкість 18.0, місткість 100, тариф 12.0)."""
    def __init__(self) -> None:
        super().__init__(speed=18.0, capacity=100, fare=12.0)

    def name(self) -> str:
        return "Тролейбус"


class Metro(TransportUnit):
    """Клас метро із захардкодженими характеристиками (швидкість 40.0, місткість 1000, тариф 20.0)."""
    def __init__(self) -> None:
        super().__init__(speed=40.0, capacity=1000, fare=20.0)

    def name(self) -> str:
        return "Метро"


class Route:
    """
    Транспортний маршрут, який об'єднує транспортний засіб та послідовність зупинок.
    Маршрут є ітерованим: `for stop_id in route` обходить зупинки в порядку проходження.

    Атрибути:
        route_id (str): Унікальний технічний ідентифікатор маршруту.
        short_name (str): Короткий номер маршруту для виводу користувачу (наприклад, "1", "11").
        transport (TransportUnit): Об'єкт транспортного засобу, що обслуговує маршрут.
        stops (list[str]): Список ідентифікаторів зупинок маршруту у порядку проходження.
    """

    def __init__(self, route_id: str, short_name: str, transport: TransportUnit, stops: list[str]) -> None:
        self._route_id = route_id
        self._short_name = short_name
        self._transport = transport
        # копія, щоб зміна списку ззовні не змінювала маршрут непомітно
        self._stops = list(stops)

    @property
    def route_id(self) -> str:
        """Повертає технічний ідентифікатор маршруту."""
        return self._route_id

    @property
    def short_name(self) -> str:
        """Повертає короткий номер маршруту."""
        return self._short_name

    @property
    def transport(self) -> TransportUnit:
        """Повертає транспортний засіб маршруту."""
        return self._transport

    @property
    def stops(self) -> list[str]:
        """Повертає список ID зупинок маршруту."""
        return self._stops

    def __iter__(self) -> Iterator[str]:
        """Послідовно обходить ID зупинок маршруту від першої до останньої."""
        return iter(self._stops)

    def __str__(self) -> str:
        """Повертає текстове представлення маршруту із зазначенням типу транспорту."""
        return f"Маршрут {self.short_name} [{self.transport.name()}]: {len(self.stops)} зупинок"

    def __repr__(self) -> str:
        return f"Route({self.route_id!r}, {self.short_name!r}, {self.transport!r}, {self.stops!r})"


class Passenger:
    """
    Пасажир, який користується транспортною мережею.

    Атрибути:
        passenger_id (str): Унікальний ідентифікатор пасажира.
        name (str): Ім'я пасажира.
    """

    def __init__(self, passenger_id: str, name: str = "Unknown") -> None:
        self._passenger_id = passenger_id
        self.name = name

    @property
    def passenger_id(self) -> str:
        """Повертає ідентифікатор пасажира."""
        return self._passenger_id

    @property
    def name(self) -> str:
        """Повертає ім'я пасажира."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """
        Встановлює ім'я пасажира. Якщо передано порожній рядок, встановлює 'Unknown'.
        """
        self._name = value if value.strip() else "Unknown"

    def __repr__(self) -> str:
        return f"Passenger({self.passenger_id!r}, {self.name!r})"


class Trip:
    """
    Конкретний рейс за певним маршрутом із детальним розкладом.

    Атрибути:
        trip_id (str): Унікальний ідентифікатор рейсу.
        route (Route): Об'єкт маршруту, за яким здійснюється рейс.
        start_time (int): Загальний час відправлення.
        service_id (str): Ідентифікатор днів курсування (будні/вихідні).
        stop_times (list[tuple[str, int, int]]): Розклад руху у форматі (stop_id, arrival_min, departure_min).
    """

    def __init__(self, trip_id: str, route: Route, start_time: int, service_id: str,
                 stop_times: list[StopTime]) -> None:
        self._trip_id = trip_id
        self._route = route
        self.start_time = start_time
        self._service_id = service_id
        self._stop_times = stop_times

    @property
    def trip_id(self) -> str:
        """Повертає ідентифікатор рейсу."""
        return self._trip_id

    @property
    def route(self) -> Route:
        """Повертає маршрут рейсу."""
        return self._route

    @property
    def service_id(self) -> str:
        """Повертає ідентифікатор днів курсування рейсу."""
        return self._service_id

    @property
    def stop_times(self) -> list[StopTime]:
        """Повертає розклад руху рейсу зупинками у хвилинах."""
        return self._stop_times

    @property
    def start_time(self) -> int:
        """Повертає час відправлення рейсу."""
        return self._start_time

    @start_time.setter
    def start_time(self, value: int) -> None:
        """
        Встановлює час відправлення.

        Винятки:
            ValueError: Якщо час є від'ємним числом.
        """
        if value < 0:
            raise ValueError("Час відправлення не може бути від'ємним.")
        self._start_time = value

    def edges(self) -> Iterator[Edge]:
        """Генерує ребра графа між сусідніми зупинками рейсу у форматі Network.edges."""
        for (from_stop, _, departure), (to_stop, arrival, _) in zip(self._stop_times, self._stop_times[1:]):
            yield from_stop, (to_stop, departure, arrival - departure, self._trip_id)

    def validate_schedule(self) -> None:
        """
        Перевіряє, що час у розкладі не йде назад.

        Винятки:
            ScheduleError: Якщо відправлення раніше прибуття або наступна зупинка раніше попередньої.
        """
        last_time = 0
        for stop_id, arrival, departure in self._stop_times:
            if departure < arrival:
                raise ScheduleError(f"Рейс '{self.trip_id}': відправлення з '{stop_id}' раніше прибуття.")
            if arrival < last_time:
                raise ScheduleError(f"Рейс '{self.trip_id}': час на зупинці '{stop_id}' йде назад.")
            last_time = departure

    def __repr__(self) -> str:
        return (f"Trip({self.trip_id!r}, route={self.route.route_id!r}, start_time={self.start_time}, "
                f"service_id={self.service_id!r}, stops={len(self.stop_times)})")


# ───────────────────────────── Агрегат ─────────────────────────────

class Network:
    """
    Головний контейнер (агрегат), який зберігає стан транспортної системи
    і стежить за її цілісністю. Підтримує протокол контейнера:
    `len(network)` — кількість зупинок, `"s1" in network` / `stop in network`,
    `for stop in network` — обхід об'єктів Stop.

    Атрибути:
        stops (dict[str, Stop]): Словник усіх зупинок, де ключ - ID зупинки, значення — об'єкт Stop.
        routes (dict[str, Route]): Словник усіх маршрутів, де ключ - ID маршруту, значення - об'єкт Route.
        trips (dict[str, Trip]): Словник усіх рейсів, де ключ - ID рейсу, значення - об'єкт Trip.
        transfer_time (int): Час на пересадку між рейсами у хвилинах (за замовчуванням 5 хвилин).
        edges (dict[str, list[tuple[str, int, int, str]]]): Список суміжності графа для алгоритму Дейкстри.
            Формат: {from_stop_id: [(to_stop_id, departure_min, travel_min, trip_id), ...]},
            кожен список відсортований за часом відправлення.
    """

    def __init__(self, transfer_time: int = 5) -> None:
        """Ініціалізує порожню транспортну мережу із заданим часом на пересадку у хвилинах."""
        self.stops: dict[str, Stop] = {}
        self.routes: dict[str, Route] = {}
        self.trips: dict[str, Trip] = {}
        self.transfer_time: int = transfer_time

        self.edges: dict[str, list[Edge]] = {}

    # ── протокол контейнера ──

    def __len__(self) -> int:
        """Повертає кількість зупинок у мережі."""
        return len(self.stops)

    def __contains__(self, item: object) -> bool:
        """Перевіряє, чи є зупинка в мережі. Приймає як об'єкт Stop, так і рядок stop_id."""
        if isinstance(item, Stop):
            return item.stop_id in self.stops
        if isinstance(item, str):
            return item in self.stops
        return False

    def __iter__(self) -> Iterator[Stop]:
        """Обходить усі зупинки мережі."""
        return iter(self.stops.values())

    def __repr__(self) -> str:
        return (f"Network(stops={len(self.stops)}, routes={len(self.routes)}, "
                f"trips={len(self.trips)}, transfer_time={self.transfer_time})")

    # ── додавання об'єктів ──

    def add_node(self, stop: Stop) -> None:
        """
        Додає нову зупинку (вузол) до мережі.

        Винятки:
            DuplicateEntityError: Якщо зупинка з таким ID вже існує (є підкласом ValueError).
        """
        if stop.stop_id in self.stops:
            raise DuplicateEntityError("Зупинка", stop.stop_id)
        self.stops[stop.stop_id] = stop
        self.edges.setdefault(stop.stop_id, [])

    def add_route(self, route: Route) -> None:
        """
        Додає новий маршрут до мережі.

        Винятки:
            DuplicateEntityError: Якщо маршрут із таким ID вже існує.
            StopNotFoundError: Якщо якась із зупинок маршруту відсутня в мережі.
        """
        if route.route_id in self.routes:
            raise DuplicateEntityError("Маршрут", route.route_id)
        self._require_stops(route)
        self.routes[route.route_id] = route

    def add_trip(self, trip: Trip) -> None:
        """
        Додає новий рейс до мережі та будує для нього ребра графа.

        Винятки:
            DuplicateEntityError: Якщо рейс із таким ID вже існує.
            ScheduleError: Якщо маршрут рейсу не зареєстрований у мережі або розклад некоректний.
            StopNotFoundError: Якщо зупинки з розкладу немає в мережі.
        """
        if trip.trip_id in self.trips:
            raise DuplicateEntityError("Рейс", trip.trip_id)
        if trip.route.route_id not in self.routes:
            raise ScheduleError(f"Маршрут '{trip.route.route_id}' для рейсу не знайдено.")
        self._require_stops(stop_id for stop_id, _, _ in trip.stop_times)
        trip.validate_schedule()

        self.trips[trip.trip_id] = trip
        for from_stop, edge in trip.edges():
            insort(self.edges.setdefault(from_stop, []), edge, key=lambda e: e[1])

    def _require_stops(self, stop_ids) -> None:
        """Викидає StopNotFoundError для першої зупинки, якої немає в мережі."""
        for stop_id in stop_ids:
            if stop_id not in self.stops:
                raise StopNotFoundError(stop_id)

    # ── зв'язність графа ──

    def _undirected_adjacency(self) -> dict[str, set[str]]:
        """Будує неорієнтований граф сусідства зупинок з ребер edges."""
        adjacency: dict[str, set[str]] = {stop_id: set() for stop_id in self.stops}
        for from_stop, edges in self.edges.items():
            for to_stop, *_ in edges:
                if from_stop in adjacency and to_stop in adjacency and from_stop != to_stop:
                    adjacency[from_stop].add(to_stop)
                    adjacency[to_stop].add(from_stop)
        return adjacency

    @staticmethod
    def _reachable(adjacency: dict[str, set[str]], start: str, excluded: str | None = None) -> set[str]:
        """BFS: повертає множину вершин, досяжних зі start, оминаючи вершину excluded."""
        visited = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor != excluded and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited

    def is_connected(self) -> bool:
        """Перевіряє (слабку) зв'язність мережі: з будь-якої зупинки можна дістатися будь-якої іншої."""
        if not self.stops:
            return True
        adjacency = self._undirected_adjacency()
        start = next(iter(self.stops))
        return len(self._reachable(adjacency, start)) == len(self.stops)

    def _is_cut_vertex(self, stop_id: str) -> bool:
        """
        Перевіряє, чи є зупинка «мостом» (точкою зчленування): чи розпадуться її сусіди
        на різні компоненти, якщо цю зупинку прибрати. Решта мережі не враховується,
        тож перевірка коректна і для мереж, які вже складаються з кількох частин.
        """
        adjacency = self._undirected_adjacency()
        neighbors = adjacency[stop_id]
        if len(neighbors) < 2:
            return False
        reachable = self._reachable(adjacency, next(iter(neighbors)), excluded=stop_id)
        return not neighbors <= reachable

    # ── вилучення об'єктів ──

    def remove_node(self, stop_id: str) -> None:
        """
        Видаляє зупинку з мережі разом із пов'язаними рейсами, маршрутами та ребрами.

        Винятки:
            StopNotFoundError: Якщо зупинку не знайдено.
            DisconnectedNetworkError: Якщо видалення зупинки розірве зв'язок між її сусідами.
        """
        if stop_id not in self.stops:
            raise StopNotFoundError(stop_id)
        if self._is_cut_vertex(stop_id):
            raise DisconnectedNetworkError(
                f"Видалення зупинки '{stop_id}' призведе до розриву транспортної мережі"
            )

        # Рейси, розклад яких проходить через зупинку, та маршрути з цією зупинкою
        removed_trips = {trip_id for trip_id, trip in self.trips.items()
                         if any(st[0] == stop_id for st in trip.stop_times)}
        removed_routes = {route_id for route_id, route in self.routes.items() if stop_id in route}
        # рейси видалених маршрутів теж стають недійсними
        removed_trips |= {trip_id for trip_id, trip in self.trips.items()
                          if trip.route.route_id in removed_routes}

        for trip_id in removed_trips:
            del self.trips[trip_id]
        for route_id in removed_routes:
            del self.routes[route_id]

        del self.stops[stop_id]
        self.edges.pop(stop_id, None)
        # прибираємо вхідні ребра та ребра видалених рейсів, щоб у графі не лишилось «висячих» trip_id
        for from_stop, edges in self.edges.items():
            self.edges[from_stop] = [e for e in edges if e[0] != stop_id and e[3] not in removed_trips]
