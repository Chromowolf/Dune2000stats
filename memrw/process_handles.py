import ctypes

PROCESS_VM_READ = 0x10
PROCESS_VM_WRITE = 0x20  # (Together with 0x0008?) Grant right to get exit code and write
PROCESS_VM_OPERATION = 0x0008  # (Together with 0x20?) Grant right to get exit code and write
PROCESS_QUERY_INFORMATION = 0x0400  # Grant right to get exit code
ALL_ACCESS = 0x1F0FFF

def validate_memory_address(mem_addr):
    if not (0 <= mem_addr <= 0xFFFFFFFF):
        raise ValueError(f"Memory address 0x{mem_addr:08X} is out of range! Should be less than 0xFFFFFFFF.")

class ProcessHandle:
    def __init__(self, pid=None, access_right=PROCESS_VM_READ | PROCESS_QUERY_INFORMATION):
        self._handle = None
        self._pid = pid
        self._access_right = access_right
        self._bytes_read = ctypes.c_uint32(0)  # number of bytes read, used in:
        # WriteReadMemory(...,ctypes.byref(self._bytes_read))
        # Note that, returning self._bytes_read will actually return a reference to the c_uint32 object, which is not good
        # So, always return self._bytes_read.value, which is a python int
        self._exit_code = ctypes.c_uint32(0)

    def __bool__(self):
        return bool(self._handle)

    def __del__(self):
        self.close_handle()

    def open_handle(self, pid=None, access_right=None):
        if self._handle:
            self.close_handle()
            print("Warning, the handle has been opened already! The existing handle has been closed.")
        access_right_used = access_right if access_right else self._access_right
        if pid:
            self._pid = pid

        if not self._pid:
            raise Exception(f"Could not open the handel: pid not defined!")
        self._handle = ctypes.windll.kernel32.OpenProcess(access_right_used, False, self._pid)

        if not self._handle:
            raise Exception(f"Could not open process {self._pid}. Error code: {ctypes.GetLastError()}")

        print(f"Handle hooked to process {self._pid}.")

    def get_exit_code(self):
        ctypes.windll.kernel32.GetExitCodeProcess(self._handle, ctypes.byref(self._exit_code))
        return self._exit_code.value

    # def write_to_memory(self, mem_addr, data):
    #     """
    #     :param mem_addr: the address to write to. A python integer like 0x798538
    #     :param data: any data type in ctype, for example ctype.c_uint32(123), or even C structure object.
    #     """
    #     if self._handle is None:
    #         raise Exception(f"Handle not initialize!")
    #     validate_memory_address(mem_addr)
    #     if not ctypes.windll.kernel32.WriteProcessMemory(self._handle, mem_addr, ctypes.byref(data),
    #                                                      ctypes.sizeof(data), None):
    #         Exception(f"Could not write to process memory 0x{mem_addr:08X}. Error code: {ctypes.GetLastError()}")

    # def write_to_memory_masked(self, mem_addr, data, bitmask):
    #     """
    #     :param mem_addr: the address to write to. A python integer like 0x798538
    #     :param data: any basic data types (instance) in ctype, for example ctype.c_uint32()
    #     :param bitmask: for example 0x00200000 to modify a single bit
    #     """
    #     if self._handle is None:
    #         raise Exception(f"Handle not initialize!")
    #     validate_memory_address(mem_addr)
    #     temp_data = type(data)()
    #     if not ctypes.windll.kernel32.ReadProcessMemory(self._handle, mem_addr,
    #                                                     ctypes.byref(temp_data), ctypes.sizeof(data),
    #                                                     ctypes.byref(self._bytes_read)):
    #         Exception(f"Could not read process memory 0x{mem_addr:08X}. Error code: {ctypes.GetLastError()}")
    #
    #     # Clear the bits to be modified
    #     temp_data.value &= ~bitmask
    #
    #     # Set the bits to be modified
    #     temp_data.value |= (data.value & bitmask)
    #
    #     if not ctypes.windll.kernel32.WriteProcessMemory(self._handle, mem_addr, ctypes.byref(temp_data),
    #                                                      ctypes.sizeof(temp_data), None):
    #         Exception(f"Could not write to process memory 0x{mem_addr:08X}. Error code: {ctypes.GetLastError()}")

    def read_data(self, mem_addr, buffer):
        """
        :param mem_addr: the address to read from. A python integer like 0x798878
        :param buffer: the placeholder for the data being read. any data type in ctype, for example ctype.c_uint32(), or even C structure object.
        :return: the buffer
        """
        if self._handle is None:
            raise Exception(f"Handle not initialize!")
        validate_memory_address(mem_addr)
        if not ctypes.windll.kernel32.ReadProcessMemory(self._handle, mem_addr,
                                                        ctypes.byref(buffer), ctypes.sizeof(buffer),
                                                        ctypes.byref(self._bytes_read)):
            Exception(f"Could not read process memory 0x{mem_addr:08X}. Error code: {ctypes.GetLastError()}")
        return buffer

    read_from_memory = read_data  # alias

    def read_simple_data(self, mem_addr, buffer):
        """
        :param mem_addr: the address to read from. A python integer like 0x798878
        :param buffer: the placeholder for the data being read. any simple data type in ctype, for example ctype.c_uint32(). Cannot be structures!
        :return: the value within the buffer
        """
        if self._handle is None:
            raise Exception(f"Handle not initialize!")
        validate_memory_address(mem_addr)
        if not ctypes.windll.kernel32.ReadProcessMemory(self._handle, mem_addr,
                                                        ctypes.byref(buffer), ctypes.sizeof(buffer),
                                                        ctypes.byref(self._bytes_read)):
            Exception(f"Could not read process memory 0x{mem_addr:08X}. Error code: {ctypes.GetLastError()}")
        return buffer.value

    def get_last_bytes_read(self):
        return self._bytes_read

    def close_handle(self):
        if self._handle is not None:
            if not ctypes.windll.kernel32.CloseHandle(self._handle):
                raise Exception(f"Could not close handle. Error code: {ctypes.GetLastError()}")
            print(f"The handle hooked to process {self._pid} has been closed.")
            self._handle = None


# global_handle = ProcessHandle(access_right=PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION)  # Need operation and write access
# global_handle = ProcessHandle(access_right=PROCESS_VM_READ | PROCESS_VM_OPERATION)  # auto closed after open
global_handle = ProcessHandle()  # Read only
