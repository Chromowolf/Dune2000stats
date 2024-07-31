import ctypes

TH32CS_SNAPPROCESS = 0x00000002
PROCNAME_MAX = 260

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
