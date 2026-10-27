import ctypes
import os
import threading
from ctypes import wintypes

from dispositivo_hid import (
    FILE_SHARE_READ,
    FILE_SHARE_WRITE,
    GENERIC_READ,
    OPEN_EXISTING,
    PRODUCT_ID,
    VENDOR_ID,
    HIDD_ATTRIBUTES,
    HIDP_CAPS,
    INVALID_HANDLE_VALUE,
    PanelInterface,
    _load_apis,
    find_panel_interfaces,
)
from protocolo import (
    HID_REPORT_BYTES,
    build_heartbeat_report,
    build_hid_reports,
    build_orientation_report,
    build_refresh_reports,
)


GENERIC_WRITE = 0x40000000


class PanelWriter:
    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError("O painel S1 só pode ser acessado pelo Windows.")

        self._write_lock = threading.Lock()
        interfaces = find_panel_interfaces()
        candidates = [
            interface
            for interface in interfaces
            if interface.output_report_bytes == HID_REPORT_BYTES
        ]
        if len(candidates) != 1:
            raise OSError(
                "Era esperado exatamente um canal HID de saída com relatório de "
                f"{HID_REPORT_BYTES} bytes; encontrados: {len(candidates)}."
            )

        self._interface: PanelInterface = candidates[0]
        self._setupapi, self._hid, self._kernel32 = _load_apis()
        self._kernel32.WriteFile.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
        ]
        self._kernel32.WriteFile.restype = wintypes.BOOL
        self._handle = self._kernel32.CreateFileW(
            self._interface.device_path,
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if self._handle == INVALID_HANDLE_VALUE:
            self._handle = None
            raise ctypes.WinError(ctypes.get_last_error())

        try:
            self._validate_device()
        except OSError:
            self.close()
            raise

    def _validate_device(self) -> None:
        attributes = HIDD_ATTRIBUTES()
        attributes.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
        if not self._hid.HidD_GetAttributes(
            self._handle, ctypes.byref(attributes)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        if attributes.VendorID != VENDOR_ID or attributes.ProductID != PRODUCT_ID:
            raise OSError("O dispositivo HID mudou desde a verificação inicial.")

        preparsed_data = ctypes.c_void_p()
        if not self._hid.HidD_GetPreparsedData(
            self._handle, ctypes.byref(preparsed_data)
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            caps = HIDP_CAPS()
            status = self._hid.HidP_GetCaps(
                preparsed_data,
                ctypes.byref(caps),
            )
            if status != 0x00110000:
                raise OSError(
                    "Não foi possível validar os descritores HID "
                    f"(status 0x{status:08X})."
                )
            if caps.OutputReportByteLength != HID_REPORT_BYTES:
                raise OSError(
                    "O tamanho do relatório mudou; nenhum quadro foi enviado."
                )
        finally:
            self._hid.HidD_FreePreparsedData(preparsed_data)

    def send(self, frame: bytes) -> None:
        with self._write_lock:
            for report in build_hid_reports(frame):
                self._write_report_locked(report)

    def heartbeat(self) -> None:
        with self._write_lock:
            self._write_report_locked(build_heartbeat_report())

    def set_orientation(self, orientation: str) -> None:
        with self._write_lock:
            self._write_report_locked(build_orientation_report(orientation))

    def send_metric_updates(
        self,
        frame: bytes,
        previous_frame: bytes | None = None,
    ) -> None:
        with self._write_lock:
            for report in build_refresh_reports(frame, previous_frame):
                self._write_report_locked(report)

    def _write_report_locked(self, report: bytes) -> None:
        if self._handle is None:
            raise OSError("A conexão HID com o painel está fechada.")
        buffer = ctypes.create_string_buffer(report)
        written = wintypes.DWORD()
        if not self._kernel32.WriteFile(
            self._handle,
            buffer,
            len(report),
            ctypes.byref(written),
            None,
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        if written.value != len(report):
            raise OSError(
                f"Relatório incompleto: {written.value} de {len(report)} bytes."
            )

    def close(self) -> None:
        with self._write_lock:
            if self._handle is not None:
                self._kernel32.CloseHandle(self._handle)
                self._handle = None


def send_frame(frame: bytes) -> None:
    if os.name != "nt":
        raise OSError("O envio ao painel só está disponível no Windows.")
    writer = PanelWriter()
    try:
        writer.send(frame)
    finally:
        writer.close()
