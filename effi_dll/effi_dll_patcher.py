import ctypes
import os
from memrw.process_handles import global_handle
from memrw.memory_table import mem
from effi_dll.effi_patch_offsets import get_units_patched_offsets, get_buildings_patched_offsets
from GetProcessIDctypes import get_module_base_address

def patch_effi_dll_in_memory(debug=False):
    pid = global_handle.get_pid()
    if not pid:
        return

    # Check the effi.dll
    exe_folder = os.path.dirname(global_handle.get_exe_path())
    effi_dll_path = os.path.join(exe_folder, "effi.dll")
    if effi_dll_path and os.path.isfile(effi_dll_path):
        print(f"[Info] effi.dll exists at: {effi_dll_path}")
    else:
        print(f"[Warning] effi.dll not found in: {exe_folder}.")

    effi_dll_base = get_module_base_address(pid, "effi.dll", debug=debug)
    if not effi_dll_base:
        print(f"[Warning] effi.dll not found!")
        return

    print(f"[Info] effi.dll base address: 0x{effi_dll_base:08X}")
    mem.set_effi_dll_base(effi_dll_base)
    # Must be called after UNITS_TABLE and BUILDINGS_TABLE memories are obtained!!!

    if not mem.UNITS_OWNED_TABLE_CNC or not mem.UNITS_OWNED_TABLE_CNC:
        print(f"[Warning] Haven't obtained units table and buildings table memory addresses, cannot patch.")
        return
    effi_dll_base = mem.get_effi_dll_base()

    units_patched_offsets = get_units_patched_offsets(effi_dll_base)
    buildings_patched_offsets = get_buildings_patched_offsets(effi_dll_base)
    need_patch = False
    for addr in units_patched_offsets:
        units_table_addr = global_handle.read_simple_data(addr, ctypes.c_int32())
        # print(f"units_table_addr: dll: 0x{units_table_addr:08X}, actual: 0x{mem.UNITS_OWNED_TABLE_CNC:08X}")
        if units_table_addr != mem.UNITS_OWNED_TABLE_CNC:
            need_patch = True
    for addr in buildings_patched_offsets:
        buildings_table_addr = global_handle.read_simple_data(addr, ctypes.c_int32())
        # print(f"buildings_table_addr: dll: 0x{buildings_table_addr:08X}, actual: 0x{mem.BUILDINGS_OWNED_TABLE_CNC:08X}")
        if buildings_table_addr != mem.BUILDINGS_OWNED_TABLE_CNC:
            need_patch = True

    if need_patch:
        print(f"[Info] Patching effi.dll in memory...")
        for addr in units_patched_offsets:
            actual_data = global_handle.read_simple_data(addr, ctypes.c_int32())
            global_handle.write_data(addr, ctypes.c_uint32(mem.UNITS_OWNED_TABLE_CNC))
            if debug:
                print(f"Patching 0x{addr:08X}: 0x{actual_data:06X} -> 0x{mem.UNITS_OWNED_TABLE_CNC:06X}")
        print(f"[Info] Units table patched to effi.dll!")
        for addr in buildings_patched_offsets:
            actual_data = global_handle.read_simple_data(addr, ctypes.c_int32())
            global_handle.write_data(addr, ctypes.c_uint32(mem.BUILDINGS_OWNED_TABLE_CNC))
            if debug:
                print(f"Patching 0x{addr:08X}: 0x{actual_data:06X} -> 0x{mem.BUILDINGS_OWNED_TABLE_CNC:06X}")
        print(f"[Info] Buildings table patched to effi.dll!")
