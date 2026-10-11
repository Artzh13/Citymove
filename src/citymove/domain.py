from abc import ABC, abstractmethod

class NetworkError(Exception):
    """Базовий клас для всіх помилок транспортної мережі."""
    pass

class StopNotFoundError(NetworkError):
    """Виняток, що викидається, якщо зупинку не знайдено в мережі."""
    pass

class RouteNotFoundError(NetworkError):
    """Виняток, що викидається, якщо маршрут не знайдено в мережі."""
    pass

class DisconnectedNetworkError(NetworkError):
    """Виняток, що викидається, якщо видалення вузла призведе до розриву мережі."""
    pass

class ScheduleError(NetworkError):
    """Виняток, що викидається при помилках у розкладі (наприклад, некоректний час)."""
    pass


class Stop:
    """
    Представляє фізичну зупинку в транспортній мережі.

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
        pass


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

    Атрибути:
        route_id (str): Унікальний технічний ідентифікатор маршруту.
        short_name (str): Короткий номер маршруту для виводу користувачу (наприклад, "1", "11").
        transport (TransportUnit): Об'єкт транспортного засобу, що обслуговує маршрут.
        stops (list[str]): Список ідентифікаторів зупинок маршруту без повторень.
    """

    def __init__(self, route_id: str, short_name: str, transport: TransportUnit, stops: list[str]) -> None:
        self._route_id = route_id
        self._short_name = short_name
        self._transport = transport
        self._stops = stops

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

    def __str__(self) -> str:
        """Повертає текстове представлення маршруту із зазначенням типу транспорту."""
        return f"Маршрут {self.short_name} [{self.transport.name()}]: {len(self.stops)} зупинок"


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

    def __init__(self, trip_id: str, route: Route, start_time: int, service_id: str, stop_times: list[tuple[str, int, int]]) -> None:
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
    def stop_times(self) -> list[tuple[str, int, int]]:
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
        

class Network:
    """
    Головний контейнер (граф), який зберігає весь стан транспортної системи.

    Атрибути:
        stops (dict[str, Stop]): Словник усіх зупинок, де ключ — ID зупинки, значення — об'єкт Stop.
        routes (dict[str, Route]): Словник усіх маршрутів, де ключ — ID маршруту, значення — об'єкт Route.
        trips (dict[str, Trip]): Словник усіх рейсів, де ключ — ID рейсу, значення — об'єкт Trip.
        transfer_time (int): Час на пересадку між рейсами у хвилинах (за замовчуванням 5 хвилин).
        edges (dict[str, list[tuple[str, int, int, str]]]): Список суміжності графа для алгоритму Дейкстри.
            Формат: {from_stop_id: [(to_stop_id, departure_min, travel_min, trip_id), ...]}
    """

    def __init__(self, transfer_time: int = 5) -> None:
        """Ініціалізує порожню транспортну мережу із заданим часом на пересадку у хвилинах."""
        self.stops: dict[str, Stop] = {}
        self.routes: dict[str, Route] = {}
        self.trips: dict[str, Trip] = {}
        self.transfer_time: int = transfer_time
        
        self.edges: dict[str, list[tuple[str, int, int, str]]] = {}