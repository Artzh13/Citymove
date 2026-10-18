import csv
from pathlib import Path
from typing import Iterator

from .domain import (
    Bus, Metro, Network, Route, ScheduleError, Stop, Tram, TransportUnit, Trip, Trolleybus,
)

Schedule = list[tuple[str, int, int]]

TRANSPORT_BY_ROUTE_TYPE: dict[str, type[TransportUnit]] = {
    '0': Tram,
    '1': Metro,
    '3': Bus,
    '11': Trolleybus,
}


def read_csv(path: str | Path) -> Iterator[dict[str, str]]:
    """
    Построчно читає GTFS csv-файл.
    :param path: шлях до файлу
    :return: генератор рядків у вигляді словників {назва_колонки: значення}
    """
    with open(path, mode='r', encoding='utf-8-sig', newline='') as file:
        yield from csv.DictReader(file)


def time_to_minutes(time_str: str) -> int:
    """
    Перетворює GTFS-час «HH:MM:SS» на хвилини від опівночі.
    Години можуть бути більшими за 24 (рейси після опівночі, напр. «25:10:00» -> 1510).
    :param time_str: час у форматі «HH:MM:SS»
    :return: кількість хвилин від опівночі (секунди відкидаються)
    :raises ScheduleError: якщо формат часу некоректний
    """
    try:
        hours, minutes, _seconds = map(int, time_str.strip().split(':'))
    except ValueError:
        raise ScheduleError(f"Некоректний час у розкладі: '{time_str}'") from None
    return hours * 60 + minutes


def make_transport(route_type: str) -> TransportUnit:
    """
    Створює об'єкт транспорту за значенням route_type з routes.txt.
    У київських даних: 0 — трамвай, 1 — метро, 3 — автобус, 11 — тролейбус.
    :param route_type: тип маршруту з routes.txt
    :return: об'єкт відповідного класу TransportUnit (невідомі типи вважаються автобусом)
    """
    transport_class = TRANSPORT_BY_ROUTE_TYPE.get(route_type, Bus)
    return transport_class()


def fix_midnight(schedule: Schedule) -> Schedule:
    """
    Робить розклад рейсу неспадним за часом.
    Деякі фіди (зокрема київський) пишуть час після опівночі як «00:05» замість «24:05».
    Якщо час «стрибає назад», до нього та всіх наступних часів додається доба (1440 хв).
    :param schedule: розклад рейсу [(stop_id, arrival_min, departure_min), ...]
    :return: виправлений розклад у тому ж форматі
    """
    result = []
    shift = 0
    last_time = 0

    for stop_id, arrival, departure in schedule:
        if arrival + shift < last_time:
            shift += 24 * 60
        last_time = departure + shift
        result.append((stop_id, arrival + shift, departure + shift))

    return result


def load_stops(path: str | Path) -> dict[str, Stop]:
    """
    Завантажує зупинки зі stops.txt.
    :param path: шлях до stops.txt
    :return: словник {stop_id: Stop}
    """
    stops = {}
    for row in read_csv(path):
        stop_id = row['stop_id']
        lat = float(row['stop_lat'])
        lon = float(row['stop_lon'])
        stops[stop_id] = Stop(stop_id, row['stop_name'], lat, lon)
    return stops


def load_stop_times(path: str | Path) -> dict[str, Schedule]:
    """
    Завантажує stop_times.txt і групує його за рейсами.
    :param path: шлях до stop_times.txt
    :return: словник {trip_id: [(stop_id, arrival_min, departure_min), ...]},
             зупинки кожного рейсу відсортовані за stop_sequence
    """
    rows_by_trip: dict[str, list[tuple[int, str, int, int]]] = {}

    for row in read_csv(path):
        rows_by_trip.setdefault(row['trip_id'], []).append((
            int(row['stop_sequence']),
            row['stop_id'],
            time_to_minutes(row['arrival_time']),
            time_to_minutes(row['departure_time']),
        ))

    stop_times = {}
    for trip_id, rows in rows_by_trip.items():
        rows.sort()
        schedule = [(stop_id, arrival, departure) for _seq, stop_id, arrival, departure in rows]
        stop_times[trip_id] = fix_midnight(schedule)

    return stop_times


