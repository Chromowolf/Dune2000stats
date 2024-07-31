import ctypes
from .memory_table import *
from .process_handles import global_handle
import numpy as np
from math import prod

def read_array(addr, elemtype, length):
    array_read = global_handle.read_from_memory(addr, (elemtype * length)())
    return np.array(array_read)


def read_u32_table(base_addr, shape=None):
    """
    :param base_addr: The address where the table is located
    :param shape: A tuple, for example (30, 8)
    :return: An numpy array of shape=shape
    """
    length = 1
    if shape:
        length = prod(shape)
    array_read = global_handle.read_from_memory(base_addr, (ctypes.c_uint32 * length)())
    return np.array(array_read).reshape(shape)


