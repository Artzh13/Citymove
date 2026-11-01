import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from .domain import Stop, Trip, Route, StopNotFoundError, Bus, Network

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
# ЄДИНИЙ СТИЛЬ ГРАФІКІВ CityMove — шаблон для команди.
# Новий графік будуємо через new_axes(...), колір однієї серії — PRIMARY_COLOR, кількох — SERIES_COLORS по порядку,
# легенду додаємо через add_legend(ax).
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
PRIMARY_COLOR, BACKGROUND, TEXT_COLOR, GRID_COLOR = SERIES_COLORS[0], "#fcfcfb", "#52514e", "#e4e3df"

CITYMOVE_STYLE = {
    "figure.figsize": (10, 6), "figure.facecolor": BACKGROUND, "axes.facecolor": BACKGROUND,
    "axes.titlesize": 15, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.labelcolor": TEXT_COLOR, "axes.edgecolor": GRID_COLOR, "axes.grid": True, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "axes.prop_cycle": plt.cycler(color=SERIES_COLORS),
    "grid.color": GRID_COLOR, "xtick.color": TEXT_COLOR, "ytick.color": TEXT_COLOR, "legend.frameon": False,
}
#===========================================================================================================================
def new_axes(title: str, xlabel: str = "", ylabel: str = ""):
    """Створює порожній графік у стилі CityMove та повертає (fig, ax)"""
    with plt.rc_context(CITYMOVE_STYLE):
        fig, ax = plt.subplots()
        ax.set(title=title, xlabel=xlabel, ylabel=ylabel)
    return fig, ax
#===========================================================================================================================
def add_legend(ax, **kwargs):
    """Додає легенду в стилі CityMove (стиль з new_axes діє лише під час створення осей, тому легенду оформлюємо тут)"""
    return ax.legend(**{"frameon": False, "labelcolor": TEXT_COLOR, **kwargs})
#===========================================================================================================================





#===========================================================================================================================
def route_headways(trips: list[Trip], service_ids: set[str] = None, max_gap: int = 120) -> list[int]:
    """
    Інтервали руху (хв) між сусідніми рейсами одного маршруту в одному напрямку (за першою зупинкою).
    service_ids — брати лише ці рейси (напр. будні з calendar.txt); інтервали > max_gap (ніч) відкидаються.
    """
    departures: dict[tuple[str, str], list[int]] = {}
    for trip in trips:
        if service_ids is None or trip.service_id in service_ids:
            key = (trip.route.route_id, trip.stop_times[0][0] if trip.stop_times else "")
            departures.setdefault(key, []).append(trip.start_time)
    gaps = []
    for times in departures.values():
        times.sort()
        gaps += [b - a for a, b in zip(times, times[1:]) if 0 < b - a <= max_gap]
    return gaps
#===========================================================================================================================
def plot_headway_histogram(headways: list[int], bin_size: int = 5) -> Figure:
    """Графік 1: гістограма розподілу інтервалів руху"""
    if not headways:
        raise ValueError("Немає інтервалів для побудови гістограми")
    fig, ax = new_axes("Розподіл інтервалів руху", "Інтервал між рейсами, хв", "Кількість інтервалів")
    ax.hist(headways, bins=range(0, max(headways) + bin_size, bin_size), color=PRIMARY_COLOR,
            edgecolor=BACKGROUND, linewidth=2)
    return fig
#===========================================================================================================================





#===========================================================================================================================
def busiest_stops(network: Network, top: int = 10) -> list[tuple[str, int]]:
    """
    Top-N зупинок за кількістю з'єднань (ребер network.edges); платформи з однаковою назвою сумуються.
    Лапки в назвах ігноруються, бо у фіді одна зупинка буває записана як «ст.м. Лісова» і «ст.м. "Лісова"».
    """
    counts: dict[str, int] = {}
    for stop_id, edges in network.edges.items():
        name = network.stops[stop_id].name if stop_id in network.stops else stop_id
        name = " ".join(name.translate(str.maketrans("", "", '"«»')).split())
        counts[name] = counts.get(name, 0) + len(edges)
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:top]
#===========================================================================================================================
def plot_busiest_stops(stops: list[tuple[str, int]]) -> Figure:
    """Графік 2: стовпчикова діаграма Top-N найзавантаженіших зупинок (найбільша — зверху)"""
    if not stops:
        raise ValueError("Немає зупинок для побудови діаграми")
    fig, ax = new_axes(f"Top-{len(stops)} найзавантаженіших зупинок", "Кількість з'єднань")
    bars = ax.barh([name for name, _ in stops][::-1], [count for _, count in stops][::-1], color=PRIMARY_COLOR)
    ax.bar_label(bars, padding=4)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()  # щоб довгі назви зупинок не обрізались
    return fig
#===========================================================================================================================




#===========================================================================================================================
def calculate_route_intervals(trips: list[Trip], route_id: str) -> list[int]:
    """Допоміжна функція для розрахунку інтервалів (у хвилинах) між рейсами одного маршруту."""
    route_trips = [t for t in trips if t.route.route_id == route_id]
    route_trips.sort(key=lambda t: t.start_time)

    intervals = []
    for i in range(1, len(route_trips)):
        intervals.append(route_trips[i].start_time - route_trips[i-1].start_time)
    return intervals

#===========================================================================================================================
def route_intervals_table(route_id: str, trips: list[Trip]) -> str:
    """Генерує текстову таблицю інтервалів руху для заданого маршруту."""
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
    """Одразу виводить текстову таблицю інтервалів у консоль."""
    print(route_intervals_table(route_id, trips))

#===========================================================================================================================
def generate_console_report(network: Network) -> None:
    """Оформлення консольного підсумкового звіту за завантаженим фідом для Демонстрації 1."""
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