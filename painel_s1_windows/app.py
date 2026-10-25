import json
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pystray
from PIL import Image, ImageDraw

from biblioteca import ImageLibrary, ImageLibraryEntry
from dispositivo_hid import find_panel_interfaces
from enviar_teste import PanelWriter
from metricas import WindowsMetrics
from protocolo import HID_REPORT_BYTES, build_test_frame
from renderizar import (
    IMAGE_LAYOUT_CODES,
    IMAGE_LAYOUTS,
    ImagePixels,
    orient_frame_for_preview,
    prepare_image_pixels,
    prepare_render_background,
    render_frame,
)


SCREEN_WIDTH = 320
SCREEN_HEIGHT = 170
REFRESH_MS = 800
METRICS_RETRY_MS = 5000
SLIDESHOW_INTERVAL_OPTIONS = (10, 15, 20, 30, 45, 60, 90, 120, 180, 300)
HEARTBEAT_INTERVAL_MS = 1_600
IMAGE_SUFFIXES = {".gif", ".png", ".jpg", ".jpeg"}
ORIENTATION_LABELS = {"Deitada": "landscape", "Em pé": "portrait"}
METRIC_LABELS = {
    "cpu": "CPU",
    "memory": "RAM",
    "clock": "Relógio e data",
    "uptime": "Tempo ligado",
    "disk": "Espaço em disco",
}
METRIC_BOUNDS = {
    "cpu": (145, 26),
    "memory": (145, 26),
    "clock": (72, 40),
    "uptime": (145, 16),
    "disk": (145, 16),
}
ANCHOR_LABELS = (
    "Superior esquerdo",
    "Superior centro",
    "Superior direito",
    "Centro esquerdo",
    "Centro",
    "Centro direito",
    "Inferior esquerdo",
    "Inferior centro",
    "Inferior direito",
)
METRIC_SCALES = {"Normal": 2, "Grande": 3, "Extra grande": 4}
PREVIEW_METRICS = {
    "cpu_percent": 65.0,
    "memory_percent": 20.0,
    "uptime_seconds": 2 * 24 * 60 * 60 + 3 * 60 * 60,
    "disk_free_gb": 120.0,
    "disk_total_gb": 500.0,
}
PREVIEW_TIME = datetime(2025, 1, 1, 12, 34)


def format_uptime(seconds: int) -> str:
    days, remainder = divmod(seconds, 24 * 60 * 60)
    hours, remainder = divmod(remainder, 60 * 60)
    minutes, _ = divmod(remainder, 60)
    return f"{days} d  {hours:02} h  {minutes:02} min"


