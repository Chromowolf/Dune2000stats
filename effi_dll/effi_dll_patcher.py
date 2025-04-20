from memrw.process_handles import global_handle
from memrw.memory_table import mem
from effi_dll.effi_patch_offsets import get_units_patched_offsets, get_buildings_patched_offsets
import ctypes

def patch_effi_dll_in_memory():
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
            global_handle.write_data(addr, ctypes.c_uint32(mem.UNITS_OWNED_TABLE_CNC))
            # print(f"Patching units table to: 0x{addr:08X}")
        print(f"[Info] Units table patched to effi.dll!")
        for addr in buildings_patched_offsets:
            global_handle.write_data(addr, ctypes.c_uint32(mem.BUILDINGS_OWNED_TABLE_CNC))
            # print(f"Patching buildings table to: 0x{addr:08X}")
        print(f"[Info] Buildings table patched to effi.dll!")