def load_routes(path: str | Path, trip_rows: list[dict[str, str]],
                stop_times: dict[str, Schedule]) -> dict[str, Route]:
    """
    Завантажує маршрути з routes.txt.
    Список зупинок маршруту береться з його найдовшого рейсу (без повторів).
    :param path: шлях до routes.txt
    :param trip_rows: рядки з trips.txt (лише рейси, для яких є розклад)
    :param stop_times: результат load_stop_times()
    :return: словник {route_id: Route}
    """
    longest_trip: dict[str, str] = {}
    for row in trip_rows:
        route_id, trip_id = row['route_id'], row['trip_id']
        best = longest_trip.get(route_id)
        if best is None or len(stop_times[trip_id]) > len(stop_times[best]):
            longest_trip[route_id] = trip_id

    routes = {}
    for row in read_csv(path):
        route_id = row['route_id']

        schedule = stop_times.get(longest_trip.get(route_id), [])
        stops = list(dict.fromkeys(stop_id for stop_id, _arr, _dep in schedule))

        transport = make_transport(row['route_type'])
        routes[route_id] = Route(route_id, row['route_short_name'], transport, stops)

    return routes


def load_trips(trip_rows: list[dict[str, str]], routes: dict[str, Route],
               stop_times: dict[str, Schedule]) -> dict[str, Trip]:
    """
    Створює рейси. start_time — час відправлення з першої зупинки (хв від опівночі).
    Рейси, маршруту яких немає в routes, пропускаються.
    :param trip_rows: рядки з trips.txt (лише рейси, для яких є розклад)
    :param routes: результат load_routes()
    :param stop_times: результат load_stop_times()
    :return: словник {trip_id: Trip}
    """
    trips = {}
    for row in trip_rows:
        route = routes.get(row['route_id'])
        if route is None:
            continue

        trip_id = row['trip_id']
        schedule = stop_times[trip_id]
        start_time = schedule[0][2]
        trips[trip_id] = Trip(trip_id, route, start_time, row['service_id'], schedule)

    return trips


def build_network(stops: dict[str, Stop], routes: dict[str, Route],
                  trips: dict[str, Trip], transfer_time: int = 5) -> Network:
    """
    Збирає мережу та будує ребра графа між сусідніми зупинками кожного рейсу.
    :param stops: результат load_stops()
    :param routes: результат load_routes()
    :param trips: результат load_trips()
    :param transfer_time: час на пересадку у хвилинах
    :return: Network, де edges =
             {from_stop_id: [(to_stop_id, departure_min, travel_min, trip_id), ...]},
             кожен список ребер відсортовано за часом відправлення
    """
    network = Network(transfer_time)
    network.stops = stops
    network.routes = routes
    network.trips = trips

    for trip in trips.values():
        schedule = trip.stop_times
        for current, following in zip(schedule, schedule[1:]):
            from_stop, _, departure = current
            to_stop, arrival, _ = following
            edge = (to_stop, departure, arrival - departure, trip.trip_id)
            network.edges.setdefault(from_stop, []).append(edge)

    for edges in network.edges.values():
        edges.sort(key=lambda edge: edge[1])

    return network


def load_network(folder: str | Path, transfer_time: int = 5) -> Network:
    """
    Завантажує GTFS-фід із папки та будує мережу.
    :param folder: шлях до папки з файлами GTFS (напр. data/gtfs_static)
    :param transfer_time: час на пересадку у хвилинах
    :return: готовий Network
    """
    folder = Path(folder)

    stops = load_stops(folder / 'stops.txt')
    stop_times = load_stop_times(folder / 'stop_times.txt')
    trip_rows = [row for row in read_csv(folder / 'trips.txt') if row['trip_id'] in stop_times]

    routes = load_routes(folder / 'routes.txt', trip_rows, stop_times)
    trips = load_trips(trip_rows, routes, stop_times)
    return build_network(stops, routes, trips, transfer_time)
