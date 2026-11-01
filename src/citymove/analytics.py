from .domain import Stop, Trip, Route, StopNotFoundError, Bus, Network
import matplotlib.pyplot as plt
#===========================================================================================================================
def stop_info_table(stop: Stop, routes: list[str] = None) -> str:
    """Генерує та повертає текстову картку зупинки"""
    border = '=' * 73
    routes_list = routes if routes else []
    routes_str = ", ".join(routes_list) if routes_list else "(Маршрутів немає)"
    lines = [
        border,
        f"{"ІНФОРМАЦІЯ ПРО ЗУПИНКУ":^70}",
        border,
        f"| {"Назва:":<20}{stop.name:<50} |",
        f"| {"ID:":<20}{stop.stop_id:<50} |",
        f"| {"Координати:":<20}{stop.lat:.4f}, {stop.lon:.4f}{" " * 34} |",
        f"| {"Маршрути:":<20}{routes_str:<50} |",
        border
    ]
    return "\n".join(lines)
#===========================================================================================================================
def print_stop_info(stop: Stop, routes: list[str] = None) -> None:
    """Одразу виводить текстову картку зупинки в консоль"""
    print(stop_info_table(stop, routes))
#===========================================================================================================================





#===========================================================================================================================
def departure_board_table(stop_name: str, trips: list) -> str:
    """Генерує та повертає текстове табло відправлень для конкретної зупинки"""
    width = 78
    border = "=" * width
    header = f" ТАБЛО ВІДПРАВЛЕНЬ: {stop_name.upper()} "

    # чи існує передана зупинка у переданих маршрутах
    stop_exists = any(
        stop.lower() == stop_name.lower() 
        for trip in trips 
        for stop in trip.route.stops
    )

    if not stop_exists:
        raise StopNotFoundError(f"Exception: stop {stop_name} is not found!")

    # які маршрути проходять чнрез передану зупинку
    filtered_trips = [
        trip for trip in trips 
        if any(stop.lower() == stop_name.lower() for stop in trip.route.stops)
    ]

    lines = [
        border,
        f"{header:^{width}}",
        border,
        f"| {'Час':^10} | {'Маршрут':^10} | {'Тип':^12} | {'Кінцева (ID)':^32} |",
        "-" * width
    ]

    if not filtered_trips:
        lines.append(f"| {'Рейсів на сьогодні більше немає':^{width - 4}} |")
    else:
        for trip in filtered_trips:
            hours = trip.start_time // 60
            minutes = trip.start_time % 60
            time_str = f"{hours:02d}:{minutes:02d}:00"

            route_str = trip.route.short_name
            type_str = trip.route.transport.name()

            dest_str = trip.route.stops[-1] if trip.route.stops else "Невідомо"
            if len(dest_str) > 30:
                dest_str = dest_str[:27] + "..."

            lines.append(
                f"| {time_str:^10} | {route_str:^10} | {type_str:^12} | {dest_str:<32} |"
            )

    lines.append(border)
    return "\n".join(lines)
#===========================================================================================================================
def print_depatrures_board(stop_name: str, trips: list) -> None:
    """Одразу виводить текстове табло відправлень для конкретної зупинки в консоль"""
    print(departure_board_table(stop_name,trips))
#===========================================================================================================================

#===========================================================================================================================
def calculate_route_intervals(trips: list[Trip], route_id: str) -> list[int]:
    """Допоміжна функція для розрахунку інтервалів (у хвилинах) між рейсами одного маршруту[cite: 2]."""
    route_trips = [t for t in trips if t.route.route_id == route_id]
    route_trips.sort(key=lambda t: t.start_time)

    intervals = []
    for i in range(1, len(route_trips)):
        intervals.append(route_trips[i].start_time - route_trips[i-1].start_time)
    return intervals

