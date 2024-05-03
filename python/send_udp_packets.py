#!/usr/bin/env python3

import socket
import random
import argparse
import struct
# import cmath as m

n = 0  # User to track phase of any sinusoids to be split into packets


def send_packets(args: argparse.Namespace):
    HOST, PORT = args.endpoint.split(':')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # Specify the endpoint of the UDP packets, UDP does not have a connection like TCP does
        sock.connect((HOST, int(PORT)))
        for i in range(args.n_packets):
            msg = create_packet(i, args.packet_size)
            sock.sendall(msg)


def create_packet(packet_number: int, size: int):
    packet = bytearray()  # Preallocate packet
    # Insert packet number in little endian 16 bit int
    packet[:2] = struct.pack('<H', packet_number)

    ### ADD CODE TO SEND DATA OF YOUR CHOICE HERE ###
    # global n
    n_ints = int((size-2)/2)  # Calculate the size
    data = [random.randrange(-2**15, 2**15) for _ in range(n_ints)]
    packet[2:] = struct.pack('h'*len(data), *data)

    return packet


def main():
    # Set up arguments and config
    parser = argparse.ArgumentParser(description='Final Lab UDP Packet Sender',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-n", type=int, dest="n_packets",
                        default="10", help="Number of packets to send")
    parser.add_argument("-s", "--size", type=int, dest="packet_size",
                        default="1026", help="Size of packet in bytes")
    parser.add_argument("-d", "--dest", type=str, dest="endpoint",
                        default="192.168.1.23:25344", help="Destination endpoint")
    args = parser.parse_args()

    send_packets(args)


if __name__ == "__main__":
    main()
