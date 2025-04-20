import ctypes
import ctypes.wintypes

TH32CS_SNAPPROCESS = 0x00000002

# Add the necessary flags
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010  # Flag to include 32-bit modules from a 64-bit process

PROCNAME_MAX = 260
MAX_MODULE_NAME32 = 255
MAX_PATH = 260

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ('dwSize', ctypes.c_ulong),
        ('cntUsage', ctypes.c_ulong),
        ('th32ProcessID', ctypes.c_ulong),
        ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
        ('th32ModuleID', ctypes.c_ulong),
        ('cntThreads', ctypes.c_ulong),
        ('th32ParentProcessID', ctypes.c_ulong),
        ('pcPriClassBase', ctypes.c_long),
        ('dwFlags', ctypes.c_ulong),
        ('szExeFile', ctypes.c_char * PROCNAME_MAX),
    ]

class MODULEENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.wintypes.DWORD),
        ("th32ModuleID", ctypes.wintypes.DWORD),
        ("th32ProcessID", ctypes.wintypes.DWORD),
        ("GlblcntUsage", ctypes.wintypes.DWORD),
        ("ProccntUsage", ctypes.wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", ctypes.wintypes.DWORD),
        ("hModule", ctypes.wintypes.HMODULE),
        ("szModule", ctypes.c_char * (MAX_MODULE_NAME32 + 1)),
        ("szExePath", ctypes.c_char * MAX_PATH),
    ]


pe32 = PROCESSENTRY32()
pe32.dwSize = ctypes.sizeof(PROCESSENTRY32)

def get_d2k_pid():
    return get_process_pid()

def get_process_pid(target_process_names=('dune2000.exe', "dune2000-spawn.exe"), ignore_case=True):
    """
    Strict match against a list (tuple) of process names
    :param target_process_names:
    :param ignore_case:
    :return:
    """
    CreateToolhelp32Snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot
    Process32First = ctypes.windll.kernel32.Process32First
    Process32Next = ctypes.windll.kernel32.Process32Next
    CloseHandle = ctypes.windll.kernel32.CloseHandle

    hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if hSnapshot is None:
        return None

    if not Process32First(hSnapshot, ctypes.byref(pe32)):
        CloseHandle(hSnapshot)
        return None

    d2k_found = False
    d2k_pid = None
    while Process32Next(hSnapshot, ctypes.byref(pe32)):
        try:
            cur_process_name = pe32.szExeFile.decode('utf-8')
            if ignore_case:
                cur_process_name = cur_process_name.lower()
            if cur_process_name in target_process_names:
                if not d2k_found:
                    d2k_found = True
                    d2k_pid = pe32.th32ProcessID
                    print(f"Hooking to process {cur_process_name}")
                else:
                    print(f"Warning! Multiple d2k processes found! {cur_process_name=}, pid={pe32.th32ProcessID}")
        except UnicodeDecodeError:
            # print(pe32.szExeFile)
            continue

    CloseHandle(hSnapshot)
    return d2k_pid


def get_module_base_address(pid, module_name):
    # Combine the flags to get both 64-bit and 32-bit modules
    # This is crucial when a 64-bit process inspects a 32-bit process
    # If we do not include TH32CS_SNAPMODULE32, then effi.dll will not be found!
    snapshot_flags = TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32

    hSnapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(snapshot_flags, pid)
    # Add better error checking for snapshot creation
    if hSnapshot == ctypes.wintypes.HANDLE(-1).value:  # INVALID_HANDLE_VALUE is -1
        error_code = ctypes.GetLastError()
        print(f"[Error] get_module_base_address: Failed to create snapshot for PID {pid}. Error code: {error_code}")
        # No exception here
        return 0

    me32 = MODULEENTRY32()
    me32.dwSize = ctypes.sizeof(MODULEENTRY32)

    found = False
    base_addr = None

    print(f"[Info] Searching for module '{module_name}' in PID {pid}...")  # Added for clarity
    if ctypes.windll.kernel32.Module32First(hSnapshot, ctypes.byref(me32)):
        while True:
            mod_name = me32.szModule.decode("utf-8").rstrip('\x00').lower()
            # Debug
            # print(f"Module name: {mod_name}")
            if mod_name == module_name.lower():
                base_addr = ctypes.cast(me32.modBaseAddr, ctypes.c_void_p).value
                found = True
                break
            if not ctypes.windll.kernel32.Module32Next(hSnapshot, ctypes.byref(me32)):
                break
    ctypes.windll.kernel32.CloseHandle(hSnapshot)
    if not found:
        print(f"[Error] get_module_base_address: Module {module_name} not found in process {pid}")
        return 0
    return base_addr
