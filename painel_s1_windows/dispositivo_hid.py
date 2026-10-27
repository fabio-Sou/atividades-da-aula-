import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass, field


VENDOR_ID = 0x04D9
PRODUCT_ID = 0xFD01
DIGCF_PRESENT = 0x00000002
DIGCF_DEVICEINTERFACE = 0x00000010
ERROR_NO_MORE_ITEMS = 259
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.c_size_t),
    ]


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.DWORD),
        ("VendorID", wintypes.WORD),
        ("ProductID", wintypes.WORD),
        ("VersionNumber", wintypes.WORD),
    ]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wintypes.WORD),
        ("UsagePage", wintypes.WORD),
        ("InputReportByteLength", wintypes.WORD),
        ("OutputReportByteLength", wintypes.WORD),
        ("FeatureReportByteLength", wintypes.WORD),
        ("Reserved", wintypes.WORD * 17),
        ("NumberLinkCollectionNodes", wintypes.WORD),
        ("NumberInputButtonCaps", wintypes.WORD),
        ("NumberInputValueCaps", wintypes.WORD),
        ("NumberInputDataIndices", wintypes.WORD),
        ("NumberOutputButtonCaps", wintypes.WORD),
        ("NumberOutputValueCaps", wintypes.WORD),
        ("NumberOutputDataIndices", wintypes.WORD),
        ("NumberFeatureButtonCaps", wintypes.WORD),
        ("NumberFeatureValueCaps", wintypes.WORD),
        ("NumberFeatureDataIndices", wintypes.WORD),
    ]


@dataclass(frozen=True)
class PanelInterface:
    output_report_bytes: int | None
    device_path: str = field(repr=False)


def _load_apis():
    if os.name != "nt":
        raise OSError("A verificação HID só está disponível no Windows.")

    setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
    hid = ctypes.WinDLL("hid", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    setupapi.SetupDiGetClassDevsW.argtypes = [
        ctypes.POINTER(GUID),
        wintypes.LPCWSTR,
        wintypes.HWND,
        wintypes.DWORD,
    ]
    setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE
    setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.POINTER(GUID),
        wintypes.DWORD,
        ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
    ]
    setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
    setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
    setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
    setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL

    hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
    hid.HidD_GetHidGuid.restype = None
    hid.HidD_GetAttributes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(HIDD_ATTRIBUTES),
    ]
    hid.HidD_GetAttributes.restype = wintypes.BOOL
    hid.HidD_GetPreparsedData.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    hid.HidD_GetPreparsedData.restype = wintypes.BOOL
    hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
    hid.HidD_FreePreparsedData.restype = wintypes.BOOL
    hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
    hid.HidP_GetCaps.restype = ctypes.c_long

    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return setupapi, hid, kernel32


def find_panel_interfaces() -> list[PanelInterface]:
    setupapi, hid, kernel32 = _load_apis()
    hid_guid = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(hid_guid))
    device_info = setupapi.SetupDiGetClassDevsW(
        ctypes.byref(hid_guid),
        None,
        None,
        DIGCF_PRESENT | DIGCF_DEVICEINTERFACE,
    )
    if device_info == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())

    matches: list[PanelInterface] = []
    try:
        index = 0
        while True:
            interface = SP_DEVICE_INTERFACE_DATA()
            interface.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
            found = setupapi.SetupDiEnumDeviceInterfaces(
                device_info,
                None,
                ctypes.byref(hid_guid),
                index,
                ctypes.byref(interface),
            )
            if not found:
                error = ctypes.get_last_error()
                if error == ERROR_NO_MORE_ITEMS:
                    break
                raise ctypes.WinError(error)
            index += 1

            required_size = wintypes.DWORD()
            setupapi.SetupDiGetDeviceInterfaceDetailW(
                device_info,
                ctypes.byref(interface),
                None,
                0,
                ctypes.byref(required_size),
                None,
            )
            if not required_size.value:
                continue

            detail_buffer = ctypes.create_string_buffer(required_size.value)
            ctypes.cast(detail_buffer, ctypes.POINTER(wintypes.DWORD))[0] = (
                8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            )
            if not setupapi.SetupDiGetDeviceInterfaceDetailW(
                device_info,
                ctypes.byref(interface),
                detail_buffer,
                required_size,
                ctypes.byref(required_size),
                None,
            ):
                continue

            device_path = ctypes.wstring_at(ctypes.addressof(detail_buffer) + 4)
            handle = kernel32.CreateFileW(
                device_path,
                GENERIC_READ,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                0,
                None,
            )
            if handle == INVALID_HANDLE_VALUE:
                continue

            try:
                attributes = HIDD_ATTRIBUTES()
                attributes.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
                if not hid.HidD_GetAttributes(handle, ctypes.byref(attributes)):
                    continue
                if (
                    attributes.VendorID != VENDOR_ID
                    or attributes.ProductID != PRODUCT_ID
                ):
                    continue

                preparsed_data = ctypes.c_void_p()
                if not hid.HidD_GetPreparsedData(
                    handle, ctypes.byref(preparsed_data)
                ):
                    matches.append(
                        PanelInterface(
                            output_report_bytes=None,
                            device_path=device_path,
                        )
                    )
                    continue
                try:
                    caps = HIDP_CAPS()
                    status = hid.HidP_GetCaps(preparsed_data, ctypes.byref(caps))
                    if status == 0x00110000:
                        matches.append(
                            PanelInterface(
                                output_report_bytes=int(caps.OutputReportByteLength),
                                device_path=device_path,
                            )
                        )
                    else:
                        matches.append(
                            PanelInterface(
                                output_report_bytes=None,
                                device_path=device_path,
                            )
                        )
                finally:
                    hid.HidD_FreePreparsedData(preparsed_data)
            finally:
                kernel32.CloseHandle(handle)
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(device_info)

    return matches
