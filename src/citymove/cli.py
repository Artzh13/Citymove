import argparse
# треба заімпортити функції з інших модулів та дописати їх нижче

def create_parser() -> argparse.ArgumentParser:
    """створює та налаштовує парсер аргументів командного рядка"""

    parser = argparse.ArgumentParser(
        prog="citymove",
        description="симулятор міської транспортної мережі"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # підкоманда route
    route_parser = subparsers.add_parser(
        "route",
        help="знайти найшвидший маршрут"
        )
    route_parser.add_argument(
        "--from",
        dest="from_stop",
        required=True,
        help="початкова зупинка"
        )
    route_parser.add_argument(
        "--to",
        dest="to_stop",
        required=True,
        help="кінцева зупинка"
        )
    route_parser.add_argument(
        "--time",
        required=True,
        help="час відправлення у форматі HH:MM"
        )

    # підкоманда stats
    stats_parser = subparsers.add_parser(
        "stats",
        help="показати статистику та звіт про GTFS-фід"
        )
    stats_parser.add_argument(
        "--feed",
        required=True,
        help="шлях до zip архіву або папки з GTFS-фідом"
        )

    # підкоманда draw
    draw_parser = subparsers.add_parser(
        "draw",
        help="зберегти графічний файл із картою мережі"
        )
    draw_parser.add_argument(
        "--out",
        required=True,
        help="шлях для збереження зображення"
        )

    return parser


def handle_route(args: argparse.Namespace) -> None:
    """обробник для route"""
    print(f"Пошук шляху: {args.from_stop} -> {args.to_stop} на час {args.time}...")
    
     #використання функції друку з фейковими даними
     #потім замінити на функцію з core.py яка шукає маршрут
    fake_data = {
        "start": args.from_stop,
        "end": args.to_stop,
        "total_time": 20,
        "stops": [args.from_stop, "Проміжна зупинка", args.to_stop]
    } 
    print_route_info(fake_data)


def handle_stats(args: argparse.Namespace) -> None:
    """обробник для stats"""
    print(f"Аналіз GTFS-фіда з джерела: {args.feed}...")
    
    # використання функції друку з фейковими даними
    #потім замінити на функцію з dataio.py
    fake_stats = {
        "stops_count": 150,
        "routes_count": 12,
        "trips_count": 450
    }
    print_feed_stats(fake_stats)


def handle_draw(args: argparse.Namespace) -> None:
    """обробник для draw"""
    print(f"Генерація карти мережі у файл: {args.out}...")
    # сюди потім написати функції яка буде робити візуалізацію
    
def print_route_info(route_data: dict) -> None:
    """виводить інформацію про знайдений маршрут"""
    
    print("\n--- ЗНАЙДЕНИЙ МАРШРУТ ---")
    print(f"Початкова точка: {route_data.get('start')}")
    print(f"Кінцева точка:   {route_data.get('end')}")
    print(f"Загальний час:   {route_data.get('total_time')} хв")
    print("Список зупинок:")
    for step, stop in enumerate(route_data.get("stops", []), start=1):
        print(f"  {step}. {stop}")
    print("-------------------------\n")
    
def print_feed_stats(stats_data: dict) -> None:
    """виводить статистику GTFS"""
    
    print("\n=== СТАТИСТИКА МЕРЕЖІ ===")
    print(f"Усього зупинок:   {stats_data.get('stops_count', 0)}")
    print(f"Усього маршрутів: {stats_data.get('routes_count', 0)}")
    print(f"Усього рейсів:    {stats_data.get('trips_count', 0)}")
    print("=========================\n")    


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "route":
        handle_route(args)
    elif args.command == "stats":
        handle_stats(args)
    elif args.command == "draw":
        handle_draw(args)


if __name__ == "__main__":
    main()