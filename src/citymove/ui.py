"""
Модуль графічного інтерфейсу (GUI) на основі бібліотеки tkinter.

Забезпечує інтерактивне полотно для візуалізації міської транспортної мережі,
масштабування, панорамування, фільтрацію за видами транспорту та перегляд деталей зупинок.
"""

import math
import tkinter as tk
from tkinter import ttk
from typing import Any

from .domain import Network, Route, Stop

# Палітра кольорів та стилів транспорту (сучасна, контрастна)
TRANSPORT_STYLES: dict[str, dict[str, Any]] = {
    "Метро": {"color": "#e11d48", "width": 4.5, "z": 4},
    "Трамвай": {"color": "#ea580c", "width": 3.0, "z": 3},
    "Тролейбус": {"color": "#059669", "width": 2.2, "z": 2},
    "Автобус": {"color": "#2563eb", "width": 1.6, "z": 1},
}
DEFAULT_STYLE: dict[str, Any] = {"color": "#64748b", "width": 1.5, "z": 0}

CANVAS_BG: str = "#f8fafc"
STOP_OUTLINE: str = "#0f172a"
STOP_FILL: str = "#ffffff"
STOP_HUB_FILL: str = "#fef08a"
HIGHLIGHT_COLOR: str = "#d97706"
HIGHLIGHT_ROUTE_COLOR: str = "#dc2626"
LABEL_COLOR: str = "#0f172a"


