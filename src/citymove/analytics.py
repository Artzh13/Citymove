from .domain import Stop, Trip, Route, StopNotFoundError, Bus

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
