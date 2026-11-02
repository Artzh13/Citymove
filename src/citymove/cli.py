import argparse
import sys
from pathlib import Path

from .core import TransportRouter, find_journey
from .dataio import load_network, validate_feed
from .domain import Network, NetworkError, StopNotFoundError
from .infra import logger, timed, log_call, load_config

# параметри за замовчуванням беремо з config.json у корені репозиторію (не залежить від поточної папки)
CONFIG = load_config(Path(__file__).resolve().parents[2] / "config.json")
DEFAULT_FEED = CONFIG.get("default_feed_path", "data/gtfs_static")
DEFAULT_PENALTY = float(CONFIG.get("transfer_penalty_min", 5))


def parse_time(value: str) -> float:
    """перетворює час 'HH:MM' на хвилини від опівночі (для argparse type=)"""
    try:
        hours, minutes = map(int, value.split(":"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"невірний формат часу '{value}', очікується HH:MM") from None
    if hours < 0 or not 0 <= minutes < 60:
        raise argparse.ArgumentTypeError(f"невірний час '{value}'")
    return float(hours * 60 + minutes)


def format_time(minutes: float) -> str:
    """хвилини від опівночі -> 'HH:MM' (години можуть бути >= 24 для рейсів після опівночі)"""
    total = int(round(minutes))
    return f"{total // 60:02d}:{total % 60:02d}"


def resolve_stop(network: Network, query: str) -> str:
    """шукає зупинку за stop_id або назвою (без урахування регістру), повертає stop_id"""
    if query in network.stops:
        return query
    matches = [s.stop_id for s in network.stops.values() if s.name.lower() == query.lower()]
    if not matches:
        raise StopNotFoundError(query)
    if len(matches) > 1:
        logger.warning(f"Назві '{query}' відповідає {len(matches)} зупинок, обрано {matches[0]}: {matches}")
    return matches[0]


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
        help="початкова зупинка (stop_id або назва)"
        )
    route_parser.add_argument(
        "--to",
        dest="to_stop",
        required=True,
        help="кінцева зупинка (stop_id або назва)"
        )
    route_parser.add_argument(
        "--time",
        required=True,
        type=parse_time,
        help="час відправлення у форматі HH:MM"
        )
    route_parser.add_argument(
        "--penalty",
        type=float,
        default=DEFAULT_PENALTY,
        help=f"штраф за пересадку у хвилинах (за замовчуванням {DEFAULT_PENALTY})"
        )

    # підкоманда stats
    stats_parser = subparsers.add_parser(
        "stats",
        help="показати статистику та звіт про GTFS-фід"
        )
    stats_parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="скільки найзв'язніших зупинок показати"
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

    # --feed спільний для всіх підкоманд
    for sub in (route_parser, stats_parser, draw_parser):
        sub.add_argument(
            "--feed",
            default=DEFAULT_FEED,
            help=f"папка з GTFS-фідом (за замовчуванням {DEFAULT_FEED})"
            )

    return parser


@timed
@log_call
def handle_route(args: argparse.Namespace) -> int:
    """обробник для route"""
    network = load_network(args.feed)
    start = resolve_stop(network, args.from_stop)
    end = resolve_stop(network, args.to_stop)
    logger.info(f"Пошук шляху: {start} -> {end} о {format_time(args.time)}")

    journey = find_journey(network, start, end, args.time, args.penalty)
    print_route_info(network, journey, args.time)
    return 0


@timed
@log_call
def handle_stats(args: argparse.Namespace) -> int:
    """обробник для stats"""
    report = validate_feed(args.feed)
    for warning in report.warnings:
        print(f"Попередження: {warning}")
    if not report.is_valid:
        for error in report.errors:
            print(f"Помилка у фіді: {error}", file=sys.stderr)
        return 1

    network = load_network(args.feed)
    metrics = TransportRouter(network).network_metrics()
    print_feed_stats(network, metrics, args.top)
    return 0


@timed
@log_call
def handle_draw(args: argparse.Namespace) -> int:
    """обробник для draw: малює зупинки й лінії маршрутів у файл"""
    import matplotlib
    matplotlib.use("Agg")  # без GUI, щоб працювало і в консолі, і в тестах
    import matplotlib.pyplot as plt

    network = load_network(args.feed)
    fig, ax = plt.subplots(figsize=(10, 10))
    for route in network.routes.values():
        points = [network.stops[s] for s in route.stops if s in network.stops]
        ax.plot([p.lon for p in points], [p.lat for p in points], linewidth=0.6, alpha=0.6)
    ax.scatter([s.lon for s in network.stops.values()], [s.lat for s in network.stops.values()],
               s=4, color="black", zorder=3)
    ax.set_title(f"Мережа: {len(network.stops)} зупинок, {len(network.routes)} маршрутів")
    ax.set_xlabel("Довгота")
    ax.set_ylabel("Широта")
    fig.savefig(args.out, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"Карту мережі збережено у файл: {args.out}")
    return 0


def print_route_info(network: Network, journey, time_0: float) -> None:
    """виводить інформацію про знайдений маршрут"""

    print("\n--- ЗНАЙДЕНИЙ МАРШРУТ ---")
    for step, (trip_id, frm, to, dep, arr) in enumerate(journey.legs, start=1):
        route = network.trips[trip_id].route
        print(f"  {step}. {route.transport.name()} №{route.short_name}: "
              f"{network.stops[frm].name} ({format_time(dep)}) -> {network.stops[to].name} ({format_time(arr)})")
    print(f"Відправлення:    {format_time(time_0)}")
    print(f"Прибуття:        {format_time(journey.arrival)}")
    print(f"Час у дорозі:    {journey.arrival - time_0:.0f} хв")
    print(f"Пересадок:       {journey.transfers}")
    print("-------------------------\n")


def print_feed_stats(network: Network, metrics: dict, top: int = 5) -> None:
    """виводить статистику GTFS та метрики мережі"""

    print("\n=== СТАТИСТИКА МЕРЕЖІ ===")
    print(f"Часова зона:      {getattr(network, 'timezone', 'UTC')}")
    print(f"Усього зупинок:   {len(network.stops)}")
    print(f"Усього маршрутів: {len(network.routes)}")
    print(f"Усього рейсів:    {len(network.trips)}")
    print(f"Діаметр мережі:   {metrics['diameter']}")
    print(f"Сер. довжина шляху: {metrics['average_path_length']:.2f} перегонів")
    centrality = sorted(metrics["degree_centrality"].items(), key=lambda kv: kv[1], reverse=True)
    print(f"Топ-{top} зупинок за зв'язністю:")
    for stop_id, value in centrality[:top]:
        print(f"  {network.stops[stop_id].name:<35} {value:.4f}")
    print("=========================\n")


HANDLERS = {"route": handle_route, "stats": handle_stats, "draw": handle_draw}


def main(argv: list[str] | None = None) -> int:
    """точка входу; повертає код завершення (0 - успіх, 1 - помилка)"""
    args = create_parser().parse_args(argv)
    try:
        return HANDLERS[args.command](args)
    except (NetworkError, OSError, ValueError) as e:
        print(f"Помилка: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