class NetworkCanvas(tk.Canvas):
    """
    Інтерактивне полотно Tkinter для візуалізації транспортної мережі.

    Підтримує:
      - географічну проекцію з урахуванням кривини широти (справжні пропорції);
      - чіткі маркери станцій (великі контрастні кола) та виділення пересадкових вузлів;
      - багаторівневе відмальовування з фільтрацією видів транспорту;
      - плавне масштабування (zoom in/out);
      - панорамування (перетягування мишею);
      - швидке фокусування на центрі міста;
      - інтерактивне підсвічування зупинок та їхніх маршрутів при кліку й наведенні;
      - дедуплікацію та чітке відображення підписів зупинок.
    """

    def __init__(
        self,
        master: Any = None,
        network: Network | None = None,
        width: int = 850,
        height: int = 650,
        bg: str = CANVAS_BG,
        **kwargs: Any,
    ) -> None:
        """
        Ініціалізує полотно візуалізації мережі.

        :param master: батьківський віджет tkinter.
        :param network: об'єкт транспортної мережі для відображення.
        :param width: початкова ширина полотна в пікселях.
        :param height: початкова висота полотна в пікселях.
        :param bg: колір тла полотна.
        """
        super().__init__(master, width=width, height=height, bg=bg, **kwargs)
        self.width = width
        self.height = height
        self.network: Network | None = network

        self.padding: float = 35.0
        self.scale: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.show_labels: bool = True
        self.base_stop_radius: float = 4.5

        # Фільтр увімкнених видів транспорту
        self.enabled_transports: set[str] = {"Метро", "Трамвай", "Тролейбус", "Автобус"}

        # Вибрана та підсвічена зупинка
        self.selected_stop_id: str | None = None
        self.hovered_stop_id: str | None = None
        self.on_stop_select: Any = None
        self.on_stop_hover: Any = None

        # Кеш маршрутів для кожної зупинки: {stop_id: [Route, ...]}
        self.stop_routes: dict[str, list[Route]] = {}

        # Географічні межі мережі та коефіцієнт корекції широти
        self.min_lon: float = 0.0
        self.max_lon: float = 0.0
        self.min_lat: float = 0.0
        self.max_lat: float = 0.0
        self._cos_lat: float = 1.0
        self._base_scale: float = 1.0
        self._base_offset_x: float = 0.0
        self._base_offset_y: float = 0.0

        # Координати для перетягування мишею
        self._drag_start_x: float = 0.0
        self._drag_start_y: float = 0.0
        self._dragged: bool = False

        self._bind_events()

        if self.network is not None:
            self.set_network(self.network)

    def _bind_events(self) -> None:
        """Підключає обробники подій миші для панорамування, вибору та масштабування."""
        self.bind("<ButtonPress-1>", self._on_mouse_down)
        self.bind("<B1-Motion>", self._on_drag_motion)
        self.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.bind("<Motion>", self._on_mouse_move)
        self.bind("<MouseWheel>", self._on_mouse_wheel)
        self.bind("<Button-4>", lambda e: self.zoom(1.15, e.x, e.y))
        self.bind("<Button-5>", lambda e: self.zoom(1.0 / 1.15, e.x, e.y))
        self.bind("<Configure>", self._on_resize)

    def set_network(self, network: Network) -> None:
        """
        Встановлює нову мережу для відображення та центрує полотно.

        :param network: об'єкт Network.
        """
        self.network = network
        self.selected_stop_id = None
        self.hovered_stop_id = None

        # Будуємо мапінг зупинок до маршрутів
        self.stop_routes.clear()
        if self.network:
            for route in self.network.routes.values():
                for sid in route.stops:
                    self.stop_routes.setdefault(sid, []).append(route)

        # Для великих мереж підписи за замовчуванням вимкнені, щоб уникнути захаращення
        if network and len(network.stops) > 50:
            self.show_labels = False

        self._compute_bounds()
        self.reset_view()

    def _compute_bounds(self) -> None:
        """Обчислює крайні координати (bounding box) для зупинок мережі."""
        if not self.network or not self.network.stops:
            self.min_lon = self.max_lon = self.min_lat = self.max_lat = 0.0
            self._cos_lat = 1.0
            return

        lons = [stop.lon for stop in self.network.stops.values()]
        lats = [stop.lat for stop in self.network.stops.values()]
        self.min_lon, self.max_lon = min(lons), max(lons)
        self.min_lat, self.max_lat = min(lats), max(lats)

        mid_lat = (self.min_lat + self.max_lat) / 2.0
        self._cos_lat = max(math.cos(math.radians(mid_lat)), 0.01)

    def reset_view(self) -> None:
        """Скидає масштаб і зсув так, щоб уся мережа повністю вміщувалася на полотні."""
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        cur_w = float(self.winfo_width()) if self.winfo_width() > 1 else float(self.width)
        cur_h = float(self.winfo_height()) if self.winfo_height() > 1 else float(self.height)

        if abs(self.max_lon - self.min_lon) < 1e-9 and abs(self.max_lat - self.min_lat) < 1e-9:
            self._base_scale = 1.0
            self._base_offset_x = cur_w / 2.0
            self._base_offset_y = cur_h / 2.0
        else:
            span_x = max((self.max_lon - self.min_lon) * self._cos_lat, 1e-6)
            span_y = max(self.max_lat - self.min_lat, 1e-6)

            avail_w = max(cur_w - 2.0 * self.padding, 10.0)
            avail_h = max(cur_h - 2.0 * self.padding, 10.0)

            self._base_scale = min(avail_w / span_x, avail_h / span_y)
            self._base_offset_x = self.padding + (avail_w - span_x * self._base_scale) / 2.0
            self._base_offset_y = self.padding + (avail_h - span_y * self._base_scale) / 2.0

        self.draw_network()

    def focus_center(self) -> None:
        """
        Фокусує вигляд на центральній частині міста зі зручним збільшенням.
        Виключає далекі заміські зупинки, депонує фокус на ядрі міської активності.
        """
        if not self.network or not self.network.stops:
            return

        # Шукаємо зупинки ядра Києва (між 50.38 і 50.52 широти, 30.38 і 30.65 довготи)
        core_stops = [
            s for s in self.network.stops.values()
            if 50.36 <= s.lat <= 50.53 and 30.36 <= s.lon <= 30.66
        ]
        if not core_stops:
            core_stops = list(self.network.stops.values())

        lons = [s.lon for s in core_stops]
        lats = [s.lat for s in core_stops]
        center_lon = sum(lons) / len(lons)
        center_lat = sum(lats) / len(lats)

        # Скидаємо базовий огляд і масштабуємо у 2.4 рази до центру міста
        self.reset_view()
        cur_w = float(self.winfo_width()) if self.winfo_width() > 1 else float(self.width)
        cur_h = float(self.winfo_height()) if self.winfo_height() > 1 else float(self.height)

        target_x, target_y = self.geo_to_canvas(center_lon, center_lat)
        self.offset_x += cur_w / 2.0 - target_x
        self.offset_y += cur_h / 2.0 - target_y
        self.zoom(2.3, cur_w / 2.0, cur_h / 2.0)

    def set_transport_filter(self, enabled_types: set[str]) -> None:
        """
        Встановлює набір увімкнених видів транспорту та оновлює полотно.

        :param enabled_types: множина назв транспорту, наприклад {"Трамвай", "Тролейбус"}.
        """
        self.enabled_transports = set(enabled_types)
        self.draw_network()

    def geo_to_canvas(self, lon: float, lat: float) -> tuple[float, float]:
        """
        Перетворює географічні координати (lon, lat) у координати полотна (x, y).

        :param lon: географічна довгота.
        :param lat: географічна широта.
        :return: пара екранних координат (x, y).
        """
        cur_w = float(self.winfo_width()) if self.winfo_width() > 1 else float(self.width)
        cur_h = float(self.winfo_height()) if self.winfo_height() > 1 else float(self.height)

        base_x = (lon - self.min_lon) * self._cos_lat * self._base_scale + self._base_offset_x
        # Інвертуємо вісь Y: північ (вища широта) має бути вгорі полотна
        base_y = cur_h - ((lat - self.min_lat) * self._base_scale + self._base_offset_y)

        cx, cy = cur_w / 2.0, cur_h / 2.0
        x = (base_x - cx) * self.scale + cx + self.offset_x
        y = (base_y - cy) * self.scale + cy + self.offset_y
        return x, y

    def canvas_to_geo(self, x: float, y: float) -> tuple[float, float]:
        """
        Зворотне перетворення координат полотна (x, y) у географічні координати.

        :param x: координата x на полотні.
        :param y: координата y на полотні.
        :return: пара (lon, lat).
        """
        cur_w = float(self.winfo_width()) if self.winfo_width() > 1 else float(self.width)
        cur_h = float(self.winfo_height()) if self.winfo_height() > 1 else float(self.height)

        cx, cy = cur_w / 2.0, cur_h / 2.0
        base_x = (x - cx - self.offset_x) / self.scale + cx
        base_y = (y - cy - self.offset_y) / self.scale + cy

        lon = (base_x - self._base_offset_x) / (self._base_scale * self._cos_lat) + self.min_lon
        lat = (cur_h - base_y - self._base_offset_y) / self._base_scale + self.min_lat
        return lon, lat

    def draw_network(self) -> None:
        """Повністю перемальовує лінії маршрутів, вузли зупинок та підписи."""
        self.delete("all")
        if not self.network or not self.network.stops:
            self.create_text(
                self.width / 2.0,
                self.height / 2.0,
                text="Мережа порожня або не завантажена",
                font=("TkDefaultFont", 12),
                fill="#64748b",
                tags="empty_msg",
            )
            return

        # Визначаємо маршрути, пов'язані з вибраною зупинкою (для підсвічування)
        active_route_ids: set[str] = set()
        if self.selected_stop_id and self.selected_stop_id in self.stop_routes:
            active_route_ids = {r.route_id for r in self.stop_routes[self.selected_stop_id]}

        # 1. Сортуємо маршрути за пріоритетом шарів (Автобуси знизу, Трамваї та Метро зверху)
        sorted_routes = sorted(
            self.network.routes.values(),
            key=lambda r: TRANSPORT_STYLES.get(r.transport.name() if hasattr(r.transport, "name") else "", DEFAULT_STYLE)["z"],
        )

        # 2. Малюємо лінії маршрутів
        for route in sorted_routes:
            transport_name = route.transport.name() if hasattr(route.transport, "name") else ""
            if transport_name and transport_name not in self.enabled_transports:
                continue

            coords: list[float] = []
            for stop_id in route.stops:
                stop = self.network.stops.get(stop_id)
                if stop:
                    coords.extend(self.geo_to_canvas(stop.lon, stop.lat))

            if len(coords) >= 4:
                style = TRANSPORT_STYLES.get(transport_name, DEFAULT_STYLE)
                is_active = route.route_id in active_route_ids

                line_color = HIGHLIGHT_ROUTE_COLOR if is_active else style["color"]
                line_width = style["width"] + 2.0 if is_active else style["width"]

                self.create_line(
                    coords,
                    fill=line_color,
                    width=line_width,
                    capstyle=tk.ROUND,
                    joinstyle=tk.ROUND,
                    tags=("route", f"route_{route.route_id}"),
                )

        # 3. Динамічний розмір зупинки (зростає при наближенні)
        current_radius = max(3.5, min(8.5, self.base_stop_radius * math.sqrt(self.scale)))

        # 4. Малюємо зупинки
        visible_stops = self.network.stops.items()
        for stop_id, stop in visible_stops:
            x, y = self.geo_to_canvas(stop.lon, stop.lat)
            r = current_radius

            # Перевіряємо, чи це пересадковий вузол (кілька маршрутів)
            routes_count = len(self.stop_routes.get(stop_id, []))
            is_hub = routes_count >= 2
            is_selected = stop_id == self.selected_stop_id
            is_hovered = stop_id == self.hovered_stop_id

            if is_selected:
                r += 3.0
                fill_col = HIGHLIGHT_COLOR
                out_col = "#7c2d12"
                out_w = 2.5
            elif is_hovered:
                r += 2.0
                fill_col = "#38bdf8"
                out_col = "#0369a1"
                out_w = 2.0
            elif is_hub:
                r += 1.0
                fill_col = STOP_HUB_FILL
                out_col = STOP_OUTLINE
                out_w = 1.5
            else:
                fill_col = STOP_FILL
                out_col = STOP_OUTLINE
                out_w = 1.2

            self.create_oval(
                x - r,
                y - r,
                x + r,
                y + r,
                fill=fill_col,
                outline=out_col,
                width=out_w,
                tags=("stop", f"stop_{stop_id}"),
            )

        # 5. Підписи зупинок (з дедуплікацією за назвою для усунення перекриття)
        label_state = tk.NORMAL if self.show_labels else tk.HIDDEN
        drawn_names: set[str] = set()

        for stop_id, stop in visible_stops:
            x, y = self.geo_to_canvas(stop.lon, stop.lat)
            r = current_radius

            # Якщо підписи увімкнено, малюємо лише один підпис для зупинок з однаковою назвою
            if self.show_labels:
                if stop.name in drawn_names:
                    # Створюємо прихований підпис для збереження тегів тестування
                    self.create_text(
                        x, y, text=stop.name, state=tk.HIDDEN, tags=("stop_label", f"label_{stop_id}")
                    )
                    continue
                drawn_names.add(stop.name)

            # Тіньова підкладка для високої читабельності
            if self.show_labels:
                self.create_text(
                    x + r + 5,
                    y + 1,
                    text=stop.name,
                    anchor=tk.W,
                    font=("TkDefaultFont", 8, "bold"),
                    fill="#ffffff",
                    state=label_state,
                    tags="label_shadow",
                )

            self.create_text(
                x + r + 4,
                y,
                text=stop.name,
                anchor=tk.W,
                font=("TkDefaultFont", 8),
                fill=LABEL_COLOR,
                state=label_state,
                tags=("stop_label", f"label_{stop_id}"),
            )

    def zoom(
        self,
        factor: float,
        center_x: float | None = None,
        center_y: float | None = None,
    ) -> None:
        """
        Масштабує вміст полотна відносно заданої точки або центру.

        :param factor: коефіцієнт зміни масштабу (> 0).
        :param center_x: x-координата фокусу масштабування.
        :param center_y: y-координата фокусу масштабування.
        :raises ValueError: якщо factor <= 0.
        """
        if factor <= 0:
            raise ValueError(f"Коефіцієнт масштабування має бути додатним, отримано: {factor}")

        cur_w = float(self.winfo_width()) if self.winfo_width() > 1 else float(self.width)
        cur_h = float(self.winfo_height()) if self.winfo_height() > 1 else float(self.height)

        cx = center_x if center_x is not None else cur_w / 2.0
        cy = center_y if center_y is not None else cur_h / 2.0

        # Зсув для фокусування зуму на точці (cx, cy)
        self.offset_x = (self.offset_x + cur_w / 2.0 - cx) * factor + cx - cur_w / 2.0
        self.offset_y = (self.offset_y + cur_h / 2.0 - cy) * factor + cy - cur_h / 2.0
        self.scale *= factor

        self.draw_network()

    def zoom_in(self) -> None:
        """Збільшує масштаб на 25%."""
        self.zoom(1.25)

    def zoom_out(self) -> None:
        """Зменшує масштаб на 25%."""
        self.zoom(1.0 / 1.25)

    def pan(self, dx: float, dy: float) -> None:
        """
        Зсуває область перегляду полотна на (dx, dy).

        :param dx: зміщення по горизонталі в пікселях.
        :param dy: зміщення по вертикалі в пікселях.
        """
        self.offset_x += dx
        self.offset_y += dy
        self.draw_network()

    def toggle_labels(self, visible: bool | None = None) -> bool:
        """
        Перемикає видимість текстових підписів зупинок на полотні.

        :param visible: явний стан (True/False). Якщо None, стан інвертується.
        :return: новий стан видимості підписів.
        """
        if visible is None:
            self.show_labels = not self.show_labels
        else:
            self.show_labels = visible

        self.draw_network()
        return self.show_labels

    def _find_stop_at(self, x: float, y: float, tolerance: float = 7.0) -> Stop | None:
        """Шукає зупинку поблизу координат (x, y) полотна."""
        if not self.network:
            return None
        items = self.find_overlapping(x - tolerance, y - tolerance, x + tolerance, y + tolerance)
        for item in items:
            for tag in self.gettags(item):
                if tag.startswith("stop_"):
                    sid = tag[5:]
                    return self.network.stops.get(sid)
        return None

    def _on_mouse_down(self, event: tk.Event) -> None:
        self._drag_start_x = float(event.x)
        self._drag_start_y = float(event.y)
        self._dragged = False

    def _on_drag_motion(self, event: tk.Event) -> None:
        dx = float(event.x) - self._drag_start_x
        dy = float(event.y) - self._drag_start_y
        if abs(dx) > 2 or abs(dy) > 2:
            self._dragged = True
            self._drag_start_x = float(event.x)
            self._drag_start_y = float(event.y)
            self.pan(dx, dy)

    def _on_mouse_up(self, event: tk.Event) -> None:
        # Якщо був чистий клік без перетягування — вибираємо зупинку
        if not self._dragged:
            clicked_stop = self._find_stop_at(float(event.x), float(event.y))
            if clicked_stop:
                self.selected_stop_id = clicked_stop.stop_id
                if callable(self.on_stop_select):
                    self.on_stop_select(clicked_stop)
                self.draw_network()
            elif self.selected_stop_id is not None:
                self.selected_stop_id = None
                if callable(self.on_stop_select):
                    self.on_stop_select(None)
                self.draw_network()

    def _on_mouse_move(self, event: tk.Event) -> None:
        hovered = self._find_stop_at(float(event.x), float(event.y))
        new_hover_id = hovered.stop_id if hovered else None
        if new_hover_id != self.hovered_stop_id:
            self.hovered_stop_id = new_hover_id
            if callable(self.on_stop_hover):
                self.on_stop_hover(hovered)
            # При наведенні оновлюємо курсор
            self.config(cursor="hand2" if hovered else "")

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        if event.delta > 0:
            self.zoom(1.15, float(event.x), float(event.y))
        elif event.delta < 0:
            self.zoom(1.0 / 1.15, float(event.x), float(event.y))

    def _on_resize(self, event: tk.Event) -> None:
        if event.width > 1 and event.height > 1:
            self.width = event.width
            self.height = event.height
            self.draw_network()