class S1PanelApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Painel S1 local")
        self.root.geometry("900x700")
        self.root.minsize(620, 450)
        self.root.configure(bg="#171717")
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self.root.bind("<Unmap>", self._minimize_to_tray)
        self.tray_icon: pystray.Icon | None = None
        self.tray_actions: queue.Queue[str] = queue.Queue()
        self.tray_poll_id: str | None = None

        try:
            self.image_library = ImageLibrary(Path(__file__).resolve().parent)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Biblioteca de imagens indisponível",
                f"Não foi possível preparar a biblioteca local:\n{error}",
                parent=self.root,
            )
            raise
        self.metrics = WindowsMetrics()
        self.panel_writer: PanelWriter | None = None
        self.latest_metrics: dict[str, float | int | None] = {
            "cpu_percent": None,
            "memory_percent": 0.0,
            "memory_used_gb": 0.0,
            "memory_total_gb": 0.0,
            "uptime_seconds": 0,
            "disk_free_gb": 0.0,
            "disk_total_gb": 0.0,
        }
        self.metrics_available = False
        self.background_image: ImagePixels | None = None
        self.background_pixels: bytes | None = None
        self.displayed_background_pixels: bytes | None = None
        self.pending_background_pixels: bytes | None = None
        self.displayed_frame: bytes | None = None
        self.pending_frame: bytes | None = None
        self.pending_metric_frame: bytes | None = None
        self.background_path: Path | None = None
        self.current_preview_path: Path | None = None
        self.active_library_entry: ImageLibraryEntry | None = None
        self.last_image_path: Path | None = None
        self.last_folder_path: Path | None = None
        self.last_image_entry: ImageLibraryEntry | None = None
        self.last_folder_entry: ImageLibraryEntry | None = None
        self.folder_images: list[Path] = []
        self.folder_index = 0
        self.preparation_results: queue.Queue[tuple[str, object]] = queue.Queue()
        self.preparation_running = False
        self.pending_preparation: (
            tuple[str, list[Path], ImageLibraryEntry, int] | None
        ) = None
        self.library_status = tk.StringVar(value="")
        self.mode = tk.StringVar(value="fixed")
        self.image_layout = tk.StringVar(value=IMAGE_LAYOUTS[0])
        self.orientation = tk.StringVar(value="Deitada")
        self.slideshow_interval = tk.StringVar(value="30")
        self.metric_sizes = {metric: "Normal" for metric in METRIC_LABELS}
        self.metric_positions = {
            "cpu": (12, 39),
            "memory": (12, 75),
            "clock": (196, 43),
            "uptime": (12, 127),
            "disk": (196, 127),
        }
        self.visible_metrics = set(METRIC_LABELS)
        self.drag_metric: str | None = None
        self.drag_offset = (0, 0)
        self.send_results: queue.Queue[tuple[str, str]] = queue.Queue()
        self.device_compatible = False
        self.selection_controls: list[ttk.Widget] = []
        self.sending = False
        self.metrics_update_running = False
        self.auto_running = False
        self.metrics_refresh_id: str | None = None
        self.render_background_source: bytes | None = None
        self.render_background_orientation: str | None = None
        self.render_background_cache: bytes | None = None
        self.image_apply_pending = False
        self.frame_count = 0
        self.last_frame_started = 0.0
        self.next_update_at: float | None = None
        self.next_update_id: str | None = None
        self.countdown_id: str | None = None
        self.heartbeat_id: str | None = None
        self.heartbeat_running = False

        self._configure_theme()
        self._build_ui()
        self._start_tray_icon()
        self.tray_poll_id = self.root.after(100, self._poll_tray_actions)
        self._load_layout_settings()
        self._refresh_library_view()
        self._check_panel()
        self._restore_last_selection()
        self._draw_preview()
        self._refresh_metrics()
        self.root.after(100, self._poll_send_results)

    def _configure_theme(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(
            ".",
            background="#171717",
            foreground="#eeeeee",
            font=("Segoe UI", 10),
        )
        style.configure("TFrame", background="#171717")
        style.configure("TLabel", background="#171717", foreground="#eeeeee")
        style.configure(
            "Muted.TLabel",
            background="#171717",
            foreground="#aaaaaa",
            font=("Segoe UI", 9),
        )
        style.configure(
            "TButton",
            background="#292929",
            foreground="#eeeeee",
            padding=(10, 6),
        )
        style.configure(
            "TRadiobutton",
            background="#171717",
            foreground="#eeeeee",
        )
        style.configure(
            "Library.Treeview",
            background="#242424",
            fieldbackground="#242424",
            foreground="#f2f2f2",
            rowheight=30,
        )
        style.map(
            "Library.Treeview",
            background=[("selected", "#176b87")],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "Library.Treeview.Heading",
            background="#353535",
            foreground="#ffffff",
            font=("Segoe UI", 9, "bold"),
        )

    def _build_ui(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        self.panel_tab = ttk.Frame(self.notebook)
        self.library_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.panel_tab, text="Painel")
        self.notebook.add(self.library_tab, text="Biblioteca")

        viewport = ttk.Frame(self.panel_tab)
        viewport.pack(fill="both", expand=True)
        self.content_canvas = tk.Canvas(
            viewport,
            bg="#171717",
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(
            viewport,
            orient="vertical",
            command=self.content_canvas.yview,
        )
        self.content_canvas.configure(yscrollcommand=scrollbar.set)
        self.content_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        outer = ttk.Frame(self.content_canvas, padding=18)
        self.content_window = self.content_canvas.create_window(
            (0, 0),
            window=outer,
            anchor="nw",
        )
        outer.bind("<Configure>", self._update_scroll_region)
        self.content_canvas.bind("<Configure>", self._resize_scroll_content)
        self.root.bind_all("<MouseWheel>", self._scroll_content)
        ttk.Label(
            outer,
            text="Painel S1 local",
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Prévia demonstrativa e envio controlado à tela física. "
                "Não instala nem altera drivers."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(3, 12))

        preview_frame = ttk.Frame(outer)
        preview_frame.pack(fill="x")
        self.canvas = tk.Canvas(
            preview_frame,
            width=SCREEN_WIDTH,
            height=SCREEN_HEIGHT,
            bg="#070d17",
            highlightthickness=1,
            highlightbackground="#555555",
        )
        self.canvas.pack(side="left", anchor="n")

        controls = ttk.Frame(preview_frame, padding=(15, 0, 0, 0))
        controls.pack(side="left", fill="both", expand=True)
        fixed_mode = ttk.Radiobutton(
            controls,
            text="Imagem fixa",
            variable=self.mode,
            value="fixed",
            command=self._mode_changed,
        )
        fixed_mode.pack(anchor="w")
        self.selection_controls.append(fixed_mode)
        choose_image = ttk.Button(
            controls,
            text="Escolher imagem...",
            command=self._choose_background,
        )
        choose_image.pack(anchor="w", pady=(3, 10))
        self.choose_image_button = choose_image
        ttk.Label(controls, text="Ajuste da imagem", style="Muted.TLabel").pack(
            anchor="w"
        )
        self.image_layout_combo = ttk.Combobox(
            controls,
            textvariable=self.image_layout,
            values=IMAGE_LAYOUTS,
            state="readonly",
            width=18,
        )
        self.image_layout_combo.pack(anchor="w", pady=(3, 10))
        self.image_layout_combo.bind(
            "<<ComboboxSelected>>",
            self._image_layout_changed,
        )
        ttk.Label(controls, text="Orientação da tela", style="Muted.TLabel").pack(
            anchor="w"
        )
        self.orientation_combo = ttk.Combobox(
            controls,
            textvariable=self.orientation,
            values=tuple(ORIENTATION_LABELS),
            state="readonly",
            width=18,
        )
        self.orientation_combo.pack(anchor="w", pady=(3, 7))
        self.orientation_combo.bind(
            "<<ComboboxSelected>>",
            self._orientation_changed,
        )
        self.customize_button = ttk.Button(
            controls,
            text="Personalizar informações...",
            command=self._customize_metrics,
        )
        self.customize_button.pack(anchor="w", pady=(0, 10))
        ttk.Label(controls, text="Intervalo das imagens da pasta", style="Muted.TLabel").pack(
            anchor="w"
        )
        self.slideshow_interval_combo = ttk.Combobox(
            controls,
            textvariable=self.slideshow_interval,
            values=tuple(str(seconds) for seconds in SLIDESHOW_INTERVAL_OPTIONS),
            state="readonly",
            width=18,
        )
        self.slideshow_interval_combo.pack(anchor="w", pady=(3, 10))
        self.slideshow_interval_combo.bind(
            "<<ComboboxSelected>>",
            self._slideshow_interval_changed,
        )
        ttk.Label(
            controls,
            text="Você também pode arrastar os itens na prévia.",
            style="Muted.TLabel",
            wraplength=230,
        ).pack(anchor="w", pady=(0, 10))
        folder_mode = ttk.Radiobutton(
            controls,
            text="Alternar imagens de uma pasta",
            variable=self.mode,
            value="folder",
            command=self._mode_changed,
        )
        folder_mode.pack(anchor="w")
        self.selection_controls.append(folder_mode)
        choose_folder = ttk.Button(
            controls,
            text="Escolher pasta...",
            command=self._choose_folder,
        )
        choose_folder.pack(anchor="w", pady=(3, 10))
        self.selection_controls.append(choose_folder)
        ttk.Label(
            controls,
            textvariable=self._image_selection_text(),
            style="Muted.TLabel",
            wraplength=340,
            justify="left",
        ).pack(anchor="w", pady=(0, 7))
        ttk.Label(
            controls,
            text=(
                "A pasta percorre PNG, GIF e JPEG em ordem alfabética e repete. "
                "A prévia mostra a orientação e o ajuste escolhidos."
            ),
            style="Muted.TLabel",
            wraplength=340,
            justify="left",
        ).pack(anchor="w")

        ttk.Label(
            outer,
            text="Prévia demonstrativa",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(15, 5))
        ttk.Label(
            outer,
            text=(
                "Os valores da prévia são fixos e apenas ilustrativos "
                "(CPU 65%, RAM 20%). As métricas reais são enviadas somente "
                "à tela física durante a atualização contínua."
            ),
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w")

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(12, 7))
        self.diagnostic_button = ttk.Button(
            actions,
            text="Teste visual S1 TEST",
            command=self._send_diagnostic_frame,
            state="disabled",
        )
        self.diagnostic_button.pack(side="left", padx=(8, 0))
        self.start_button = ttk.Button(
            actions,
            text="Iniciar atualização contínua",
            command=self._start_automatic,
            state="disabled",
        )
        self.start_button.pack(side="left", padx=(8, 0))
        self.stop_button = ttk.Button(
            actions,
            text="Parar",
            command=self._stop_automatic,
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=(8, 0))

        self.device_status = ttk.Label(
            outer,
            text="Verificando a interface USB 04D9:FD01...",
            style="Muted.TLabel",
            wraplength=760,
        )
        self.device_status.pack(anchor="w", pady=(3, 3))
        self.run_status = ttk.Label(
            outer,
            text="Atualizações automáticas só começam depois de você clicar em Iniciar.",
            style="Muted.TLabel",
            wraplength=760,
        )
        self.run_status.pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "CPU/RAM são atualizadas na tela física a cada 0,8 s no modo "
                "contínuo. O intervalo das "
                "imagens da pasta é configurável. "
                "Cada quadro leva cerca de 9 s. Temperatura e RPM da ventoinha "
                "não estão disponíveis pelas interfaces padrão deste PC."
            ),
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(8, 0))
        self._build_library_tab()

    def _build_library_tab(self) -> None:
        content = ttk.Frame(self.library_tab, padding=18)
        content.pack(fill="both", expand=True)
        ttk.Label(
            content,
            text="Imagens e pastas usadas anteriormente",
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            content,
            text=(
                "Os originais nunca são alterados. As cópias prontas para a "
                "telinha ficam na pasta “Imagens preparadas”, ao lado do app."
            ),
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(4, 12))
        columns = ("kind", "location")
        self.library_tree = ttk.Treeview(
            content,
            columns=columns,
            show="tree headings",
            selectmode="browse",
            height=14,
            style="Library.Treeview",
            takefocus=True,
        )
        self.library_tree.heading("#0", text="Nome original")
        self.library_tree.heading("kind", text="Tipo")
        self.library_tree.heading("location", text="Localização original")
        self.library_tree.column("#0", width=210, stretch=False)
        self.library_tree.column("kind", width=90, stretch=False)
        self.library_tree.column("location", width=520, stretch=True)
        tree_scrollbar = ttk.Scrollbar(
            content,
            orient="vertical",
            command=self.library_tree.yview,
        )
        self.library_tree.configure(yscrollcommand=tree_scrollbar.set)
        self.library_tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")
        self.library_tree.bind(
            "<Double-1>",
            lambda _event: self._use_library_selection(),
        )
        self.library_tree.bind(
            "<<TreeviewSelect>>",
            self._library_selection_changed,
        )
        actions = ttk.Frame(content)
        actions.pack(fill="x", pady=(10, 0))
        self.library_use_button = ttk.Button(
            actions,
            text="Usar selecionado",
            command=self._use_library_selection,
        )
        self.library_use_button.pack(side="left")
        self.library_remove_button = ttk.Button(
            actions,
            text="Remover da biblioteca...",
            command=self._remove_library_selection,
        )
        self.library_remove_button.pack(side="left", padx=(8, 0))
        self.library_progress = ttk.Progressbar(
            content,
            mode="determinate",
            maximum=1,
        )
        self.library_progress.pack(fill="x", pady=(12, 3))
        ttk.Label(
            content,
            textvariable=self.library_status,
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w")

    def _update_scroll_region(self, _event: tk.Event) -> None:
        self.content_canvas.configure(
            scrollregion=self.content_canvas.bbox("all")
        )

    def _resize_scroll_content(self, event: tk.Event) -> None:
        self.content_canvas.itemconfigure(self.content_window, width=event.width)

    def _scroll_content(self, event: tk.Event) -> str:
        if self.notebook.select() != str(self.panel_tab):
            return "break"
        bounds = self.content_canvas.bbox("all")
        if bounds is None or self.content_canvas.winfo_height() >= bounds[3]:
            return "break"
        self.content_canvas.yview_scroll(-int(event.delta / 120), "units")
        return "break"

    def _image_selection_text(self) -> tk.StringVar:
        self.image_selection = tk.StringVar(value="Nenhuma imagem selecionada.")
        return self.image_selection

    def _check_panel(self) -> None:
        try:
            interfaces = find_panel_interfaces()
        except (OSError, RuntimeError) as error:
            self.device_status.configure(
                text=f"Não foi possível consultar a interface HID: {error}"
            )
            return

        compatible = [
            interface
            for interface in interfaces
            if interface.output_report_bytes == HID_REPORT_BYTES
        ]
        capacities = [
            str(interface.output_report_bytes)
            for interface in interfaces
            if interface.output_report_bytes is not None
        ]
        if len(compatible) != 1:
            self.device_status.configure(
                text=(
                    "Não foi encontrado exatamente um canal HID de saída compatível "
                    "com o painel. Nenhum quadro será enviado."
                )
            )
            return

        self.device_compatible = True
        self.device_status.configure(
            text=(
                "Painel 04D9:FD01 encontrado; relatório HID de 4105 bytes "
                f"confirmado (capacidades: {', '.join(capacities)}). "
                "O teste anterior mostrou que o envio chegou à tela."
            )
        )
        self._update_controls()

    def _mode_changed(self) -> None:
        if self.preparation_running:
            return
        if self.mode.get() == "fixed" and self.last_image_path is not None:
            if self.background_path != self.last_image_path:
                self._select_image_path(self.last_image_path)
                return
        if self.mode.get() == "folder" and self.last_folder_path is not None:
            if (
                self.active_library_entry is None
                or self.active_library_entry["path"]
                != str(self.last_folder_path.resolve())
            ):
                self._select_folder_path(self.last_folder_path)
                return
        self._update_image_label()
        self._draw_preview()
        self._update_controls()
        self._save_layout_settings()

    def _library_selection_changed(self, _event: tk.Event | None = None) -> None:
        selection = self.library_tree.selection()
        if not selection:
            return
        entry = self.library_rows.get(selection[0])
        if entry is not None:
            self.library_status.set(
                f"Selecionado: {entry['name']} — use “Usar selecionado” "
                "ou “Remover da biblioteca”."
            )

    def _image_layout_changed(self, _event: tk.Event | None = None) -> None:
        if (
            self.mode.get() == "folder"
            and self.folder_images
            and self.active_library_entry is not None
        ):
            self._save_layout_settings()
            self._begin_image_preparation(
                "folder",
                self.folder_images,
                self.active_library_entry,
                self.folder_index,
            )
            return
        try:
            pixels = self._prepare_background(self.background_image)
        except (OSError, tk.TclError, ValueError) as error:
            messagebox.showerror(
                "Não foi possível ajustar a imagem",
                f"A imagem não pôde ser preparada:\n{error}",
                parent=self.root,
            )
            return
        self.background_pixels = pixels
        self._draw_preview()
        self._save_layout_settings()
        if self.auto_running and self.background_path is not None:
            self._queue_background_send()

    def _selected_orientation(self) -> str:
        try:
            return ORIENTATION_LABELS[self.orientation.get()]
        except KeyError:
            raise ValueError(
                f"Orientação não reconhecida: {self.orientation.get()}"
            ) from None

    def _selected_metric_scale(self, metric: str) -> int:
        try:
            scale = METRIC_SCALES[self.metric_sizes[metric]]
        except KeyError:
            raise ValueError(
                f"Tamanho da informação não reconhecido: {metric}"
            ) from None
        if self._selected_orientation() == "portrait":
            return min(scale, 3)
        return scale

    def _metric_bounds(self, metric: str) -> tuple[int, int]:
        base_width, base_height = METRIC_BOUNDS[metric]
        scale = self._selected_metric_scale(metric)
        return (
            base_width * scale // 2,
            base_height * scale // 2,
        )

    def _selected_slideshow_interval_ms(self) -> int:
        try:
            seconds = int(self.slideshow_interval.get())
        except ValueError:
            raise ValueError(
                f"Intervalo de imagens inválido: {self.slideshow_interval.get()}"
            ) from None
        if seconds not in SLIDESHOW_INTERVAL_OPTIONS:
            raise ValueError(f"Intervalo de imagens não permitido: {seconds}")
        return seconds * 1000

    def _slideshow_interval_changed(self, _event: tk.Event | None = None) -> None:
        try:
            self._selected_slideshow_interval_ms()
        except ValueError as error:
            messagebox.showerror(
                "Intervalo inválido",
                str(error),
                parent=self.root,
            )
            return
        self._save_layout_settings()


    def _orientation_changed(self, _event: tk.Event | None = None) -> None:
        orientation = self._selected_orientation()
        self._reset_metric_positions(orientation)
        if (
            self.mode.get() == "folder"
            and self.folder_images
            and self.active_library_entry is not None
        ):
            self._save_layout_settings()
            self._begin_image_preparation(
                "folder",
                self.folder_images,
                self.active_library_entry,
                self.folder_index,
            )
            return
        try:
            pixels = self._prepare_background(self.background_image)
        except (OSError, tk.TclError, ValueError) as error:
            messagebox.showerror(
                "Não foi possível mudar a orientação",
                f"A imagem não pôde ser preparada:\n{error}",
                parent=self.root,
            )
            return
        self.background_pixels = pixels
        self._draw_preview()
        if self.auto_running:
            self._queue_background_send()
        self._save_layout_settings()

    def _prepare_background(
        self,
        image: ImagePixels | None,
    ) -> bytes | None:
        if self.background_path is not None and self.active_library_entry is not None:
            prepared = self.image_library.prepare_image(
                self.active_library_entry,
                self.background_path,
                self.image_layout.get(),
                self._selected_orientation(),
            )
            self.current_preview_path = prepared.preview_path
            return prepared.pixels
        if image is None:
            return None
        layout = IMAGE_LAYOUT_CODES[self.image_layout.get()]
        return prepare_image_pixels(image, layout, self._selected_orientation())

    def _photo_from_rgb565(
        self,
        pixels: bytes,
        width: int = SCREEN_WIDTH,
        height: int = SCREEN_HEIGHT,
    ) -> tk.PhotoImage:
        photo = tk.PhotoImage(
            master=self.root,
            width=width,
            height=height,
        )
        for y in range(height):
            row = []
            for x in range(width):
                offset = (y * width + x) * 2
                value = int.from_bytes(pixels[offset : offset + 2], "big")
                red = ((value >> 11) & 0x1F) * 255 // 31
                green = ((value >> 5) & 0x3F) * 255 // 63
                blue = (value & 0x1F) * 255 // 31
                row.append(f"#{red:02x}{green:02x}{blue:02x}")
            photo.put("{" + " ".join(row) + "}", to=(0, y))
        return photo

    def _queue_background_send(self) -> None:
        if not self.auto_running:
            return
        self._cancel_scheduled_update()
        self._cancel_countdown()
        self.next_update_at = None
        self.image_apply_pending = True
        self.run_status.configure(text="Aplicando a imagem ajustada ao painel...")
        if not self.metrics_update_running:
            self.image_apply_pending = False
            self._begin_send()

    def _choose_background(self) -> None:
        filename = filedialog.askopenfilename(
            parent=self.root,
            title="Escolher imagem de fundo",
            filetypes=[
                ("Imagens PNG, GIF e JPEG", "*.png *.gif *.jpg *.jpeg"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not filename:
            return
        self._select_image_path(Path(filename))

    def _choose_folder(self) -> None:
        folder_name = filedialog.askdirectory(
            parent=self.root,
            title="Escolher pasta de imagens",
        )
        if not folder_name:
            return

        try:
            paths = sorted(
                (
                    path
                    for path in Path(folder_name).iterdir()
                    if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
                ),
                key=lambda path: path.name.casefold(),
            )
        except OSError as error:
            messagebox.showerror(
                "Não foi possível ler a pasta",
                f"A pasta de imagens não pôde ser lida:\n{error}",
                parent=self.root,
            )
            return
        if not paths:
            messagebox.showerror(
                "Pasta sem imagens",
                "Escolha uma pasta com pelo menos uma imagem PNG, GIF ou JPEG "
                "(.jpg/.jpeg).",
                parent=self.root,
            )
            return
        self._select_folder_path(Path(folder_name), paths)

    def _select_image_path(self, path: Path) -> None:
        if not path.is_file():
            messagebox.showerror(
                "Imagem não encontrada",
                f"O arquivo não existe mais:\n{path}",
                parent=self.root,
            )
            self._refresh_library_view()
            return
        try:
            entry = self.image_library.add("image", path)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Não foi possível salvar na biblioteca",
                str(error),
                parent=self.root,
            )
            return
        self.last_image_path = path.resolve()
        self.last_image_entry = entry
        self.mode.set("fixed")
        self._save_layout_settings()
        self._refresh_library_view()
        self._begin_image_preparation("image", [path], entry)

    def _select_folder_path(
        self,
        folder: Path,
        paths: list[Path] | None = None,
    ) -> None:
        try:
            image_paths = paths or sorted(
                (
                    path
                    for path in folder.iterdir()
                    if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
                ),
                key=lambda path: path.name.casefold(),
            )
        except OSError as error:
            messagebox.showerror(
                "Não foi possível ler a pasta",
                f"A pasta de imagens não pôde ser lida:\n{error}",
                parent=self.root,
            )
            return
        if not image_paths:
            messagebox.showerror(
                "Pasta sem imagens",
                "A pasta selecionada não contém imagens PNG, GIF ou JPEG.",
                parent=self.root,
            )
            return
        try:
            entry = self.image_library.add("folder", folder)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Não foi possível salvar na biblioteca",
                str(error),
                parent=self.root,
            )
            return
        self.last_folder_path = folder.resolve()
        self.last_folder_entry = entry
        self.mode.set("folder")
        self._save_layout_settings()
        self._refresh_library_view()
        self._begin_image_preparation("folder", image_paths, entry)

    def _begin_image_preparation(
        self,
        kind: str,
        paths: list[Path],
        entry: ImageLibraryEntry,
        start_index: int = 0,
    ) -> None:
        if self.preparation_running:
            return
        self.preparation_running = True
        self.pending_preparation = (kind, paths, entry, start_index)
        self._cancel_scheduled_update()
        self._cancel_countdown()
        self.library_progress.configure(maximum=len(paths), value=0)
        self.library_status.set(
            f"Preparando 0 de {len(paths)} imagens. "
            "Você poderá iniciar quando o preparo terminar."
        )
        self.run_status.configure(text="Preparando imagens para a telinha...")
        self._update_controls()
        layout = self.image_layout.get()
        orientation = self._selected_orientation()
        threading.Thread(
            target=self._prepare_images_in_background,
            args=(entry, paths, layout, orientation),
            daemon=True,
        ).start()
        self.root.after(100, self._poll_image_preparation)

    def _prepare_images_in_background(
        self,
        entry: ImageLibraryEntry,
        paths: list[Path],
        layout: str,
        orientation: str,
    ) -> None:
        try:
            for index, path in enumerate(paths, start=1):
                self.image_library.prepare_image(
                    entry,
                    path,
                    layout,
                    orientation,
                    save_index=False,
                )
                self.preparation_results.put(
                    ("progress", (index, len(paths), path.name))
                )
        except (OSError, ValueError) as error:
            try:
                self.image_library.save()
            except OSError as save_error:
                self.preparation_results.put(
                    ("error", f"{error}; também não foi possível salvar o índice: {save_error}")
                )
            else:
                self.preparation_results.put(("error", str(error)))
        else:
            try:
                self.image_library.save()
            except OSError as error:
                self.preparation_results.put(("error", str(error)))
            else:
                self.preparation_results.put(("success", ""))

    def _poll_image_preparation(self) -> None:
        try:
            while True:
                status, payload = self.preparation_results.get_nowait()
                if status == "progress":
                    index, total, name = payload
                    self.library_progress.configure(value=index)
                    self.library_status.set(
                        f"Preparadas {index} de {total}: {name}"
                    )
                    self.run_status.configure(
                        text=f"Preparando imagens: {index} de {total} — {name}"
                    )
                    continue
                if status == "error":
                    self.preparation_running = False
                    self.pending_preparation = None
                    self.library_status.set("O preparo foi interrompido.")
                    self.run_status.configure(
                        text=f"Não foi possível preparar as imagens: {payload}"
                    )
                    self._update_controls()
                    if self.auto_running and self.mode.get() == "folder":
                        try:
                            self._schedule_next_update(
                                self._selected_slideshow_interval_ms()
                            )
                        except ValueError as interval_error:
                            self.run_status.configure(
                                text=(
                                    "A apresentação foi parada porque o "
                                    f"intervalo é inválido: {interval_error}"
                                )
                            )
                            self._stop_automatic()
                    messagebox.showerror(
                        "Falha ao preparar imagens",
                        "Não foi possível preparar a imagem para a telinha:\n\n"
                        f"{payload}\n\n"
                        "Os arquivos originais não foram alterados.",
                        parent=self.root,
                    )
                    continue

                pending = self.pending_preparation
                self.pending_preparation = None
                self.preparation_running = False
                if pending is None:
                    continue
                kind, paths, entry, start_index = pending
                selected_path = paths[start_index % len(paths)]
                try:
                    prepared = self.image_library.prepare_image(
                        entry,
                        selected_path,
                        self.image_layout.get(),
                        self._selected_orientation(),
                    )
                except (OSError, ValueError) as error:
                    self.library_status.set("O preparo terminou, mas a leitura falhou.")
                    messagebox.showerror(
                        "Falha ao abrir imagem preparada",
                        f"A cópia preparada não pôde ser carregada:\n{error}",
                        parent=self.root,
                    )
                    self._update_controls()
                    continue

                self.active_library_entry = entry
                self.background_path = selected_path
                self.background_image = None
                self.background_pixels = prepared.pixels
                self.current_preview_path = prepared.preview_path
                if kind == "folder":
                    self.folder_images = paths
                    self.folder_index = start_index % len(paths)
                    self.mode.set("folder")
                else:
                    self.folder_images = []
                    self.folder_index = 0
                    self.mode.set("fixed")
                self._update_image_label()
                self._draw_preview()
                self._save_layout_settings()
                self.run_status.configure(
                    text="Imagens preparadas; prontas para a atualização contínua."
                )
                self.library_status.set(
                    f"Pronto: {len(paths)} imagem(ns) preparada(s) e visível(is) "
                    "na pasta “Imagens visuais”."
                )
                if self.auto_running:
                    self._queue_background_send()
                self._update_controls()
        except queue.Empty:
            pass
        if self.preparation_running:
            self.root.after(100, self._poll_image_preparation)

    def _refresh_library_view(self) -> None:
        if not hasattr(self, "library_tree"):
            return
        for item in self.library_tree.get_children():
            self.library_tree.delete(item)
        self.library_rows: dict[str, ImageLibraryEntry] = {}
        for index, entry in enumerate(self.image_library.entries):
            row_id = f"library-{index}"
            path = str(entry["path"])
            self.library_tree.insert(
                "",
                "end",
                iid=row_id,
                text=str(entry["name"]),
                values=(
                    "Pasta" if entry["kind"] == "folder" else "Imagem",
                    path,
                ),
            )
            self.library_rows[row_id] = entry

    def _use_library_selection(self) -> None:
        selection = self.library_tree.selection()
        if not selection:
            messagebox.showinfo(
                "Selecione um item",
                "Selecione uma imagem ou pasta da biblioteca.",
                parent=self.root,
            )
            return
        entry = self.library_rows[selection[0]]
        path = Path(str(entry["path"]))
        if entry["kind"] == "folder":
            self._select_folder_path(path)
        else:
            self._select_image_path(path)
        self.notebook.select(self.panel_tab)

    def _remove_library_selection(self) -> None:
        if self.auto_running or self.preparation_running:
            messagebox.showinfo(
                "Atualização em andamento",
                "Pare a atualização contínua e aguarde o preparo terminar "
                "antes de remover itens da biblioteca.",
                parent=self.root,
            )
            return
        selection = self.library_tree.selection()
        if not selection:
            messagebox.showinfo(
                "Selecione um item",
                "Selecione uma imagem ou pasta para remover da biblioteca.",
                parent=self.root,
            )
            return
        entry = self.library_rows[selection[0]]
        confirmed = messagebox.askyesno(
            "Remover da biblioteca",
            f"Remover “{entry['name']}” e as cópias preparadas da biblioteca?\n\n"
            "O arquivo original e a pasta original não serão apagados.",
            parent=self.root,
        )
        if not confirmed:
            return
        try:
            self.image_library.remove(entry)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Não foi possível remover o item",
                str(error),
                parent=self.root,
            )
            return
        if (
            entry["kind"] == "image"
            and self.last_image_path is not None
            and str(self.last_image_path.resolve()) == str(entry["path"])
        ):
            self.last_image_entry = self._make_last_config_entry(
                "image", self.last_image_path
            )
        if (
            entry["kind"] == "folder"
            and self.last_folder_path is not None
            and str(self.last_folder_path.resolve()) == str(entry["path"])
        ):
            self.last_folder_entry = self._make_last_config_entry(
                "folder", self.last_folder_path
            )
        if self.active_library_entry is entry:
            self.active_library_entry = None
            self.current_preview_path = None
            self.background_path = None
            self.background_image = None
            self.background_pixels = None
            self.folder_images = []
            self.folder_index = 0
            self.mode.set("fixed")
            self._update_image_label()
            self._draw_preview()
        self._save_layout_settings()
        self._refresh_library_view()
        self.library_status.set("Item removido; o original foi preservado.")

    def _update_image_label(self) -> None:
        if self.mode.get() == "folder":
            if self.folder_images:
                self.image_selection.set(
                    f"Pasta: {self.folder_images[0].parent}\n"
                    f"{len(self.folder_images)} imagens PNG/GIF/JPEG; "
                    f"atual: {self.background_path.name if self.background_path else '-'}"
                )
            else:
                self.image_selection.set("Escolha uma pasta de imagens.")
        elif self.background_path is not None:
            self.image_selection.set(f"Imagem fixa: {self.background_path.name}")
        else:
            self.image_selection.set("Fundo escuro padrão; nenhuma imagem selecionada.")

    def _draw_preview(self) -> None:
        orientation = self._selected_orientation()
        if self.current_preview_path is not None and self.current_preview_path.is_file():
            photo = tk.PhotoImage(
                master=self.root,
                file=str(self.current_preview_path),
            )
            width, height = photo.width(), photo.height()
        else:
            frame = self._render_current_frame(self.background_pixels, set())
            preview_pixels, width, height = orient_frame_for_preview(
                frame,
                orientation,
            )
            photo = self._photo_from_rgb565(preview_pixels, width, height)
        self.preview_rendered_image = photo
        self.canvas.delete("all")
        self.preview_metric_items: dict[str, dict[str, int]] = {}
        self.canvas.configure(bg="#070d17")
        self.canvas.configure(width=width, height=height)
        self.canvas.create_image(0, 0, anchor="nw", image=photo, tags=("background",))
        for key in self.visible_metrics:
            x, y = self.metric_positions[key]
            tags = (f"metric_{key}",)
            scale = self._selected_metric_scale(key)
            items: dict[str, int] = {}
            if key == "cpu":
                items["text"] = self.canvas.create_text(
                    x,
                    y,
                    anchor="nw",
                    fill="#eef2f7",
                    font=("Segoe UI", 7 * scale, "bold"),
                    tags=tags,
                )
                bar_y = y + 10 * scale
                bar_width, bar_height = self._preview_bar_size(key)
                items["bar_bg"] = self.canvas.create_rectangle(
                    x, bar_y, x + bar_width, bar_y + bar_height,
                    fill="#323e4c", outline="", tags=tags,
                )
                items["bar"] = self.canvas.create_rectangle(
                    x, bar_y, x, bar_y + bar_height,
                    fill="#44cdf5", outline="", tags=tags,
                )
            elif key == "memory":
                items["text"] = self.canvas.create_text(
                    x,
                    y,
                    anchor="nw",
                    fill="#eef2f7",
                    font=("Segoe UI", 7 * scale, "bold"),
                    tags=tags,
                )
                bar_y = y + 10 * scale
                bar_width, bar_height = self._preview_bar_size(key)
                items["bar_bg"] = self.canvas.create_rectangle(
                    x, bar_y, x + bar_width, bar_y + bar_height,
                    fill="#323e4c", outline="", tags=tags,
                )
                items["bar"] = self.canvas.create_rectangle(
                    x, bar_y, x, bar_y + bar_height,
                    fill="#b58eff", outline="", tags=tags,
                )
            elif key == "clock":
                items["time"] = self.canvas.create_text(
                    x, y, anchor="nw", fill="#44cdf5",
                    font=("Segoe UI", 9 * scale, "bold"), tags=tags,
                )
                items["date"] = self.canvas.create_text(
                    x, y + 12 * scale, anchor="nw", fill="#eef2f7",
                    font=("Segoe UI", 7 * scale), tags=tags,
                )
            else:
                items["text"] = self.canvas.create_text(
                    x,
                    y,
                    anchor="nw",
                    fill="#eef2f7",
                    font=("Segoe UI", 7 * scale, "bold"),
                    tags=tags,
                )
            self.preview_metric_items[key] = items
        self._update_preview_metrics()
        self.canvas.bind("<ButtonPress-1>", self._start_metric_drag)
        self.canvas.bind("<B1-Motion>", self._drag_metric)
        self.canvas.bind("<ButtonRelease-1>", self._finish_metric_drag)

    def _preview_bar_size(self, metric: str) -> tuple[int, int]:
        orientation = self._selected_orientation()
        frame_width = SCREEN_WIDTH if orientation == "landscape" else SCREEN_HEIGHT
        x, _ = self.metric_positions[metric]
        scale = self._selected_metric_scale(metric)
        return min(145 * scale // 2, frame_width - x), 3 * scale

    def _update_preview_metrics(self) -> None:
        if not hasattr(self, "preview_metric_items"):
            return
        cpu_value = PREVIEW_METRICS["cpu_percent"]
        memory_value = PREVIEW_METRICS["memory_percent"]
        values = {
            "cpu": f"{cpu_value:.0f}%",
            "memory": f"{memory_value:.0f}%",
            "clock": PREVIEW_TIME.strftime("%H:%M"),
            "date": PREVIEW_TIME.strftime("%d/%m"),
            "uptime": "UP " + self._short_uptime(
                int(PREVIEW_METRICS["uptime_seconds"])
            ),
            "disk": (
                f"D {PREVIEW_METRICS['disk_free_gb']:.0f}/"
                f"{PREVIEW_METRICS['disk_total_gb']:.0f}G"
            ),
        }
        for key, items in self.preview_metric_items.items():
            if key == "clock":
                self.canvas.itemconfigure(items["time"], text=values["clock"])
                self.canvas.itemconfigure(items["date"], text=values["date"])
                continue
            text = (
                f"CPU {values['cpu']}"
                if key == "cpu"
                else f"RAM {values['memory']}"
                if key == "memory"
                else values[key]
            )
            self.canvas.itemconfigure(items["text"], text=text)
            if key in {"cpu", "memory"}:
                x, y = self.metric_positions[key]
                bar_width, bar_height = self._preview_bar_size(key)
                fraction = cpu_value if key == "cpu" else memory_value
                bar_y = y + 10 * self._selected_metric_scale(key)
                filled_width = round(bar_width * fraction / 100)
                self.canvas.coords(
                    items["bar_bg"],
                    x,
                    bar_y,
                    x + bar_width,
                    bar_y + bar_height,
                )
                self.canvas.coords(
                    items["bar"],
                    x,
                    bar_y,
                    x + filled_width,
                    bar_y + bar_height,
                )

    def _start_metric_drag(self, event: tk.Event) -> None:
        if self.auto_running or self.sending or self.metrics_update_running:
            self.drag_metric = None
            return
        current = self.canvas.find_withtag("current")
        if not current:
            self.drag_metric = None
            return
        tags = self.canvas.gettags(current[0])
        metric_tag = next((tag for tag in tags if tag.startswith("metric_")), None)
        if metric_tag is None:
            self.drag_metric = None
            return
        self.drag_metric = metric_tag.removeprefix("metric_")
        x, y = self.metric_positions[self.drag_metric]
        self.drag_offset = (event.x - x, event.y - y)

    def _drag_metric(self, event: tk.Event) -> None:
        if (
            self.drag_metric is None
            or self.auto_running
            or self.sending
            or self.metrics_update_running
        ):
            return
        orientation = self._selected_orientation()
        frame_width = SCREEN_WIDTH if orientation == "landscape" else SCREEN_HEIGHT
        frame_height = SCREEN_HEIGHT if orientation == "landscape" else SCREEN_WIDTH
        item_width, item_height = self._metric_bounds(self.drag_metric)
        x = max(0, min(event.x - self.drag_offset[0], frame_width - item_width))
        y = max(0, min(event.y - self.drag_offset[1], frame_height - item_height))
        old_x, old_y = self.metric_positions[self.drag_metric]
        self.metric_positions[self.drag_metric] = (x, y)
        self.canvas.move(
            f"metric_{self.drag_metric}",
            x - old_x,
            y - old_y,
        )

    def _finish_metric_drag(self, _event: tk.Event) -> None:
        if (
            self.drag_metric is None
            or self.auto_running
            or self.sending
            or self.metrics_update_running
        ):
            return
        self.drag_metric = None
        self._save_layout_settings()
        self._layout_changed()

    def _reset_metric_positions(self, orientation: str) -> None:
        self.metric_positions = (
            {
                "cpu": (12, 39),
                "memory": (12, 75),
                "clock": (196, 43),
                "uptime": (12, 127),
                "disk": (196, 127),
            }
            if orientation == "landscape"
            else {
                "cpu": (12, 35),
                "memory": (12, 92),
                "clock": (12, 149),
                "uptime": (12, 206),
                "disk": (12, 263),
            }
        )

    def _anchor_position(self, metric: str, anchor: str) -> tuple[int, int]:
        orientation = self._selected_orientation()
        frame_width = SCREEN_WIDTH if orientation == "landscape" else SCREEN_HEIGHT
        frame_height = SCREEN_HEIGHT if orientation == "landscape" else SCREEN_WIDTH
        item_width, item_height = self._metric_bounds(metric)
        columns = {
            "esquerdo": 0,
            "centro": max(0, (frame_width - item_width) // 2),
            "direito": max(0, frame_width - item_width),
        }
        rows = {
            "Superior": 0,
            "Centro": max(0, (frame_height - item_height) // 2),
            "Inferior": max(0, frame_height - item_height),
        }
        vertical, horizontal = anchor.split(" ", 1)
        return columns[horizontal], rows[vertical]

    def _anchor_for_position(self, metric: str) -> str:
        x, y = self.metric_positions[metric]
        orientation = self._selected_orientation()
        frame_width = SCREEN_WIDTH if orientation == "landscape" else SCREEN_HEIGHT
        frame_height = SCREEN_HEIGHT if orientation == "landscape" else SCREEN_WIDTH
        item_width, item_height = self._metric_bounds(metric)
        column = min(
            (("esquerdo", 0), ("centro", 1), ("direito", 2)),
            key=lambda item: abs(
                x
                - {
                    "esquerdo": 0,
                    "centro": max(0, (frame_width - item_width) // 2),
                    "direito": max(0, frame_width - item_width),
                }[item[0]]
            ),
        )[0]
        row = min(
            (("Superior", 0), ("Centro", 1), ("Inferior", 2)),
            key=lambda item: abs(
                y
                - {
                    "Superior": 0,
                    "Centro": max(0, (frame_height - item_height) // 2),
                    "Inferior": max(0, frame_height - item_height),
                }[item[0]]
            ),
        )[0]
        return f"{row} {column}"

    def _customize_metrics(self) -> None:
        if self.auto_running or self.sending or self.metrics_update_running:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Personalizar informações")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        content = ttk.Frame(dialog, padding=14)
        content.pack(fill="both", expand=True)
        ttk.Label(
            content,
            text="Escolha o que aparece, a posição e o tamanho de cada informação.",
            style="Muted.TLabel",
        ).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))

        for row, (key, label) in enumerate(METRIC_LABELS.items(), start=1):
            visible = tk.BooleanVar(value=key in self.visible_metrics)
            position = tk.StringVar(value=self._anchor_for_position(key))
            size = tk.StringVar(value=self.metric_sizes[key])
            checkbox = ttk.Checkbutton(
                content,
                text=label,
                variable=visible,
                command=lambda metric=key, value=visible: self._set_metric_visible(
                    metric, value.get()
                ),
            )
            checkbox.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
            ttk.Label(content, text="Posição").grid(row=row, column=1, padx=4)
            combo = ttk.Combobox(
                content,
                textvariable=position,
                values=ANCHOR_LABELS,
                state="readonly",
                width=24,
            )
            combo.grid(row=row, column=2, sticky="ew", pady=3)
            combo.bind(
                "<<ComboboxSelected>>",
                lambda _event, metric=key, value=position: self._set_metric_anchor(
                    metric, value.get()
                ),
            )
            ttk.Label(content, text="Tamanho").grid(row=row, column=3, padx=(8, 4))
            size_combo = ttk.Combobox(
                content,
                textvariable=size,
                values=tuple(METRIC_SCALES),
                state="readonly",
                width=14,
            )
            size_combo.grid(row=row, column=4, sticky="ew", pady=3)
            size_combo.bind(
                "<<ComboboxSelected>>",
                lambda _event, metric=key, value=size: self._set_metric_size(
                    metric, value.get()
                ),
            )
        ttk.Label(
            content,
            text="Depois, arraste qualquer item diretamente na prévia para ajustar.",
            style="Muted.TLabel",
            wraplength=370,
        ).grid(row=len(METRIC_LABELS) + 1, column=0, columnspan=5, sticky="w", pady=(9, 0))
        dialog.grab_set()

    def _set_metric_visible(self, metric: str, visible: bool) -> None:
        if self.auto_running or self.sending or self.metrics_update_running:
            return
        if visible:
            self.visible_metrics.add(metric)
        else:
            self.visible_metrics.discard(metric)
        self._save_layout_settings()
        self._layout_changed()

    def _set_metric_anchor(self, metric: str, anchor: str) -> None:
        if self.auto_running or self.sending or self.metrics_update_running:
            return
        self.metric_positions[metric] = self._anchor_position(metric, anchor)
        self._save_layout_settings()
        self._layout_changed()

    def _set_metric_size(self, metric: str, size: str) -> None:
        if self.auto_running or self.sending or self.metrics_update_running:
            return
        if size not in METRIC_SCALES:
            raise ValueError(f"Tamanho desconhecido para {METRIC_LABELS[metric]}.")
        old_width, old_height = self._metric_bounds(metric)
        self.metric_sizes[metric] = size
        new_width, new_height = self._metric_bounds(metric)
        orientation = self._selected_orientation()
        frame_width = SCREEN_WIDTH if orientation == "landscape" else SCREEN_HEIGHT
        frame_height = SCREEN_HEIGHT if orientation == "landscape" else SCREEN_WIDTH
        x, y = self.metric_positions[metric]
        self.metric_positions[metric] = (
            max(0, min(x, frame_width - new_width)),
            max(0, min(y, frame_height - new_height)),
        )
        self._save_layout_settings()
        if old_width != new_width or old_height != new_height:
            self._layout_changed()

    def _layout_changed(self) -> None:
        self._draw_preview()

    def _save_layout_settings(self) -> None:
        path = Path.home() / ".painel_s1_windows.json"
        settings = {
            "orientation": self.orientation.get(),
            "image_layout": self.image_layout.get(),
            "mode": self.mode.get(),
            "last_image_path": (
                None if self.last_image_path is None else str(self.last_image_path)
            ),
            "last_folder_path": (
                None if self.last_folder_path is None else str(self.last_folder_path)
            ),
            "last_image_entry": self.last_image_entry,
            "last_folder_entry": self.last_folder_entry,
            "metric_sizes": self.metric_sizes,
            "slideshow_interval": self.slideshow_interval.get(),
            "visible_metrics": sorted(self.visible_metrics),
            "metric_positions": self.metric_positions,
        }
        try:
            path.write_text(
                json.dumps(settings, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
        except OSError as error:
            messagebox.showerror(
                "Não foi possível salvar o layout",
                f"As preferências não puderam ser gravadas em {path}:\n{error}",
                parent=self.root,
            )

    def _load_layout_settings(self) -> None:
        path = Path.home() / ".painel_s1_windows.json"
        if not path.exists():
            return
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
            orientation = settings["orientation"]
            metric_sizes = settings.get("metric_sizes")
            legacy_metric_size = settings.get("metric_size", "Normal")
            slideshow_interval = str(settings.get("slideshow_interval", "30"))
            visible_metrics = settings["visible_metrics"]
            metric_positions = settings["metric_positions"]
            image_layout = settings.get("image_layout", IMAGE_LAYOUTS[0])
            mode = settings.get("mode", "fixed")
            last_image_path = settings.get("last_image_path")
            last_folder_path = settings.get("last_folder_path")
            last_image_entry = settings.get("last_image_entry")
            last_folder_entry = settings.get("last_folder_entry")
            if orientation not in ORIENTATION_LABELS:
                raise ValueError("A orientação salva não é reconhecida.")
            if image_layout not in IMAGE_LAYOUTS:
                raise ValueError("O ajuste de imagem salvo não é reconhecido.")
            if mode not in {"fixed", "folder"}:
                raise ValueError("O modo de imagem salvo não é reconhecido.")
            if last_image_path is not None and not isinstance(last_image_path, str):
                raise ValueError("O caminho da última imagem salva é inválido.")
            if last_folder_path is not None and not isinstance(last_folder_path, str):
                raise ValueError("O caminho da última pasta salva é inválido.")
            for entry, kind, saved_path in (
                (last_image_entry, "image", last_image_path),
                (last_folder_entry, "folder", last_folder_path),
            ):
                if entry is None:
                    continue
                if (
                    not isinstance(entry, dict)
                    or entry.get("kind") != kind
                    or not isinstance(entry.get("path"), str)
                    or entry.get("path") != saved_path
                    or not isinstance(entry.get("name"), str)
                    or not isinstance(entry.get("cache_name"), str)
                    or not isinstance(entry.get("prepared", {}), dict)
                ):
                    raise ValueError("Os dados da última imagem preparada são inválidos.")
            if slideshow_interval not in {
                str(seconds) for seconds in SLIDESHOW_INTERVAL_OPTIONS
            }:
                raise ValueError("O intervalo de troca de imagens salvo é inválido.")
            if metric_sizes is None:
                metric_sizes = {
                    metric: legacy_metric_size for metric in METRIC_LABELS
                }
            if (
                not isinstance(metric_sizes, dict)
                or set(metric_sizes) != set(METRIC_LABELS)
                or any(size not in METRIC_SCALES for size in metric_sizes.values())
            ):
                raise ValueError("Os tamanhos individuais salvos são inválidos.")
            if (
                not isinstance(visible_metrics, list)
                or any(metric not in METRIC_LABELS for metric in visible_metrics)
            ):
                raise ValueError("A lista de informações salva é inválida.")
            if not isinstance(metric_positions, dict):
                raise ValueError("As posições salvas são inválidas.")
            width, height = (
                (SCREEN_WIDTH, SCREEN_HEIGHT)
                if orientation == "Deitada"
                else (SCREEN_HEIGHT, SCREEN_WIDTH)
            )
            loaded_positions = {}
            for metric, (x, y) in metric_positions.items():
                if metric not in METRIC_LABELS or type(x) is not int or type(y) is not int:
                    raise ValueError("Uma posição salva é inválida.")
                base_width, base_height = METRIC_BOUNDS[metric]
                metric_scale = METRIC_SCALES[metric_sizes[metric]]
                if orientation == "Em pé":
                    metric_scale = min(metric_scale, 3)
                item_width = base_width * metric_scale // 2
                item_height = base_height * metric_scale // 2
                loaded_positions[metric] = (
                    max(0, min(x, width - item_width)),
                    max(0, min(y, height - item_height)),
                )
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror(
                "Não foi possível carregar o layout",
                f"As preferências locais em {path} são inválidas:\n{error}",
                parent=self.root,
            )
            return

        self.orientation.set(orientation)
        self.image_layout.set(image_layout)
        self.mode.set(mode)
        self.last_image_path = (
            None if last_image_path is None else Path(last_image_path)
        )
        self.last_folder_path = (
            None if last_folder_path is None else Path(last_folder_path)
        )
        self.last_image_entry = last_image_entry
        self.last_folder_entry = last_folder_entry
        self.metric_sizes = metric_sizes
        self.slideshow_interval.set(slideshow_interval)
        self.visible_metrics = set(visible_metrics)
        self._reset_metric_positions(ORIENTATION_LABELS[orientation])
        self.metric_positions.update(loaded_positions)

    def _restore_last_selection(self) -> None:
        if self.mode.get() == "folder" and self.last_folder_path is not None:
            if self.last_folder_path.is_dir():
                try:
                    image_paths = sorted(
                        (
                            path
                            for path in self.last_folder_path.iterdir()
                            if path.is_file()
                            and path.suffix.lower() in IMAGE_SUFFIXES
                        ),
                        key=lambda path: path.name.casefold(),
                    )
                except OSError as error:
                    self.run_status.configure(
                        text=f"Não foi possível ler a última pasta salva: {error}"
                    )
                    return
                if image_paths:
                    entry = self.last_folder_entry or self._make_last_config_entry(
                        "folder", self.last_folder_path
                    )
                    self.last_folder_entry = entry
                    self._begin_image_preparation("folder", image_paths, entry)
                    return
                self.run_status.configure(
                    text=(
                        "A última pasta salva não contém imagens PNG, GIF ou JPEG: "
                        f"{self.last_folder_path}"
                    )
                )
                return
            self.run_status.configure(
                text=f"A última pasta salva não foi encontrada: {self.last_folder_path}"
            )
            self.mode.set("fixed")
            self._save_layout_settings()
        if self.mode.get() == "fixed" and self.last_image_path is not None:
            if self.last_image_path.is_file():
                entry = self.last_image_entry or self._make_last_config_entry(
                    "image", self.last_image_path
                )
                self.last_image_entry = entry
                self._begin_image_preparation(
                    "image",
                    [self.last_image_path],
                    entry,
                )
                return
            self.run_status.configure(
                text=f"A última imagem salva não foi encontrada: {self.last_image_path}"
            )
            self.last_image_path = None
            self.last_image_entry = None
            self._save_layout_settings()

    def _make_last_config_entry(self, kind: str, path: Path) -> ImageLibraryEntry:
        resolved_path = str(path.resolve())
        base_name = path.name if kind == "folder" else path.stem
        cache_name = f"Última configuração - {base_name}"
        existing_names = {
            str(entry["cache_name"]).casefold()
            for entry in self.image_library.entries
        }
        suffix = 2
        while cache_name.casefold() in existing_names:
            cache_name = f"Última configuração - {base_name} ({suffix})"
            suffix += 1
        return {
            "kind": kind,
            "name": path.name,
            "path": resolved_path,
            "cache_name": cache_name,
            "prepared": {},
        }

    @staticmethod
    def _short_uptime(seconds: int) -> str:
        days, remainder = divmod(seconds, 24 * 60 * 60)
        hours = remainder // (60 * 60)
        return f"{days:02}D {hours:02}H"

    def _refresh_metrics(self) -> None:
        self.metrics_refresh_id = None
        try:
            self.latest_metrics = self.metrics.read()
        except OSError as error:
            self.metrics_available = False
            self.auto_running = False
            self._cancel_metrics_refresh()
            self.image_apply_pending = False
            self.next_update_at = None
            self._cancel_scheduled_update()
            self._cancel_countdown()
            self.run_status.configure(text=f"Falha ao ler métricas locais: {error}")
            self._update_controls()
            if not self.auto_running:
                self.metrics_refresh_id = self.root.after(
                    METRICS_RETRY_MS,
                    self._refresh_metrics,
                )
        else:
            was_available = self.metrics_available
            self.metrics_available = True
            if not was_available:
                self._update_controls()
            self._send_live_metric_updates()
        if self.auto_running:
            self.metrics_refresh_id = self.root.after(
                REFRESH_MS,
                self._refresh_metrics,
            )

    def _render_background(self, image_pixels: bytes | None) -> bytes:
        orientation = self._selected_orientation()
        if (
            self.render_background_cache is None
            or self.render_background_source is not image_pixels
            or self.render_background_orientation != orientation
        ):
            self.render_background_cache = prepare_render_background(
                image_pixels,
                orientation=orientation,
            )
            self.render_background_source = image_pixels
            self.render_background_orientation = orientation
        return self.render_background_cache

    def _render_current_frame(
        self,
        image_pixels: bytes | None,
        visible_metrics: set[str] | None = None,
    ) -> bytes:
        prepared_background = self._render_background(image_pixels)
        return render_frame(
            prepared_background,
            (
                None
                if self.latest_metrics["cpu_percent"] is None
                else float(self.latest_metrics["cpu_percent"])
            ),
            float(self.latest_metrics["memory_percent"]),
            int(self.latest_metrics["uptime_seconds"]),
            now=datetime.now(),
            orientation=self._selected_orientation(),
            metric_positions=self.metric_positions,
            visible_metrics=(
                self.visible_metrics
                if visible_metrics is None
                else visible_metrics
            ),
            disk_free_gb=float(self.latest_metrics["disk_free_gb"]),
            disk_total_gb=float(self.latest_metrics["disk_total_gb"]),
            metric_scale={
                metric: self._selected_metric_scale(metric)
                for metric in METRIC_LABELS
            },
            prepared_background=True,
        )

    def _send_live_metric_updates(self) -> None:
        writer = self.panel_writer
        if (
            not self.auto_running
            or self.sending
            or self.metrics_update_running
            or self.preparation_running
            or self.image_apply_pending
            or writer is None
        ):
            return
        try:
            frame = self._render_current_frame(self.displayed_background_pixels)
        except (tk.TclError, ValueError) as error:
            self.auto_running = False
            self.image_apply_pending = False
            self.next_update_at = None
            self._cancel_scheduled_update()
            self._cancel_countdown()
            self.run_status.configure(
                text=f"Atualização das métricas interrompida: {error}"
            )
            self._update_controls()
            return

        self.metrics_update_running = True
        if frame == self.displayed_frame:
            self.metrics_update_running = False
            return
        self.pending_metric_frame = frame
        self._update_controls()
        threading.Thread(
            target=self._send_live_metric_updates_in_background,
            args=(writer, frame, self.displayed_frame),
            daemon=True,
        ).start()

    def _send_live_metric_updates_in_background(
        self,
        writer: PanelWriter,
        frame: bytes,
        previous_frame: bytes | None,
    ) -> None:
        try:
            writer.send_metric_updates(frame, previous_frame)
        except (OSError, ValueError) as error:
            self.send_results.put(("metrics_error", str(error)))
        else:
            self.send_results.put(("metrics_success", ""))

    def _update_controls(self) -> None:
        library_busy = (
            self.preparation_running
            or self.sending
            or self.metrics_update_running
            or self.heartbeat_running
        )
        self.library_use_button.configure(
            state="disabled" if library_busy else "normal"
        )
        self.library_remove_button.configure(
            state=(
                "disabled"
                if library_busy or self.auto_running
                else "normal"
            )
        )
        selection_state = (
            "disabled"
            if (
                self.auto_running
                or self.sending
                or self.metrics_update_running
                or self.heartbeat_running
            )
            else "normal"
        )
        for control in self.selection_controls:
            control.configure(state=selection_state)

        if self.preparation_running:
            for widget in (
                self.choose_image_button,
                self.image_layout_combo,
                self.orientation_combo,
                self.customize_button,
                self.slideshow_interval_combo,
                self.diagnostic_button,
                self.start_button,
                self.library_use_button,
                self.library_remove_button,
            ):
                widget.configure(state="disabled")
            self.stop_button.configure(
                state="normal" if self.auto_running else "disabled"
            )
            return

        if self.auto_running:
            image_state = "disabled" if self.sending else "normal"
            self.choose_image_button.configure(state=image_state)
            self.image_layout_combo.configure(
                state="disabled" if self.sending else "readonly"
            )
            self.orientation_combo.configure(
                state="disabled" if self.sending else "readonly"
            )
            self.customize_button.configure(
                state="disabled"
            )
            self.slideshow_interval_combo.configure(state="disabled")
            self.diagnostic_button.configure(state="disabled")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            return
        if self.sending or self.metrics_update_running or self.heartbeat_running:
            self.choose_image_button.configure(state="disabled")
            self.image_layout_combo.configure(state="disabled")
            self.orientation_combo.configure(state="disabled")
            self.customize_button.configure(state="disabled")
            self.slideshow_interval_combo.configure(state="disabled")
            self.diagnostic_button.configure(state="disabled")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
            return

        can_send = self.device_compatible and self.metrics_available
        if self.mode.get() == "folder" and not self.folder_images:
            can_send = False
        self.choose_image_button.configure(state="normal")
        self.image_layout_combo.configure(state="readonly")
        self.orientation_combo.configure(state="readonly")
        self.customize_button.configure(state="normal")
        self.slideshow_interval_combo.configure(
            state="readonly" if self.mode.get() == "folder" else "disabled"
        )
        diagnostic_state = "normal" if self.device_compatible else "disabled"
        self.diagnostic_button.configure(state=diagnostic_state)
        self.start_button.configure(state="normal" if can_send else "disabled")
        self.stop_button.configure(state="disabled")

    def _send_diagnostic_frame(self) -> None:
        if (
            self.sending
            or self.metrics_update_running
            or self.heartbeat_running
            or self.auto_running
            or self.preparation_running
        ):
            return
        confirmed = messagebox.askyesno(
            "Teste visual do painel",
            "Enviar o padrão azul “S1 TEST” à tela física?\n\n"
            "Ele substituirá temporariamente o conteúdo atual. Isso testa "
            "o envio independentemente da imagem escolhida.",
            parent=self.root,
        )
        if confirmed:
            self._begin_send(build_test_frame())

    def _start_automatic(self) -> None:
        if (
            self.sending
            or self.metrics_update_running
            or self.heartbeat_running
            or self.auto_running
            or self.preparation_running
        ):
            return
        if self.mode.get() == "folder" and not self.folder_images:
            messagebox.showerror(
                "Pasta não selecionada",
                "Escolha uma pasta com imagens PNG, GIF ou JPEG antes de iniciar.",
                parent=self.root,
            )
            return
        if self.mode.get() == "folder":
            try:
                interval_seconds = self._selected_slideshow_interval_ms() // 1000
            except ValueError as error:
                messagebox.showerror(
                    "Intervalo inválido",
                    str(error),
                    parent=self.root,
                )
                return
            interval_text = (
                "um quadro completo imediato, métricas a cada 0,8 segundo e "
                f"troca de imagem a cada {interval_seconds} segundos"
            )
        else:
            interval_text = (
                "um quadro completo imediato e atualizações das métricas "
                "a cada 0,8 segundo, mantendo a imagem fixa"
            )
        confirmed = messagebox.askyesno(
            "Iniciar atualização automática",
            "Iniciar o envio automático " + interval_text + "?\n\n"
            "Depois do quadro inicial, somente as áreas das métricas serão "
            "atualizadas rapidamente. Clique em Parar para encerrar. "
            "Nenhum driver será alterado.",
            parent=self.root,
        )
        if not confirmed:
            return
        try:
            self.latest_metrics = self.metrics.read()
        except OSError as error:
            self.metrics_available = False
            self.run_status.configure(text=f"Falha ao ler métricas locais: {error}")
            self._update_controls()
            messagebox.showerror(
                "Falha ao ler métricas",
                f"Não foi possível iniciar a atualização contínua:\n\n{error}",
                parent=self.root,
            )
            return
        self.metrics_available = True
        self._cancel_metrics_refresh()
        self.auto_running = True
        self.image_apply_pending = False
        self.frame_count = 0
        self.next_update_at = None
        self.run_status.configure(
            text=f"Atualização contínua ativa: {interval_text}. "
            "Use Parar para encerrar."
        )
        self._update_controls()
        self._begin_send()
        if self.auto_running:
            self.metrics_refresh_id = self.root.after(
                REFRESH_MS,
                self._refresh_metrics,
            )

    def _stop_automatic(self) -> None:
        if not self.auto_running:
            return
        self.auto_running = False
        self.image_apply_pending = False
        self.next_update_at = None
        self._cancel_scheduled_update()
        self._cancel_metrics_refresh()
        if self.sending:
            self.run_status.configure(
                text="Parada solicitada; o quadro atual terminará antes de parar."
            )
        else:
            self.run_status.configure(text="Atualização automática parada.")
        self._cancel_countdown()
        self._update_controls()

    def _advance_folder(self) -> bool:
        if not self.folder_images:
            return False
        self.folder_index = (self.folder_index + 1) % len(self.folder_images)
        path = self.folder_images[self.folder_index]
        if self.active_library_entry is None:
            return False
        try:
            prepared = self.image_library.prepare_image(
                self.active_library_entry,
                path,
                self.image_layout.get(),
                self._selected_orientation(),
            )
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Não foi possível ajustar a imagem",
                f"A imagem não pôde ser preparada:\n{error}",
                parent=self.root,
            )
            return False
        self.background_path = path
        self.background_image = None
        self.background_pixels = prepared.pixels
        self.current_preview_path = prepared.preview_path
        self._update_image_label()
        self._draw_preview()
        return True

    def _automatic_refresh(self) -> None:
        self.next_update_id = None
        self.next_update_at = None
        self._cancel_countdown()
        if not self.auto_running or self.sending:
            return
        if self.preparation_running:
            self.next_update_id = self.root.after(100, self._automatic_refresh)
            return
        if self.metrics_update_running:
            self.next_update_id = self.root.after(100, self._automatic_refresh)
            return
        if self.mode.get() == "folder" and not self._advance_folder():
            self.auto_running = False
            self._cancel_metrics_refresh()
            self.next_update_at = None
            self._cancel_countdown()
            self.run_status.configure(
                text="A apresentação foi parada porque uma imagem não pôde ser aberta."
            )
            self._update_controls()
            return
        self._begin_send()

    def _begin_send(self, frame: bytes | None = None) -> None:
        if self.sending or self.metrics_update_running:
            return
        if frame is None and not self.metrics_available:
            self.auto_running = False
            self._cancel_metrics_refresh()
            self.run_status.configure(
                text="Envio cancelado: as métricas locais não estão disponíveis."
            )
            self._update_controls()
            return
        background_to_display = None
        if frame is None:
            try:
                frame = self._render_current_frame(self.background_pixels)
            except (tk.TclError, ValueError) as error:
                self.auto_running = False
                self._cancel_metrics_refresh()
                self.next_update_at = None
                self._cancel_scheduled_update()
                self._cancel_countdown()
                self.run_status.configure(
                    text=f"Não foi possível desenhar o quadro: {error}"
                )
                self._update_controls()
                return
            background_to_display = self.background_pixels

        self.pending_background_pixels = background_to_display
        self.pending_frame = frame
        self.sending = True
        self.last_frame_started = time.monotonic()
        self._update_controls()
        self.run_status.configure(text="Enviando quadro ao painel...")
        threading.Thread(
            target=self._send_in_background,
            args=(frame, self._selected_orientation()),
            daemon=True,
        ).start()

    def _send_in_background(
        self,
        frame: bytes,
        orientation: str = "landscape",
    ) -> None:
        try:
            if self.panel_writer is None:
                self.panel_writer = PanelWriter()
            self.panel_writer.set_orientation(orientation)
            self.panel_writer.send(frame)
        except (OSError, ValueError) as error:
            if self.panel_writer is not None:
                self.panel_writer.close()
                self.panel_writer = None
            self.send_results.put(("error", str(error)))
        else:
            self.send_results.put(("success", ""))

    def _heartbeat_tick(self) -> None:
        self.heartbeat_id = None
        writer = self.panel_writer
        if writer is None:
            return
        if (
            not self.heartbeat_running
            and not self.sending
            and not self.metrics_update_running
        ):
            self.heartbeat_running = True
            threading.Thread(
                target=self._heartbeat_in_background,
                args=(writer,),
                daemon=True,
            ).start()
        self.heartbeat_id = self.root.after(
            HEARTBEAT_INTERVAL_MS,
            self._heartbeat_tick,
        )

    def _heartbeat_in_background(self, writer: PanelWriter) -> None:
        try:
            writer.heartbeat()
        except (OSError, ValueError) as error:
            self.send_results.put(("heartbeat_error", str(error)))
        else:
            self.send_results.put(("heartbeat_success", ""))

    def _poll_send_results(self) -> None:
        try:
            while True:
                status, message = self.send_results.get_nowait()
                if status == "heartbeat_success":
                    self.heartbeat_running = False
                    if not self.auto_running and not self.sending:
                        self.run_status.configure(
                            text=(
                                "Sinal periódico enviado ao painel; "
                                "o conteúdo da tela foi mantido."
                            )
                        )
                    continue
                if status == "heartbeat_error":
                    self.heartbeat_running = False
                    if self.panel_writer is not None:
                        self.panel_writer.close()
                        self.panel_writer = None
                    self.auto_running = False
                    self._cancel_metrics_refresh()
                    self.next_update_at = None
                    self._cancel_scheduled_update()
                    self._cancel_countdown()
                    self.run_status.configure(
                        text=f"Falha ao manter a comunicação com o painel: {message}"
                    )
                    messagebox.showerror(
                        "Falha na comunicação com o painel",
                        "Não foi possível enviar o sinal periódico:\n\n"
                        f"{message}\n\n"
                        "A atualização automática foi parada.",
                        parent=self.root,
                    )
                    self._update_controls()
                    continue
                if status == "metrics_success":
                    self.metrics_update_running = False
                    if self.pending_metric_frame is not None:
                        self.displayed_frame = self.pending_metric_frame
                    self.pending_metric_frame = None
                    if self.image_apply_pending and self.auto_running:
                        self.image_apply_pending = False
                        self._begin_send()
                    else:
                        self._update_controls()
                    continue
                if status == "metrics_error":
                    self.metrics_update_running = False
                    self.pending_metric_frame = None
                    self.image_apply_pending = False
                    self.auto_running = False
                    self._cancel_metrics_refresh()
                    self.next_update_at = None
                    self._cancel_scheduled_update()
                    self._cancel_countdown()
                    if self.panel_writer is not None:
                        self.panel_writer.close()
                        self.panel_writer = None
                    self.run_status.configure(
                        text=f"Atualização rápida das métricas falhou: {message}"
                    )
                    messagebox.showerror(
                        "Falha ao atualizar métricas no painel",
                        "O envio rápido das métricas falhou:\n\n"
                        f"{message}\n\n"
                        "A atualização automática foi parada.",
                        parent=self.root,
                    )
                    self._update_controls()
                    continue

                self.sending = False
                if status == "error":
                    self.pending_background_pixels = None
                    self.pending_frame = None
                    self.image_apply_pending = False
                    self.auto_running = False
                    self._cancel_metrics_refresh()
                    self.next_update_at = None
                    self._cancel_scheduled_update()
                    self._cancel_countdown()
                    self.run_status.configure(
                        text=f"Envio interrompido: {message}. Não houve nova tentativa."
                    )
                    messagebox.showerror(
                        "Falha ao enviar ao painel",
                        f"O envio falhou:\n\n{message}\n\n"
                        "A atualização automática foi parada e não haverá "
                        "tentativa automática.",
                        parent=self.root,
                    )
                    self._update_controls()
                    continue

                self.displayed_background_pixels = self.pending_background_pixels
                self.pending_background_pixels = None
                self.displayed_frame = self.pending_frame
                self.pending_frame = None
                self.frame_count += 1
                if self.heartbeat_id is None:
                    self.heartbeat_id = self.root.after(
                        HEARTBEAT_INTERVAL_MS,
                        self._heartbeat_tick,
                    )
                self.run_status.configure(
                    text=(
                        f"Quadro completo {self.frame_count} enviado; "
                        "conexão com o painel permanece aberta."
                    )
                )
                if self.auto_running:
                    if self.mode.get() == "folder":
                        elapsed = int(
                            (time.monotonic() - self.last_frame_started) * 1000
                        )
                        delay = max(
                            0,
                            self._selected_slideshow_interval_ms() - elapsed,
                        )
                        self._schedule_next_update(delay)
                    else:
                        self.run_status.configure(
                            text=(
                                "Imagem fixa ativa; métricas atualizadas "
                                "a cada 0,8 segundo. Clique em Parar para encerrar."
                            )
                        )
                        self._update_controls()
                else:
                    self._update_controls()
        except queue.Empty:
            pass
        polling_delay = (
            100
            if self.sending or self.metrics_update_running or self.heartbeat_running
            else 1000
        )
        self.root.after(polling_delay, self._poll_send_results)

    def _schedule_next_update(self, delay_ms: int) -> None:
        self._cancel_scheduled_update()
        self._cancel_countdown()
        self.next_update_at = time.monotonic() + delay_ms / 1000
        self.next_update_id = self.root.after(delay_ms, self._automatic_refresh)
        self._update_countdown()

    def _update_countdown(self) -> None:
        self.countdown_id = None
        if not self.auto_running or self.next_update_at is None or self.sending:
            return
        remaining = max(0, int(self.next_update_at - time.monotonic() + 0.999))
        self.run_status.configure(
            text=f"Quadro {self.frame_count} enviado. "
            f"Próxima atualização em {remaining} s. Clique em Parar para encerrar."
        )
        if remaining > 0:
            self.countdown_id = self.root.after(1000, self._update_countdown)

    def _cancel_scheduled_update(self) -> None:
        if self.next_update_id is not None:
            self.root.after_cancel(self.next_update_id)
            self.next_update_id = None

    def _cancel_countdown(self) -> None:
        if self.countdown_id is not None:
            self.root.after_cancel(self.countdown_id)
            self.countdown_id = None

    def _cancel_metrics_refresh(self) -> None:
        if self.metrics_refresh_id is not None:
            self.root.after_cancel(self.metrics_refresh_id)
            self.metrics_refresh_id = None

    @staticmethod
    def _create_tray_image() -> Image.Image:
        image = Image.new("RGBA", (64, 64), (23, 23, 23, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle(
            (5, 5, 59, 59),
            radius=12,
            fill=(32, 115, 145, 255),
        )
        draw.rounded_rectangle(
            (14, 13, 50, 42),
            radius=3,
            outline=(255, 255, 255, 255),
            width=3,
        )
        draw.line((23, 49, 41, 49), fill=(255, 255, 255, 255), width=3)
        draw.line((32, 42, 32, 49), fill=(255, 255, 255, 255), width=3)
        return image

    def _start_tray_icon(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem(
                "Abrir Painel S1",
                lambda _icon, _item: self.tray_actions.put("show"),
                default=True,
            ),
            pystray.MenuItem(
                "Sair",
                lambda _icon, _item: self.tray_actions.put("close"),
            ),
        )
        self.tray_icon = pystray.Icon(
            "painel_s1_local",
            self._create_tray_image(),
            "Painel S1 local",
            menu,
        )
        self.tray_icon.run_detached()

    def _poll_tray_actions(self) -> None:
        self.tray_poll_id = None
        try:
            while True:
                action = self.tray_actions.get_nowait()
                if action == "show":
                    self._show_from_tray()
                elif action == "close":
                    self._close()
                    if self.tray_icon is None:
                        return
        except queue.Empty:
            pass
        self.tray_poll_id = self.root.after(100, self._poll_tray_actions)

    def _minimize_to_tray(self, _event: tk.Event | None = None) -> None:
        if self.root.state() == "iconic":
            self.root.after_idle(self.root.withdraw)

    def _hide_to_tray(self) -> None:
        self.root.withdraw()

    def _show_from_tray(self) -> None:
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def _close(self) -> None:
        if (
            self.sending
            or self.metrics_update_running
            or self.heartbeat_running
            or self.preparation_running
        ):
            self._show_from_tray()
            messagebox.showwarning(
                "Comunicação em andamento",
                "Aguarde o envio atual ao painel terminar antes de fechar o aplicativo.",
                parent=self.root,
            )
            return
        self.auto_running = False
        self._cancel_scheduled_update()
        self._cancel_countdown()
        self._cancel_metrics_refresh()
        if self.tray_poll_id is not None:
            self.root.after_cancel(self.tray_poll_id)
            self.tray_poll_id = None
        if self.heartbeat_id is not None:
            self.root.after_cancel(self.heartbeat_id)
            self.heartbeat_id = None
        if self.panel_writer is not None:
            self.panel_writer.close()
            self.panel_writer = None
        self.metrics.close()
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    S1PanelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
