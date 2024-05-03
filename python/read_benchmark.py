#!/usr/bin/env python3

import ctypes as ct

RADIO_TUNER_TIMER_REG_OFFSET = 0xC
RADIO_PERIPH_ADDRESS = 0x43c00000

c_zyboutils = ct.cdll.LoadLibrary("./libzyboutils.so")


class memHandle(ct.Structure):
    _fields_ = [("virt_addr", ct.c_void_p),
                ("fd", ct.c_int)]


c_zyboutils.map_mem.restype = ct.POINTER(memHandle)
radioPeriphHandle = c_zyboutils.map_mem(RADIO_PERIPH_ADDRESS)


def read_register(offset) -> int:
    val = ct.c_uint()
    ret = c_zyboutils.read_reg(radioPeriphHandle, offset, ct.byref(val))
    if ret == -1:
        print(
            f"Could not devmem read address {RADIO_PERIPH_ADDRESS+RADIO_TUNER_TIMER_REG_OFFSET}")
    value = val.value
    return value


start_time = read_register(RADIO_PERIPH_ADDRESS+RADIO_TUNER_TIMER_REG_OFFSET)
for i in range(2048):
    stop_time = read_register(RADIO_PERIPH_ADDRESS +
                              RADIO_TUNER_TIMER_REG_OFFSET)

c_zyboutils.unmap_mem(radioPeriphHandle)

print(f"Start time: {start_time}")
print(f"Stop time: {stop_time}")
bytes_transferred = 4 * 2048
time_spent = (stop_time-start_time)/125e6
throughput = (bytes_transferred / time_spent)/1e6

print(
    f"You transferred {bytes_transferred} bytes of data in {time_spent} seconds\n")
print(f"Measured Transfer throughput = {throughput} Mbytes/sec\n")
