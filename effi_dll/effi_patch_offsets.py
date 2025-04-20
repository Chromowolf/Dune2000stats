units_patched_offsets = [
    0x3175, 0x31CB, 0x3224, 0x327D, 0x32D6,
    0x332F, 0x3388, 0x33E1, 0x34CD, 0x352C,
    0x358B, 0x35EA, 0x364C, 0x36AB, 0x370A,
    0x3769, 0x37C8, 0x3827, 0x3886, 0x38E5,
    0x3944,
]
buildings_patched_offsets = [0x340B, 0x3438, 0x3467]

text_section_file_offset = 1024
text_section_virtual_offset = 0x1000

def get_units_patched_offsets(effi_dll_base_addr):
    return [
        effi_dll_base_addr + ofs - text_section_file_offset + text_section_virtual_offset for ofs in units_patched_offsets
    ]

def get_buildings_patched_offsets(effi_dll_base_addr):
    return [
        effi_dll_base_addr + ofs - text_section_file_offset + text_section_virtual_offset for ofs in buildings_patched_offsets
    ]


# Debug
# if __name__ == "__main__":
#     for a in get_units_patched_offsets(0x542A0000):
#         print(f"0x{a:08X}")
#     print()
#     for a in get_buildings_patched_offsets(0x542A0000):
#         print(f"0x{a:08X}")
