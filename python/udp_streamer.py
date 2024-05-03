#!/usr/bin/env python3

import socket
import argparse
import struct
import ctypes as ct
import threading
import traceback
import subprocess
# import cmath as m


class memHandle(ct.Structure):
    _fields_ = [("virt_addr", ct.c_void_p),
                ("fd", ct.c_int)]


SYSCLOCK_FREQ = 125000000.0
PHASE_WIDTH_DECIMAL = 4294967296.0
SAMP_BYTES_PER_PACKET = 1024  # Number of sample data bytes in each packet
SAMPS_PER_PACKET = 256  # Each sample is 4 bytes, so there is 256 samps per packet
PACKET_SIZE = 1026  # Total bytes

RADIO_PERIPH_ADDRESS = 0x43c00000  # Full radio periph
RADIO_TUNER_FAKE_ADC_PINC_OFFSET = 0x0  # Radio freq
RADIO_TUNER_TUNER_PINC_OFFSET = 0x4  # Tune freq
RADIO_TUNER_CONTROL_REG_OFFSET = 0x8  # Radio reset
RADIO_TUNER_TIMER_REG_OFFSET = 0xC  # Benchmarking timer

SAMPLES_SOURCE_ADDRESS = 0x43C10000  # FIFO periph
SAMPLES_SOURCE_WORD_COUNT_OFFSET = 0x0
SAMPLES_SOURCE_CURRENT_SAMPLE = 0x4
# SAMPLES_SOURCE_UNIMPLEMENTED2=2
# SAMPLES_SOURCE_UNIMPLEMENTED3=3

PACKET_NUMBER = 0

# Compile with "gcc -shared -o libzyboutils.so zyboutils.c"
subprocess.run("gcc -shared -o libzyboutils.so zyboutils.c".split(' '))
c_zyboutils = ct.cdll.LoadLibrary("./libzyboutils.so")

c_zyboutils.map_mem.restype = ct.POINTER(memHandle)


def write_register(handle, addr, value) -> None:
    ret = c_zyboutils.write_reg(handle, addr, value)
    if ret == -1:
        print(f"Could not devmem write address {addr}")
    return


def read_register(handle, addr) -> int:
    val = ct.c_uint()
    ret = c_zyboutils.read_reg(handle, addr, ct.byref(val))
    if ret == -1:
        print(f"Could not devmem read address {addr}")
    value = val.value
    return value


def print_packet(packet) -> None:
    packet_number = int.from_bytes(
        packet[0:2], byteorder='little', signed=False)
    data = [int.from_bytes(packet[i:i+2], byteorder='little', signed=True)
            for i in range(2, PACKET_SIZE, 2)]
    print(f"Packet number: {packet_number}")
    print(f"Packet data: {data}")


def get_packet(simpleFifoHandle) -> bytearray:
    global PACKET_NUMBER
    header_bytes = bytearray(struct.pack('<H', PACKET_NUMBER))
    lr_data = [read_register(simpleFifoHandle, SAMPLES_SOURCE_ADDRESS+SAMPLES_SOURCE_CURRENT_SAMPLE)
               for _ in range(SAMPS_PER_PACKET)]
    data_bytes = bytearray(struct.pack('<'+'I'*len(lr_data), *lr_data))
    packet = header_bytes + data_bytes
    # print(f"Packet: {packet}")

    PACKET_NUMBER += 1
    return packet


def set_frequency(radioPeriphHandle, adc_freq: float) -> None:
    pinc = adc_freq/SYSCLOCK_FREQ*PHASE_WIDTH_DECIMAL
    write_register(radioPeriphHandle, RADIO_PERIPH_ADDRESS +
                   RADIO_TUNER_FAKE_ADC_PINC_OFFSET, int(pinc))
    print(f"Wrote phase increment {int(pinc)}")


def set_tune_frequency(radioPeriphHandle, tune_frequency: float) -> None:
    pinc = tune_frequency/SYSCLOCK_FREQ*PHASE_WIDTH_DECIMAL
    write_register(radioPeriphHandle, RADIO_PERIPH_ADDRESS +
                   RADIO_TUNER_TUNER_PINC_OFFSET, int(pinc))
    print(f"Wrote phase increment {int(pinc)}")


