import ctypes
import math
import os
import shutil
import time
from ctypes import wintypes
from pathlib import Path


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


PDH_FMT_DOUBLE = 0x00000200
PDH_CSTATUS_VALID_DATA = 0x00000000
PDH_CSTATUS_NEW_DATA = 0x00000001
CPU_COUNTER_PATH = r"\Processor Information(_Total)\% Processor Utility"


class PDH_FMT_COUNTERVALUE_DOUBLE(ctypes.Structure):
    _fields_ = [
        ("CStatus", wintypes.DWORD),
        ("doubleValue", ctypes.c_double),
    ]


def normalize_cpu_percent(value: float, counter_status: int) -> float:
    if counter_status not in {PDH_CSTATUS_VALID_DATA, PDH_CSTATUS_NEW_DATA}:
        raise OSError(f"Contador de CPU inválido (status 0x{counter_status:08X}).")
    if not math.isfinite(value):
        raise OSError("O contador do Windows retornou um valor de CPU inválido.")
    return max(0.0, min(100.0, value))


class WindowsMetrics:
    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError("Este aplicativo usa APIs nativas do Windows.")

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._pdh = ctypes.WinDLL("pdh", use_last_error=True)
        self._query = ctypes.c_void_p()
        self._cpu_counter = ctypes.c_void_p()

        self._pdh.PdhOpenQueryW.argtypes = [
            wintypes.LPCWSTR,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self._pdh.PdhOpenQueryW.restype = wintypes.LONG
        self._check_pdh(
            self._pdh.PdhOpenQueryW(None, 0, ctypes.byref(self._query)),
            "abrir consulta de desempenho",
        )

        self._pdh.PdhAddEnglishCounterW.argtypes = [
            ctypes.c_void_p,
            wintypes.LPCWSTR,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self._pdh.PdhAddEnglishCounterW.restype = wintypes.LONG
        try:
            self._check_pdh(
                self._pdh.PdhAddEnglishCounterW(
                    self._query,
                    CPU_COUNTER_PATH,
                    0,
                    ctypes.byref(self._cpu_counter),
                ),
                "registrar contador de utilização da CPU",
            )
        except OSError:
            self.close()
            raise

        self._pdh.PdhCollectQueryData.argtypes = [ctypes.c_void_p]
        self._pdh.PdhCollectQueryData.restype = wintypes.LONG
        self._pdh.PdhGetFormattedCounterValue.argtypes = [
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(PDH_FMT_COUNTERVALUE_DOUBLE),
        ]
        self._pdh.PdhGetFormattedCounterValue.restype = wintypes.LONG
        self._pdh.PdhCloseQuery.argtypes = [ctypes.c_void_p]
        self._pdh.PdhCloseQuery.restype = wintypes.LONG

        self._get_tick_count = kernel32.GetTickCount64
        self._get_tick_count.restype = ctypes.c_ulonglong

        self._global_memory_status = kernel32.GlobalMemoryStatusEx
        self._global_memory_status.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
        self._global_memory_status.restype = wintypes.BOOL
        self._check_pdh(
            self._pdh.PdhCollectQueryData(self._query),
            "inicializar contador total de CPU",
        )
        self._cpu_ready_after = time.monotonic() + 0.5

    @staticmethod
    def _check_pdh(status: int, operation: str) -> None:
        if status != 0:
            raise OSError(f"Falha ao {operation} (PDH status 0x{status:08X}).")

    def _read_cpu_percent(self) -> float | None:
        self._check_pdh(
            self._pdh.PdhCollectQueryData(self._query),
            "coletar contador total de CPU",
        )
        if time.monotonic() < self._cpu_ready_after:
            return None
        formatted = PDH_FMT_COUNTERVALUE_DOUBLE()
        self._check_pdh(
            self._pdh.PdhGetFormattedCounterValue(
                self._cpu_counter,
                PDH_FMT_DOUBLE,
                None,
                ctypes.byref(formatted),
            ),
            "formatar contador total de CPU",
        )
        return normalize_cpu_percent(formatted.doubleValue, formatted.CStatus)

    def read(self) -> dict[str, float | int | None]:
        cpu_percent = self._read_cpu_percent()

        memory = MEMORYSTATUSEX()
        memory.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not self._global_memory_status(ctypes.byref(memory)):
            raise ctypes.WinError(ctypes.get_last_error())

        disk = shutil.disk_usage(Path.home().anchor)
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": float(memory.dwMemoryLoad),
            "memory_used_gb": (memory.ullTotalPhys - memory.ullAvailPhys)
            / (1024**3),
            "memory_total_gb": memory.ullTotalPhys / (1024**3),
            "uptime_seconds": int(self._get_tick_count() // 1000),
            "disk_free_gb": disk.free / (1024**3),
            "disk_total_gb": disk.total / (1024**3),
        }

    def close(self) -> None:
        if getattr(self, "_query", None):
            self._pdh.PdhCloseQuery(self._query)
            self._query = ctypes.c_void_p()
