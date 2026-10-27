import queue
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import app as app_module
from app import S1PanelApp


class SingleInstanceTests(unittest.TestCase):
    def setUp(self):
        self.previous_mutex = app_module._instance_mutex
        app_module._instance_mutex = None

    def tearDown(self):
        app_module._instance_mutex = self.previous_mutex

    def test_acquires_named_mutex_for_first_instance(self):
        kernel32 = Mock()
        kernel32.CreateMutexW.return_value = 123

        with (
            patch.object(app_module.os, "name", "nt"),
            patch.object(app_module.ctypes, "WinDLL", return_value=kernel32),
            patch.object(app_module.ctypes, "get_last_error", return_value=0),
        ):
            self.assertTrue(app_module.acquire_single_instance())

        self.assertEqual(app_module._instance_mutex, 123)
        kernel32.CreateMutexW.assert_called_once_with(
            None,
            False,
            app_module.INSTANCE_MUTEX_NAME,
        )

    def test_rejects_duplicate_instance_and_shows_message(self):
        kernel32 = Mock()
        kernel32.CreateMutexW.return_value = 456
        user32 = Mock()

        with (
            patch.object(app_module.os, "name", "nt"),
            patch.object(
                app_module.ctypes,
                "WinDLL",
                side_effect=[kernel32, user32],
            ),
            patch.object(
                app_module.ctypes,
                "get_last_error",
                return_value=app_module.ERROR_ALREADY_EXISTS,
            ),
        ):
            self.assertFalse(app_module.acquire_single_instance())

        self.assertIsNone(app_module._instance_mutex)
        kernel32.CloseHandle.assert_called_once_with(456)
        user32.MessageBoxW.assert_called_once()


class FakeRoot:
    def __init__(self):
        self.callbacks = {}
        self.cancelled = []
        self.next_id = 1

    def after(self, delay_ms, callback):
        callback_id = f"after-{self.next_id}"
        self.next_id += 1
        self.callbacks[callback_id] = (delay_ms, callback)
        return callback_id

    def after_cancel(self, callback_id):
        self.cancelled.append(callback_id)
        self.callbacks.pop(callback_id, None)


class FakeTrayRoot:
    def __init__(self, window_state):
        self.window_state = window_state
        self.idle_callbacks = []
        self.after_calls = []
        self.cancelled = []
        self.next_id = 0
        self.withdrawn = False
        self.deiconified = False
        self.lifted = False
        self.focused = False

    def state(self, value=None):
        if value is not None:
            self.window_state = value
        return self.window_state

    def after_idle(self, callback):
        self.idle_callbacks.append(callback)

    def after(self, delay_ms, callback):
        self.next_id += 1
        callback_id = f"tray-after-{self.next_id}"
        self.after_calls.append((delay_ms, callback))
        return callback_id

    def after_cancel(self, callback_id):
        self.cancelled.append(callback_id)

    def withdraw(self):
        self.withdrawn = True

    def deiconify(self):
        self.deiconified = True

    def lift(self):
        self.lifted = True

    def focus_force(self):
        self.focused = True


class FakeStatus:
    def __init__(self):
        self.text = ""

    def configure(self, *, text):
        self.text = text


class FakeWidget:
    def __init__(self):
        self.state = None

    def configure(self, *, state):
        self.state = state


class ImmediateThread:
    def __init__(self, *, target, args, daemon):
        self.target = target
        self.args = args

    def start(self):
        self.target(*self.args)


