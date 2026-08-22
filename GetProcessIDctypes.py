import ctypes
from ctypes import wintypes


TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

MAX_PATH = 260
MAX_MODULE_NAME32 = 255
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

# wintypes.WCHAR: Windows built-in wide character. A very safe and locale-independent approach to get process and module names
# "W" suffix in functions: using wintypes.WCHAR string to directly read process and module names,
#   not raw bytes, to avoid manual decoding

class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * MAX_PATH),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(wintypes.BYTE)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * (MAX_MODULE_NAME32 + 1)),
        ("szExePath", wintypes.WCHAR * MAX_PATH),
    ]


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
CreateToolhelp32Snapshot.restype = wintypes.HANDLE

Process32FirstW = kernel32.Process32FirstW
Process32FirstW.argtypes = (
    wintypes.HANDLE,
    ctypes.POINTER(PROCESSENTRY32W),
)
Process32FirstW.restype = wintypes.BOOL

Process32NextW = kernel32.Process32NextW
Process32NextW.argtypes = (
    wintypes.HANDLE,
    ctypes.POINTER(PROCESSENTRY32W),
)
Process32NextW.restype = wintypes.BOOL

Module32FirstW = kernel32.Module32FirstW
Module32FirstW.argtypes = (
    wintypes.HANDLE,
    ctypes.POINTER(MODULEENTRY32W),
)
Module32FirstW.restype = wintypes.BOOL

Module32NextW = kernel32.Module32NextW
Module32NextW.argtypes = (
    wintypes.HANDLE,
    ctypes.POINTER(MODULEENTRY32W),
)
Module32NextW.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = (wintypes.HANDLE,)
CloseHandle.restype = wintypes.BOOL


def get_d2k_pid():
    return get_process_pid()


def get_process_pid(
    target_process_names=("dune2000.exe", "dune2000-spawn.exe"),
    ignore_case=True,
):
    """
    Strict match against a tuple/list of process names.
    Returns the first matching PID, or None.
    """
    if isinstance(target_process_names, str):
        target_process_names = (target_process_names,)

    if ignore_case:
        target_process_names = {
            name.casefold() for name in target_process_names
        }
    else:
        target_process_names = set(target_process_names)

    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)

    if snapshot == INVALID_HANDLE_VALUE:
        return None

    pe32 = PROCESSENTRY32W()
    pe32.dwSize = ctypes.sizeof(pe32)

    found_pid = None

    try:
        success = Process32FirstW(snapshot, ctypes.byref(pe32))

        while success:
            process_name = pe32.szExeFile
            comparison_name = (
                process_name.casefold()
                if ignore_case
                else process_name
            )

            if comparison_name in target_process_names:
                if found_pid is None:
                    found_pid = pe32.th32ProcessID
                    print(
                        f"Hooking to process {process_name}"
                    )
                else:
                    print(
                        "Warning! Multiple d2k processes found! "
                        f"process_name={process_name!r}, "
                        f"pid={pe32.th32ProcessID}"
                    )

            success = Process32NextW(
                snapshot,
                ctypes.byref(pe32),
            )

    finally:
        CloseHandle(snapshot)

    # noinspection PyUnreachableCode
    return found_pid


def get_module_base_address(pid, module_name, debug=False):
    # Combine the flags to get both 64-bit and 32-bit modules
    # This is crucial when a 64-bit process inspects a 32-bit process
    # If we do not include TH32CS_SNAPMODULE32, then effi.dll will not be found!
    snapshot_flags = (
        TH32CS_SNAPMODULE
        | TH32CS_SNAPMODULE32
    )

    snapshot = CreateToolhelp32Snapshot(snapshot_flags, pid)

    if snapshot == INVALID_HANDLE_VALUE:
        error_code = ctypes.get_last_error()
        print(
            "[Error] get_module_base_address: "
            f"Failed to create snapshot for PID {pid}. "
            f"Error code: {error_code}"
        )
        return 0

    me32 = MODULEENTRY32W()
    me32.dwSize = ctypes.sizeof(me32)

    wanted_name = module_name.casefold()
    module_names_found = []

    print(
        f"[Info] Searching for module "
        f"{module_name!r} in PID {pid}..."
    )

    try:
        success = Module32FirstW(
            snapshot,
            ctypes.byref(me32),
        )

        while success:
            current_name = me32.szModule
            module_names_found.append(current_name)

            if current_name.casefold() == wanted_name:
                return (
                    ctypes.cast(
                        me32.modBaseAddr,
                        ctypes.c_void_p,
                    ).value
                    or 0
                )

            success = Module32NextW(
                snapshot,
                ctypes.byref(me32),
            )

    finally:
        CloseHandle(snapshot)

    # noinspection PyUnreachableCode
    print(
        "[Error] get_module_base_address: "
        f"Module {module_name!r} not found "
        f"in process {pid}."
    )

    # noinspection PyUnreachableCode
    if debug:
        for current_name in module_names_found:
            print(f"Module name: {current_name}")

    # noinspection PyUnreachableCode
    return 0