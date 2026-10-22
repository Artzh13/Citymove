import argparse
from citymove.dataio import load_network
from citymove.infra import logger, timed, log_call
from citymove.core import TransportRouter
# треба заімпортити функції з інших модулів та дописати їх нижче

def create_parser() -> argparse.ArgumentParser:
    """створює та налаштовує парсер аргументів командного рядка"""

    parser = argparse.ArgumentParser(
        prog="citymove",
        description="СИМУЛЯТОР МІСЬКОЇ ТРАНСПОРТНОЇ МЕРЕЖІ"
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

@timed
@log_call
def handle_route(args: argparse.Namespace) -> None:
    """обробник для route"""
    logger.info(f"Пошук шляху: {args.from_stop} -> {args.to_stop} на час {args.time}...")
    
    try:
        #Завантажуємо мережу (тут можна вказати шлях до  фіда, наприклад, 'data/gtfs.zip' або додати аргумент --feed у парсер route)
        feed_path = getattr(args, "feed", "data/gtfs.zip") 
        network = load_network(feed_path)
        
        router = TransportRouter(network)
        
        # Конвертуємо час із рядка "HH:MM" у хвилини від початку доби (float)
        try:
            hours, minutes = map(int, args.time.split(":"))
            time_0 = float(hours * 60 + minutes)
        except ValueError:
            logger.error(f"Невірний формат часу: {args.time}. Використовуйте HH:MM")
            print("Помилка: невірний формат часу. Використовуйте формат HH:MM (наприклад, 09:00).")
            return

        #Викликаємо метод пошуку найкоротшого шляху
        total_time_min = router.shortest_path_from(args.from_stop, args.to_stop, time_0)
        
        print("\n--- ЗНАЙДЕНИЙ МАРШРУТ ---")
        print(f"Початкова точка: {args.from_stop}")
        print(f"Кінцева точка:   {args.to_stop}")
        print(f"Час відправлення: {args.time}")
        print(f"Загальний час у дорозі: {total_time_min - time_0:.1f} хв (прибуття о ...)")
        print("-------------------------\n")
        
    except Exception as e:
        logger.error(f"Помилка під час пошуку маршруту: {e}")
        print(f"Помилка: {e}")

@timed
@log_call
def handle_stats(args: argparse.Namespace) -> None:
    """обробник для stats"""
    logger.info(f"Аналіз GTFS-фіда з джерела: {args.feed}...")
    
    try:
        # викликаємо load_network із dataio.py для завантаження реальних даних
        network = load_network(args.feed)
        
        # Формуємо словник зі статистикою на основі завантаженої мережі
        real_stats = {
            "stops_count": len(network.stops),
            "routes_count": len(network.routes),
            "trips_count": len(network.trips)
        }
        print_feed_stats(real_stats)
    except Exception as e:
        logger.info(f"Помилка при завантаженні фіда: {e}")


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