class FakeMode:
    def __init__(self, mode):
        self.value = mode

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class AutoRefreshTests(unittest.TestCase):
    def test_folder_image_filter_accepts_jpeg_extensions(self):
        self.assertTrue({".jpg", ".jpeg"}.issubset(app_module.IMAGE_SUFFIXES))

    def make_app(self, mode):
        app = S1PanelApp.__new__(S1PanelApp)
        app.root = FakeRoot()
        app.send_results = queue.Queue()
        app.sending = True
        app.metrics_update_running = False
        app.auto_running = True
        app.metrics_refresh_id = None
        app.preparation_running = False
        app.image_apply_pending = False
        app.heartbeat_running = False
        app.heartbeat_id = None
        app.mode = FakeMode(mode)
        app.slideshow_interval = FakeMode("30")
        app.frame_count = 0
        app.last_frame_started = time.monotonic() - 3
        app.next_update_at = None
        app.next_update_id = None
        app.countdown_id = None
        app.displayed_background_pixels = None
        app.pending_background_pixels = None
        app.displayed_frame = None
        app.pending_frame = None
        app.pending_metric_frame = None
        app.run_status = FakeStatus()
        app.selection_controls = []
        app.device_compatible = True
        app.metrics_available = True
        app.folder_images = []
        app.choose_image_button = FakeWidget()
        app.image_layout_combo = FakeWidget()
        app.orientation_combo = FakeWidget()
        app.customize_button = FakeWidget()
        app.slideshow_interval_combo = FakeWidget()
        app.diagnostic_button = FakeWidget()
        app.start_button = FakeWidget()
        app.stop_button = FakeWidget()
        app.library_use_button = FakeWidget()
        app.library_remove_button = FakeWidget()
        app.send_results.put(("success", ""))
        return app

    def test_idle_metric_read_does_not_schedule_repeated_refreshes(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.root = FakeRoot()
        app.metrics = type("Metrics", (), {"read": lambda _self: {}})()
        app.metrics_refresh_id = None
        app.auto_running = False
        app.metrics_available = False
        app.latest_metrics = {}
        app.run_status = FakeStatus()
        app._update_controls = lambda: None
        app._send_live_metric_updates = lambda: None

        app._refresh_metrics()

        self.assertTrue(app.metrics_available)
        self.assertEqual(app.root.callbacks, {})

    def test_continuous_mode_schedules_metric_refresh(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.root = FakeRoot()
        app.metrics = type("Metrics", (), {"read": lambda _self: {}})()
        app.metrics_refresh_id = None
        app.auto_running = True
        app.metrics_available = True
        app.latest_metrics = {}
        app._update_controls = lambda: None
        app._send_live_metric_updates = lambda: None

        app._refresh_metrics()

        self.assertEqual(
            [delay for delay, _ in app.root.callbacks.values()],
            [app_module.REFRESH_MS],
        )

    def test_fixed_image_keeps_metrics_live_without_full_frame_timer(self):
        app = self.make_app("fixed")

        app._poll_send_results()

        delays = [delay for delay, _ in app.root.callbacks.values()]
        self.assertFalse(any(delay >= 6_000 for delay in delays))
        self.assertIn("métricas atualizadas a cada 0,8 segundo", app.run_status.text)
        self.assertEqual(app.frame_count, 1)
        self.assertTrue(app.auto_running)

    def test_folder_mode_uses_selected_slideshow_interval(self):
        app = self.make_app("folder")
        app.slideshow_interval = FakeMode("15")

        app._poll_send_results()

        delays = [delay for delay, _ in app.root.callbacks.values()]
        self.assertTrue(any(11_000 <= delay <= 12_100 for delay in delays))

    def test_folder_mode_schedules_next_image_after_thirty_seconds(self):
        app = self.make_app("folder")

        app._poll_send_results()

        delays = [delay for delay, _ in app.root.callbacks.values()]
        self.assertTrue(any(26_000 <= delay <= 27_100 for delay in delays))

    def test_stop_cancels_pending_update_and_countdown(self):
        app = self.make_app("fixed")
        app.next_update_id = app.root.after(5_000, lambda: None)
        app.countdown_id = app.root.after(1_000, lambda: None)
        app.sending = False

        app._stop_automatic()

        self.assertFalse(app.auto_running)
        self.assertIsNone(app.next_update_at)
        self.assertIn("Atualização automática parada.", app.run_status.text)
        self.assertEqual(len(app.root.cancelled), 2)

    def test_image_selection_remains_available_during_auto(self):
        app = self.make_app("fixed")
        app.sending = False
        app.heartbeat_running = False
        app.metrics_update_running = False

        app._update_controls()

        self.assertEqual(app.choose_image_button.state, "normal")
        self.assertEqual(app.customize_button.state, "disabled")
        self.assertEqual(app.slideshow_interval_combo.state, "disabled")
        self.assertEqual(app.diagnostic_button.state, "disabled")
        self.assertEqual(app.stop_button.state, "normal")
        self.assertEqual(app.library_use_button.state, "normal")
        self.assertEqual(app.library_remove_button.state, "disabled")

    def test_metric_positions_cannot_be_changed_during_continuous_updates(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.auto_running = True
        app.sending = False
        app.metrics_update_running = False
        app.visible_metrics = {"cpu"}
        app.metric_positions = {"cpu": (12, 39)}
        app._set_metric_visible("cpu", False)
        app._set_metric_anchor("cpu", "Inferior direito")

        self.assertEqual(app.visible_metrics, {"cpu"})
        self.assertEqual(app.metric_positions, {"cpu": (12, 39)})

    def test_metric_size_is_capped_to_fit_portrait_width(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.orientation = FakeMode("Em pé")
        app.metric_sizes = {metric: "Extra grande" for metric in app_module.METRIC_LABELS}

        self.assertEqual(app._selected_metric_scale("cpu"), 3)

    def test_individual_metric_sizes_do_not_change_other_metrics(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.orientation = FakeMode("Deitada")
        app.metric_sizes = {metric: "Normal" for metric in app_module.METRIC_LABELS}
        app.metric_positions = {
            "cpu": (12, 39),
            "memory": (12, 75),
            "clock": (196, 43),
            "uptime": (12, 127),
            "disk": (196, 127),
        }
        app.sending = False
        app.auto_running = False
        app.metrics_update_running = False
        app._save_layout_settings = lambda: None
        app._layout_changed = lambda: None
        old_positions = dict(app.metric_positions)

        app._set_metric_size("cpu", "Grande")

        self.assertEqual(app.metric_sizes["cpu"], "Grande")
        self.assertEqual(app.metric_sizes["memory"], "Normal")
        for metric in ("memory", "clock", "uptime", "disk"):
            self.assertEqual(app.metric_positions[metric], old_positions[metric])

    def test_slideshow_interval_accepts_configured_values(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.slideshow_interval = FakeMode("15")

        self.assertEqual(app._selected_slideshow_interval_ms(), 15_000)

    def test_slideshow_interval_rejects_unlisted_values(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.slideshow_interval = FakeMode("7")

        with self.assertRaises(ValueError):
            app._selected_slideshow_interval_ms()

    def test_choosing_image_during_auto_queues_preparation(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.root = FakeRoot()
        selected = []
        app._select_image_path = lambda path: selected.append(path)

        with patch.object(app_module.filedialog, "askopenfilename", return_value="new.png"):
            app._choose_background()

        self.assertEqual(selected, [Path("new.png")])

    def test_image_preparation_completion_activates_cached_image(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.root = FakeRoot()
        app.preparation_results = queue.Queue()
        app.preparation_results.put(("success", ""))
        app.preparation_running = True
        path = Path("ready.png")
        entry = {"kind": "image", "path": str(path)}
        app.pending_preparation = ("image", [path], entry, 0)
        app.image_layout = FakeMode("Preencher")
        app.orientation = FakeMode("Deitada")
        app.image_library = type(
            "Library",
            (),
            {
                "prepare_image": lambda _self, *_args: type(
                    "Prepared",
                    (),
                    {"pixels": b"prepared pixels", "preview_path": Path("ready-cache.png")},
                )()
            },
        )()
        app.mode = FakeMode("folder")
        app.library_progress = FakeWidget()
        app.library_status = type(
            "Status",
            (),
            {"set": lambda _self, _value: None},
        )()
        app.run_status = FakeStatus()
        app.auto_running = False
        app.folder_images = []
        app.folder_index = 0
        app._update_image_label = lambda: None
        app._draw_preview = lambda: None
        app._save_layout_settings = lambda: None
        app._update_controls = lambda: None
        app._queue_background_send = lambda: self.fail("unexpected panel send")

        app._poll_image_preparation()

        self.assertFalse(app.preparation_running)
        self.assertEqual(app.background_path, path)
        self.assertEqual(app.background_pixels, b"prepared pixels")
        self.assertEqual(app.current_preview_path, Path("ready-cache.png"))
        self.assertEqual(app.mode.get(), "fixed")

    def test_image_send_waits_for_in_flight_metric_update(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.root = FakeRoot()
        app.send_results = queue.Queue()
        app.send_results.put(("metrics_success", ""))
        app.auto_running = True
        app.metrics_update_running = True
        app.image_apply_pending = True
        app.sending = False
        app.pending_metric_frame = b"updated frame"
        app.displayed_frame = b"old frame"
        app.heartbeat_running = False
        app.run_status = FakeStatus()
        app._update_controls = lambda: None
        sends = []
        app._begin_send = lambda: sends.append(True)

        app._poll_send_results()

        self.assertEqual(sends, [True])
        self.assertFalse(app.image_apply_pending)
        self.assertFalse(app.metrics_update_running)

    def test_panel_connection_is_reused_between_frames(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.panel_writer = None
        app.send_results = queue.Queue()
        instances = []

        class FakePanelWriter:
            def __init__(self):
                self.frames = []
                instances.append(self)

            def send(self, frame):
                self.frames.append(frame)

            def set_orientation(self, orientation):
                self.orientation = orientation

            def close(self):
                raise AssertionError("A conexão deve permanecer aberta.")

        with patch.object(app_module, "PanelWriter", FakePanelWriter):
            app._send_in_background(b"frame 1")
            app._send_in_background(b"frame 2")

        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].frames, [b"frame 1", b"frame 2"])
        self.assertEqual(
            [app.send_results.get_nowait()[0] for _ in range(2)],
            ["success", "success"],
        )

    def test_heartbeat_is_sent_only_when_a_panel_writer_exists(self):
        class FakePanelWriter:
            def __init__(self):
                self.heartbeat_count = 0

            def heartbeat(self):
                self.heartbeat_count += 1

        app = S1PanelApp.__new__(S1PanelApp)
        app.root = FakeRoot()
        app.panel_writer = FakePanelWriter()
        app.heartbeat_running = False
        app.metrics_update_running = False
        app.sending = False
        app.send_results = queue.Queue()

        with patch.object(app_module.threading, "Thread", ImmediateThread):
            app._heartbeat_tick()

        self.assertEqual(app.panel_writer.heartbeat_count, 1)
        self.assertTrue(app.heartbeat_running)
        self.assertEqual(
            [delay for delay, _ in app.root.callbacks.values()],
            [app_module.HEARTBEAT_INTERVAL_MS],
        )
        self.assertEqual(
            app.send_results.get_nowait(),
            ("heartbeat_success", ""),
        )

    def test_live_metrics_are_sent_as_partial_updates(self):
        class FakePanelWriter:
            def __init__(self):
                self.frames = []

            def send_metric_updates(self, frame, previous_frame):
                self.frames.append((frame, previous_frame))

        app = S1PanelApp.__new__(S1PanelApp)
        app.auto_running = True
        app.sending = False
        app.metrics_update_running = False
        app.preparation_running = False
        app.image_apply_pending = False
        app.panel_writer = FakePanelWriter()
        app.send_results = queue.Queue()
        app.displayed_background_pixels = None
        app.displayed_frame = b"previous frame"
        app._render_current_frame = lambda _pixels: b"live metrics frame"
        app._update_controls = lambda: None

        with patch.object(app_module.threading, "Thread", ImmediateThread):
            app._send_live_metric_updates()

        self.assertEqual(
            app.panel_writer.frames,
            [(b"live metrics frame", b"previous frame")],
        )
        self.assertTrue(app.metrics_update_running)
        self.assertEqual(
            app.send_results.get_nowait(),
            ("metrics_success", ""),
        )


class PreferencePersistenceTests(unittest.TestCase):
    def test_last_image_mode_and_layout_are_persisted_without_starting(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.orientation = FakeMode("Em pé")
        app.image_layout = FakeMode("Ajustar")
        app.mode = FakeMode("folder")
        app.last_image_path = Path("C:/imagens/fixa.jpg")
        app.last_folder_path = Path("C:/imagens/pasta")
        app.last_image_entry = {
            "kind": "image",
            "name": "fixa.jpg",
            "path": str(app.last_image_path),
            "cache_name": "fixa",
            "prepared": {"cache": {"variants": {}}},
        }
        app.last_folder_entry = {
            "kind": "folder",
            "name": "pasta",
            "path": str(app.last_folder_path),
            "cache_name": "pasta",
            "prepared": {},
        }
        app.metric_sizes = {metric: "Normal" for metric in app_module.METRIC_LABELS}
        app.slideshow_interval = FakeMode("30")
        app.visible_metrics = set(app_module.METRIC_LABELS)
        app.metric_positions = {
            metric: (12, 35) for metric in app_module.METRIC_LABELS
        }

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with patch("pathlib.Path.home", return_value=home):
                app._save_layout_settings()

                reopened = S1PanelApp.__new__(S1PanelApp)
                reopened.orientation = FakeMode("Deitada")
                reopened.image_layout = FakeMode(app_module.IMAGE_LAYOUTS[0])
                reopened.mode = FakeMode("fixed")
                reopened.last_image_path = None
                reopened.last_folder_path = None
                reopened.last_image_entry = None
                reopened.last_folder_entry = None
                reopened.metric_sizes = {}
                reopened.slideshow_interval = FakeMode("10")
                reopened.visible_metrics = set()
                reopened.metric_positions = {}
                with patch("pathlib.Path.home", return_value=home):
                    reopened._load_layout_settings()

        self.assertEqual(reopened.orientation.get(), "Em pé")
        self.assertEqual(reopened.image_layout.get(), "Ajustar")
        self.assertEqual(reopened.mode.get(), "folder")
        self.assertEqual(reopened.last_image_path, Path("C:/imagens/fixa.jpg"))
        self.assertEqual(reopened.last_folder_path, Path("C:/imagens/pasta"))
        self.assertEqual(reopened.last_image_entry, app.last_image_entry)
        self.assertEqual(reopened.last_folder_entry, app.last_folder_entry)
        self.assertFalse(getattr(reopened, "auto_running", False))

    def test_restoring_last_image_does_not_add_it_to_library_or_start_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "saved.png"
            image_path.write_bytes(b"placeholder")
            app = S1PanelApp.__new__(S1PanelApp)
            app.mode = FakeMode("fixed")
            app.last_image_path = image_path
            app.last_image_entry = None
            app.image_library = type(
                "Library",
                (),
                {"entries": []},
            )()
            app.run_status = FakeStatus()
            prepared = []
            app._begin_image_preparation = lambda *args: prepared.append(args)

            app._restore_last_selection()

        self.assertEqual(len(prepared), 1)
        self.assertEqual(prepared[0][0], "image")
        self.assertEqual(app.last_image_entry["kind"], "image")
        self.assertEqual(app.image_library.entries, [])
        self.assertFalse(getattr(app, "auto_running", False))


class TrayBehaviorTests(unittest.TestCase):
    def test_minimizing_hides_window_after_tk_finishes_unmapping(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.root = FakeTrayRoot("iconic")

        app._minimize_to_tray()

        self.assertEqual(app.root.idle_callbacks, [app.root.withdraw])
        self.assertFalse(app.root.withdrawn)

    def test_window_close_hides_and_tray_restore_shows_window(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.root = FakeTrayRoot("normal")

        app._hide_to_tray()
        app._show_from_tray()

        self.assertTrue(app.root.withdrawn)
        self.assertTrue(app.root.deiconified)
        self.assertEqual(app.root.state(), "normal")
        self.assertTrue(app.root.lifted)
        self.assertTrue(app.root.focused)

    def test_tray_icon_is_started_with_the_expected_menu_title_and_image(self):
        app = S1PanelApp.__new__(S1PanelApp)
        app.root = FakeTrayRoot("normal")
        app.tray_actions = queue.Queue()
        app.tray_poll_id = None
        created = []

        class FakeTrayIcon:
            def __init__(self, *args):
                self.args = args
                self.started = False
                created.append(self)

            def run_detached(self):
                self.started = True

        with patch.object(app_module.pystray, "Icon", FakeTrayIcon):
            app._start_tray_icon()

        self.assertTrue(created[0].started)
        self.assertEqual(created[0].args[2], "Painel S1 local")
        self.assertEqual(created[0].args[1].size, (64, 64))
        self.assertIs(app.tray_icon, created[0])
        created[0].args[3].items[0](None)
        app._poll_tray_actions()
        self.assertTrue(app.root.deiconified)
        self.assertEqual(app.root.after_calls[0][0], 100)


if __name__ == "__main__":
    unittest.main()