def send_packets(dest: str, simpleFifoHandle, shutdown_event: threading.Event) -> None:
    HOST, PORT = dest.split(':')

    while(not shutdown_event.is_set()):
        # Should kick off a read operation from the peripheral
        wordcount = read_register(simpleFifoHandle,
                                  SAMPLES_SOURCE_ADDRESS+SAMPLES_SOURCE_WORD_COUNT_OFFSET)
        # print(f"Available samples: {wordcount}")
        if wordcount >= SAMPS_PER_PACKET:
            packet = get_packet(simpleFifoHandle)
            # print(f"Packet Count: {PACKET_NUMBER}")
            # print_packet(packet)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                # Specify the endpoint of the UDP packets, UDP does not have a connection like TCP does
                sock.connect((HOST, int(PORT)))
                sock.sendall(packet)
        else:
            continue


def start_streaming(args: argparse.Namespace, simpleFifoHandle, thread_handle: threading.Thread, shutdown_event: threading.Event) -> threading.Thread:
    thread_handle = threading.Thread(target=send_packets, args=(
        args.endpoint, simpleFifoHandle, shutdown_event), daemon=True)
    thread_handle.start()

    return thread_handle


def main():
    # Set up arguments and config
    parser = argparse.ArgumentParser(description='Final Lab UDP Packet Sender',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-d", "--dest", type=str, dest="endpoint",
                        default="192.168.1.23:25344", help="Destination endpoint")
    args = parser.parse_args()

    udp_thread_handle = threading.Thread()
    shutdown_event = threading.Event()

    radioPeriphHandle = c_zyboutils.map_mem(RADIO_PERIPH_ADDRESS)
    simpleFifoHandle = c_zyboutils.map_mem(SAMPLES_SOURCE_ADDRESS)

    # Turn radio on and set to an audible tone to start
    write_register(radioPeriphHandle, RADIO_PERIPH_ADDRESS +
                   RADIO_TUNER_CONTROL_REG_OFFSET, 1)
    set_frequency(radioPeriphHandle, 1000)
    set_tune_frequency(radioPeriphHandle, 0)

    while(True):
        try:
            print("Input a command. Press f to set fake ADC frequency, t to set tune frequency, s to toggle streaming, sc for shell command, m to toggle mute, and exit to exit. During streaming, press s then enter to toggle streaming off.")
            command = input()
            if command == "f":
                print("Input desired fake ADC frequency")
                freq = float(input())
                set_frequency(radioPeriphHandle, freq)
            elif command == "t":
                print("Input desired tuner frequency")
                tunefreq = float(input())
                set_tune_frequency(radioPeriphHandle, tunefreq)
            elif command == "s":
                print("")
                if udp_thread_handle.is_alive():
                    print("Toggling streaming off")
                    shutdown_event.set()
                else:
                    print("Toggling streaming on")
                    shutdown_event.clear()
                    udp_thread_handle = start_streaming(
                        args, simpleFifoHandle, udp_thread_handle, shutdown_event)
            elif command == "sc":
                print("Type a shell command and press enter, ex. 'devmem 0x43c0000c'")
                command = input()
                subprocess.run(command.split(' '))
            elif command == "exit":
                print("Ending program")
                c_zyboutils.unmap_mem(radioPeriphHandle)
                c_zyboutils.unmap_mem(simpleFifoHandle)
                break
            elif command == "m":
                mute = read_register(radioPeriphHandle,
                                     RADIO_PERIPH_ADDRESS+RADIO_TUNER_CONTROL_REG_OFFSET)
                if not mute:
                    write_register(radioPeriphHandle, RADIO_PERIPH_ADDRESS +
                                   RADIO_TUNER_CONTROL_REG_OFFSET, 1)
                elif mute:
                    write_register(radioPeriphHandle, RADIO_PERIPH_ADDRESS +
                                   RADIO_TUNER_CONTROL_REG_OFFSET, 0)

        except ...:
            traceback.format_exc()
            # c_zyboutils.unmap_mem(radioPeriphHandle)
            # c_zyboutils.unmap_mem(simpleFifoHandle)


if __name__ == "__main__":
    main()