class MainWindow(tk.Tk):
    """Головне графічне вікно застосунку CityMove."""

    def __init__(self, network: Network | None = None) -> None:
        super().__init__()
        self.title("CityMove — Карта міської транспортної мережі")
        self.geometry("1050x720")
        self.minsize(750, 480)

        # Контейнер для полотна та бічної панелі деталей
        main_container = ttk.Frame(self)
        self.canvas = NetworkCanvas(main_container, network=network)
        self.canvas.on_stop_hover = self._on_stop_hover
        self.canvas.on_stop_select = self._on_stop_select

        self._create_toolbar()
        main_container.pack(fill=tk.BOTH, expand=True)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._create_side_panel(main_container)
        self._create_statusbar()

    def _create_toolbar(self) -> None:
        toolbar = ttk.Frame(self, padding=6)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Навігаційні кнопки
        btn_in = ttk.Button(toolbar, text="➕ Збільшити", command=self.canvas.zoom_in)
        btn_in.pack(side=tk.LEFT, padx=2)

        btn_out = ttk.Button(toolbar, text="➖ Зменшити", command=self.canvas.zoom_out)
        btn_out.pack(side=tk.LEFT, padx=2)

        btn_center = ttk.Button(toolbar, text="🎯 Центр міста", command=self.canvas.focus_center)
        btn_center.pack(side=tk.LEFT, padx=4)

        btn_reset = ttk.Button(toolbar, text="⌂ Вся мережа", command=self.canvas.reset_view)
        btn_reset.pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Фільтри видів транспорту
        self._filter_vars: dict[str, tk.BooleanVar] = {}
        transport_icons = {"Трамвай": "🚋 Трамваї", "Тролейбус": "🚎 Тролейбуси", "Автобус": "🚌 Автобуси"}

        for t_name, label in transport_icons.items():
            var = tk.BooleanVar(value=True)
            self._filter_vars[t_name] = var
            cb = ttk.Checkbutton(toolbar, text=label, variable=var, command=self._apply_filters)
            cb.pack(side=tk.LEFT, padx=4)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        # Підписи зупинок
        self._labels_var = tk.BooleanVar(value=self.canvas.show_labels)
        btn_labels = ttk.Checkbutton(
            toolbar,
            text="🏷️ Підписи",
            variable=self._labels_var,
            command=lambda: self.canvas.toggle_labels(self._labels_var.get()),
        )
        btn_labels.pack(side=tk.LEFT, padx=4)

    def _apply_filters(self) -> None:
        """Передає активні фільтри транспорту на полотно."""
        active = {t for t, var in self._filter_vars.items() if var.get()}
        active.add("Метро")
        self.canvas.set_transport_filter(active)

    def _create_side_panel(self, parent: ttk.Frame) -> None:
        """Створює бічну панель із деталями вибраної зупинки та легендою."""
        self.side_panel = ttk.Frame(parent, width=240, padding=10)
        self.side_panel.pack(side=tk.RIGHT, fill=tk.Y)

        title = ttk.Label(self.side_panel, text="Деталі зупинки", font=("TkDefaultFont", 11, "bold"))
        title.pack(anchor=tk.W, pady=(0, 6))

        self.info_text = tk.Text(
            self.side_panel,
            width=28,
            height=12,
            wrap=tk.WORD,
            font=("TkDefaultFont", 9),
            relief=tk.FLAT,
            bg="#f1f5f9",
            padx=8,
            pady=8,
        )
        self.info_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.info_text.insert(
            tk.END,
            "💡 Натисніть на будь-яку точку зупинки на карті, щоб переглянути всі маршрути через неї."
        )
        self.info_text.config(state=tk.DISABLED)

        # Легенда
        legend_frame = ttk.LabelFrame(self.side_panel, text="Легенда транспорту", padding=8)
        legend_frame.pack(fill=tk.X, side=tk.BOTTOM)

        for name, style in TRANSPORT_STYLES.items():
            row = ttk.Frame(legend_frame)
            row.pack(fill=tk.X, pady=2)
            color_box = tk.Canvas(row, width=16, height=12, bg=style["color"], highlightthickness=0)
            color_box.pack(side=tk.LEFT, padx=(0, 6))
            ttk.Label(row, text=name, font=("TkDefaultFont", 9)).pack(side=tk.LEFT)

    def _create_statusbar(self) -> None:
        self.status = ttk.Label(
            self,
            text="",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=4,
        )
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        self._show_default_status()

    def _show_default_status(self) -> None:
        stops_count = len(self.canvas.network.stops) if self.canvas.network else 0
        routes_count = len(self.canvas.network.routes) if self.canvas.network else 0
        self.status.config(
            text=f"Зупинок: {stops_count} | Маршрутів: {routes_count} | 💡 Клікніть на зупинку для перегляду маршрутів"
        )

    def _on_stop_hover(self, stop: Stop | None) -> None:
        if stop:
            routes = self.canvas.stop_routes.get(stop.stop_id, [])
            routes_str = ", ".join(sorted({r.short_name for r in routes})) or "немає даних"
            self.status.config(
                text=f"🚏 {stop.name} (ID: {stop.stop_id}) | Маршрути: {routes_str}"
            )
        else:
            self._show_default_status()

    def _on_stop_select(self, stop: Stop | None) -> None:
        """Оновлює бічну інформаційну панель при виборі зупинки."""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)

        if not stop:
            self.info_text.insert(
                tk.END,
                "💡 Натисніть на будь-яку точку зупинки на карті, щоб переглянути всі маршрути через неї."
            )
        else:
            routes = self.canvas.stop_routes.get(stop.stop_id, [])
            lines_by_type: dict[str, list[str]] = {}
            for r in routes:
                t_name = r.transport.name() if hasattr(r.transport, "name") else "Інше"
                lines_by_type.setdefault(t_name, []).append(r.short_name)

            content = [
                f"🚏 {stop.name}\n",
                f"ID: {stop.stop_id}\n",
                f"Координати:\n  {stop.lat:.4f}, {stop.lon:.4f}\n\n",
                f"Маршрути ({len(routes)}):\n",
            ]
            if not lines_by_type:
                content.append("  (немає рейсів)\n")
            else:
                for t_name, nums in lines_by_type.items():
                    sorted_nums = sorted(set(nums), key=lambda x: (len(x), x))
                    content.append(f"• {t_name}и:\n   {', '.join(sorted_nums)}\n")

            self.info_text.insert(tk.END, "".join(content))

        self.info_text.config(state=tk.DISABLED)


def run_gui(network: Network | None = None) -> None:
    """Запускає головне вікно графічного інтерфейсу."""
    app = MainWindow(network=network)
    app.mainloop()
