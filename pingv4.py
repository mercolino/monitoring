import socket
import os
from lib.lib import IP, ICMPv4
import datetime
import threading
import struct
import random
import argparse
import logging
import time

MOD = 1 << 16

def ones_comp_add16(num1,num2):
    result = num1 + num2
    return result if result < MOD else (result+1) % MOD


def calculate_checksum(icmp_packet):
    # Converting packet in hex string
    hex_packet = "".join("%02x" % ord(i) for i in icmp_packet)

    # Create list of 16 bits
    hex_packet_list = []
    for i in range(0, len(hex_packet), 4):
        if i == 4:
            hex_packet_list.append('0000')
        else:
            hex_packet_list.append(hex_packet[i:i+4])

    sum = ones_comp_add16(int(hex_packet_list[0], 16), int(hex_packet_list[1], 16))
    for word in hex_packet_list[2:]:
        sum = ones_comp_add16(sum, int(word, 16))

    return 65535 - sum


def threaded_sender(sock, id, dst_ip, n, logger):

    print "PING %s 48 bytes of data:" %(dst_ip)

    for i in range(0, n):
        header = struct.pack('bbHHh', 8, 0, 0, id, i + 1)
        data = "".join(chr(i) for i in range(65, 65 + 48))

        packet = header + data
        checksum = calculate_checksum(packet)

        header = struct.pack('bbHHh', 8, 0, socket.htons(checksum), id, i + 1)

        logger.info("Sending icmp packet seq %i to %s" %(i+1, dst_ip))
        send_date_list.append(datetime.datetime.utcnow())
        sock.sendto(header + data, (dst_ip, 0))
        time.sleep(1)



def threaded_receiver(sock, timeout, id, n, dst_ip, logger):
    i = 0
    rtt_list = []
    time_left = timeout
    if os.name == 'nt':
        logger.info('Windows OS, enabling RCVALL')
        # receive all packages in windows
        sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
    while i < n:
        sock.settimeout(timeout)
        # Receive Data and send to a thread for processing
        try:
            data, addr = server_socket.recvfrom(65535)
        except socket.timeout:
            pass
        else:
            ip_header = IP(data[0:20])
            if ip_header.src_address == dst_ip:
                icmp_header = ICMPv4(data[20:29])
                if icmp_header.icmp_type == 0 and icmp_header.icmp_code == 0 and icmp_header.id_le == id:
                    rtt = (datetime.datetime.utcnow() - send_date_list[i])
                    rtt = rtt.seconds * 1000 + rtt.microseconds / float(1000)
                    rtt_list.append(rtt)
                    print "%i bytes from %s: icmp_seq=%i ttl=%i time=%i ms" % (len(data[28:]), ip_header.src_address,
                                                                            icmp_header.sequence_le, ip_header.ttl,
                                                                            rtt)
                    i += 1

        try:
            time_left -= (datetime.datetime.utcnow() - send_date_list[i]).total_seconds()
        except:
            pass

        if time_left < 0:
            print "*** Ping timeout ***"
            i += 1
            time_left = timeout

    if os.name =='nt':
        # disabled promiscuous mode in windows
        sock.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        logger.info('Windows OS, disabling RCVALL')

    print "**** %s Ping Statistics ****" % dst_ip
    avg = 0
    for ms in rtt_list:
        avg = avg + ms
    try:
        avg = avg / float(len(rtt_list))
    except ZeroDivisionError:
        print "rtt min/avg/max = */*/*"
    else:
        print "rtt min/avg/max = %0.2f/%0.2f/%0.2f" % (min(rtt_list), avg, max(rtt_list))



if __name__ == "__main__":
    global send_date_list

    send_date_list = []

    # Create the parser for the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Turn on verbosity on the output", action="store_true", default=False)
    parser.add_argument("-s", dest="source", help="Specify the local host ip to bind the ping", action="store",
                        default=socket.gethostbyname(socket.gethostname()))
    parser.add_argument("-n", dest="number", help="Specify the number of packets", action="store", default=3)
    parser.add_argument("-t", dest="timeout", help="Specify the timeout in seconds", action="store", default=2)
    parser.add_argument("dst_ip", help="Specify the destination ip address", action="store")

    args = parser.parse_args()

    # Create and format the logger and the handler for logging
    logger = logging.getLogger('pingv4')
    logger.setLevel(level=logging.INFO)
    handler = logging.StreamHandler()
    handler_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                          datefmt='%m/%d/%Y %I:%M:%S %p')
    handler.setFormatter(handler_formatter)
    logger.addHandler(handler)

    # Turn logger on or off depending on the arguments
    logger.disabled = not args.verbose

    timeout = int(args.timeout)
    number_of_pings = int(args.number)
    src_ip = args.source
    dst_ip = args.dst_ip

    logger.info("Creating Socket!!!")

    # Create the raw socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)

    # Bind the socket
    server_socket.bind((src_ip, 0))

    logger.info("Binding socket to %s" % src_ip)

    id = int((id(timeout) * random.random()) % 65535)

    receive_threads = []
    r = threading.Thread(name="receiver_thread", target=threaded_receiver,
                         args=(server_socket, timeout, id, number_of_pings, dst_ip, logger))
    receive_threads.append(r)
    logger.info("Launching Receiver thread")
    r.start()

    send_threads = []
    s = threading.Thread(name="sender_thread", target=threaded_sender,
                         args=(server_socket, id, dst_ip, number_of_pings, logger))
    send_threads.append(s)
    receive_threads.append(s)
    logger.info("Launching Sender Thread")
    s.start()