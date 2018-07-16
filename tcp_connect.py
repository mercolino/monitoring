import socket
import argparse
import lib.sqlite as db
import logging
import sys
import ssl
import yaml
import datetime

LEVEL = {'debug': logging.DEBUG,
         'info': logging.INFO,
         'warning': logging.WARNING,
         'error': logging.ERROR,
         'critical': logging.CRITICAL}

if __name__ == "__main__":

    # Create the parser for the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Turn on verbosity on the output", action="store_true", default=False)
    parser.add_argument("--ssl", help="Use ssl to connect to a https server", action="store_true", default=False)
    parser.add_argument("-s", dest="source", help="Specify the local host ip to bind the ping", action="store",
                        default=socket.gethostbyname(socket.gethostname()))
    parser.add_argument("-t", dest="timeout", help="Specify the timeout in seconds", action="store", default=2)
    parser.add_argument("-6", dest="ipv6", help="Use ipv6", action="store_true", default=False)
    parser.add_argument("-p", dest="port", help="Specify port", action="store", default=80)
    parser.add_argument("--path", help="Specify path", action="store", default='/')
    parser.add_argument("dst_ip", help="Specify the timeout in seconds", action="store")

    args = parser.parse_args()

    # Load the config.yaml file
    with open('config.yaml', 'r') as f:
        config = yaml.load(f)

    # Set the logging level
    try:
        log_level = LEVEL[config["log_level"]]
    except:
        log_level = logging.INFO

    # Create and format the logger and the handler for logging
    logger = logging.getLogger('tcp_connect_v4')
    logger.setLevel(level=log_level)
    handler = logging.StreamHandler()
    handler_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                          datefmt='%m/%d/%Y %I:%M:%S %p')
    handler.setFormatter(handler_formatter)
    logger.addHandler(handler)

    # Turn logger on or off depending on the arguments
    logger.disabled = not args.verbose

    # Set the logging level
    try:
        db_name = config["db_name"]
    except:
        logger.critical('You have to configure the database name on the config file')
        sys.exit(1)

    timeout = int(args.timeout)
    src_ip = args.source
    dst_ip = args.dst_ip
    port = int(args.port)

    logger.info("Creating Socket!!!")

    # Create the raw socket
    if args.ipv6:
        server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    else:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if args.ssl:
        logger.info("Using SSL!!!")
        wrapped_socket = ssl.wrap_socket(server_socket, ssl_version=ssl.PROTOCOL_SSLv23)

    try:
        logger.info("Connecting to %s:%i" %(dst_ip, port))
        # Connecting to dst host
        if args.ssl:
            wrapped_socket.connect((dst_ip, port))
        else:
            server_socket.connect((dst_ip, port))
    except Exception as e:
        logger.critical(e)
        logger.info('Creating Database if does not exist')
        p = db.SQLite(db_name)
        logger.info('Creating tcp_table if does not exist')
        p.create_table('tcp_table', ('id integer PRIMARY KEY', 'created_at DATETIME', 'version integer', 'url text',
                                      'response_code integer'))
        logger.info('Inserting data in tcp_table')
        p.insert('tcp_table', (datetime.datetime.utcnow(), 6 if args.ipv6 else 4, dst_ip + ':' + str(port), 0))
        p.close()
        sys.exit(1)

    logger.info("Sending data to retrieve the webpage")
    if args.ssl:
        wrapped_socket.send('GET %s HTTP/1.1\nHost: %s\r\n'
                            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0\n\n'
                            % (args.path, dst_ip))
    else:
        server_socket.send('GET %s HTTP/1.1\nHost: %s\r\n'
                            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0\n\n'
                            % (args.path, dst_ip))

    data = ''
    server_socket.settimeout(timeout)
    logger.info("Waiting for data")
    while True:
        if args.ssl:
            try:
                d = wrapped_socket.recv(1024)
            except Exception as e:
                logger.info(e)
                server_socket.close()
                break
        else:
            try:
                d = server_socket.recv(1024)
            except socket.timeout:
                logger.info("Receive timeout")
                server_socket.close()
                break
        logger.info("Received 1024 bytes")
        if not d:
            logger.info("Received nothing")
            server_socket.close()
            break
        data += d

    logger.info("Closing Socket")
    server_socket.close()

    print "Response code: %s" % data[9:12]

    logger.info('Creating Database if does not exist')
    p = db.SQLite(db_name)
    logger.info('Creating tcp_table if does not exist')
    p.create_table('tcp_table', ('id integer PRIMARY KEY', 'created_at DATETIME', 'version integer', 'url text',
                                  'response_code integer'))
    logger.info('Inserting data in tcp_table')
    p.insert('tcp_table', (datetime.datetime.utcnow(), 6 if args.ipv6 else 4, dst_ip + ':' + str(port), int(data[9:12])))
    p.close()