#===========================================================================================================================
def route_intervals_table(route_id: str, trips: list[Trip]) -> str:
    """Генерує текстову таблицю інтервалів руху для заданого маршруту[cite: 2]."""
    intervals = calculate_route_intervals(trips, route_id)
    
    route_name = next((t.route.short_name for t in trips if t.route.route_id == route_id), route_id)
    width = 60
    border = "=" * width
    lines = [
        border,
        f" ІНТЕРВАЛИ РУХУ: МАРШРУТ {route_name} ".center(width),
        border
    ]

    if not intervals:
        lines.append(f"| {'Недостатньо рейсів для розрахунку інтервалів':^{width-4}} |")
    else:
        lines.append(f"| {'Кількість рейсів:':<30} {len(intervals) + 1:<23} |")
        lines.append(f"| {'Мінімальний інтервал:':<30} {min(intervals):<20} хв |")
        lines.append(f"| {'Максимальний інтервал:':<30} {max(intervals):<20} хв |")
        lines.append(f"| {'Середній інтервал:':<30} {sum(intervals)/len(intervals):<20.1f} хв |")

    lines.append(border)
    return "\n".join(lines)

#===========================================================================================================================
def print_route_intervals(route_id: str, trips: list[Trip]) -> None:
    """Одразу виводить текстову таблицю інтервалів у консоль[cite: 2]."""
    print(route_intervals_table(route_id, trips))

#===========================================================================================================================
def setup_plot_style() -> None:
    """Встановлює єдиний стиль оформлення графіків як шаблон для команди."""
    plt.style.use('seaborn-v0_8-darkgrid')
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 12

#===========================================================================================================================
def plot_interval_histogram(trips: list[Trip]) -> None:
    """Будує гістограму розподілу інтервалів руху по всіх маршрутах мережі."""
    setup_plot_style()
    all_intervals = []

    route_ids = {t.route.route_id for t in trips}
    for r_id in route_ids:
        all_intervals.extend(calculate_route_intervals(trips, r_id))

    if not all_intervals:
        print("Немає даних для побудови гістограми.")
        return

    plt.figure()
    plt.hist(all_intervals, bins=20, color='skyblue', edgecolor='black')
    plt.title('Розподіл інтервалів руху громадського транспорту')
    plt.xlabel('Інтервал (хвилини)')
    plt.ylabel('Кількість випадків')
    plt.tight_layout()
    plt.show()

#===========================================================================================================================
def plot_top_stops(network: Network, top_n: int = 10) -> None:
    """Будує стовпчикову діаграму топ-N зупинок за кількістю з'єднань[cite: 6]."""
    setup_plot_style()

    if not network.edges:
        print("Мережа не містить з'єднань.")
        return

    connections_count = {stop_id: len(edges) for stop_id, edges in network.edges.items()}
    top_stops = sorted(connections_count.items(), key=lambda item: item[1], reverse=True)[:top_n]

    stop_names, counts = [], []
    for stop_id, count in top_stops:
        name = network.stops[stop_id].name if stop_id in network.stops else stop_id
        stop_names.append(name[:13] + '..' if len(name) > 15 else name)
        counts.append(count)

    plt.figure()
    bars = plt.bar(stop_names, counts, color='coral', edgecolor='black')
    plt.title(f'Топ-{top_n} зупинок за кількістю з\'єднань')
    plt.xlabel('Зупинка')
    plt.ylabel('Кількість з\'єднань (відправлень)')
    plt.xticks(rotation=45, ha='right')

    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, int(yval), ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.show()

#===========================================================================================================================
def generate_console_report(network: Network) -> None:
    """Оформлення консольного підсумкового звіту за завантаженим фідом для Демонстрації 1[cite: 2]."""
    border = "=" * 50
    print(border)
    print(f"{'ПІДСУМКОВИЙ ЗВІТ ПО ТРАНСПОРТНІЙ МЕРЕЖІ':^50}")
    print(border)
    print(f"Кількість зупинок:  {len(network.stops)}")
    print(f"Кількість маршрутів: {len(network.routes)}")
    print(f"Кількість рейсів:   {len(network.trips)}")
    
    transport_types = set(r.transport.name() for r in network.routes.values())
    print(f"Види транспорту:    {', '.join(transport_types)}")
    print(border)