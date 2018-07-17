import lib.sqlite as db
import datetime
import dns.resolver
import dns.query
import dns.dnssec
import argparse
import logging
import yaml
import sys

LEVEL = {'debug': logging.DEBUG,
         'info': logging.INFO,
         'warning': logging.WARNING,
         'error': logging.ERROR,
         'critical': logging.CRITICAL}


if __name__ == "__main__":

    # Create the parser for the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Turn on verbosity on the output", action="store_true", default=False)
    parser.add_argument("-d", dest="domain", help="Specify the domain to check", action="store")
    parser.add_argument("--dnssec", help="Check for DNSSEC", action="store_true", default = False)
    parser.add_argument("--ns1", help="Specify the first name server to use [Optional]", action="store")
    parser.add_argument("--ns2", help="Specify the second name server to use [Optional]", action="store")

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
    logger = logging.getLogger('dns_check')
    logger.setLevel(level=log_level)
    handler = logging.StreamHandler()
    handler_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                          datefmt='%m/%d/%Y %I:%M:%S %p')
    handler.setFormatter(handler_formatter)
    logger.addHandler(handler)

    # Turn logger on or off depending on the arguments
    logger.disabled = not args.verbose

    # Set the database name
    try:
        db_name = config["db_name"]
    except:
        logger.critical('You have to configure the database name on the config file')
        sys.exit(1)

    # Create DNS resolver object
    dns_resolver = dns.resolver.Resolver()

    # Add NS on the resolver object if they were specified on the arguments
    if (args.ns1 is not None) or (args.ns2 is not None):
        logger.info("Name servers specified")
        dns_resolver.nameservers = [args.ns1, args.ns2]
    else:
        logger.info("Name servers NOT specified")

    logger.info("Query for MX Servers")
    # Query NS for the MX Records
    try:
        answer_mx = dns_resolver.query(args.domain, dns.rdatatype.MX)
    except Exception as e:
        logger.error("There was a problem trying to get the MX records of the domain %s" %(args.domain))
        logger.error(e)
        mx_servers_ipv4 = [('ERROR', 'ERROR')]
        mx_servers_ipv6 = [('ERROR', 'ERROR')]
    else:
        mx_servers_ipv4 = []
        mx_servers_ipv6 = []
        # Process the MX exchange servers and resolve the ip address to each one of them
        for rdata_mx in answer_mx:
            # Processing ipv4 addresses
            logger.info("Processing %s ipv4 exchange server" %(rdata_mx.exchange))
            try:
                answer = dns_resolver.query(rdata_mx.exchange, dns.rdatatype.A)
            except Exception as e:
                logger.error("There was a problem trying to get the A records of %s" %(rdata_mx.exchange))
                logger.error(e)
                mx_servers_ipv4.append((rdata_mx.exchange, 'N/A'))
            for rdata in answer:
                mx_servers_ipv4.append((rdata_mx.exchange, rdata))
            # Processing ipv6 addresses
            logger.info("Processing %s ipv6 exchange server" % (rdata_mx.exchange))
            try:
                answer = dns_resolver.query(rdata_mx.exchange, dns.rdatatype.AAAA)
            except Exception as e:
                logger.error("There was a problem trying to get the AAAAA records of %s" % (rdata_mx.exchange))
                logger.error(e)
                mx_servers_ipv6.append((rdata_mx.exchange, 'N/A'))
            for rdata in answer:
                mx_servers_ipv6.append((rdata_mx.exchange, rdata))

    logger.info("Query for NS Servers")
    # Query NS for the NS Records of the Domain
    try:
        answer_ns = dns_resolver.query(args.domain, dns.rdatatype.NS)
    except Exception as e:
        logger.error("There was a problem trying to get the NS records of the domain %s" % (args.domain))
        logger.error(e)
        ns_servers_ipv4 = [('ERROR', 'ERROR')]
        ns_servers_ipv6 = [('ERROR', 'ERROR')]
    else:
        ns_servers_ipv4 = []
        ns_servers_ipv6 = []
        # Process the NS servers and resolve the ip address to each one of them
        for rdata_ns in answer_ns:
            # Processing IPv4 Addresses
            logger.info("Processing %s ipv4 nameserver" % (rdata_ns.to_text()))
            try:
                answer = dns_resolver.query(rdata_ns.to_text(), dns.rdatatype.A)
            except Exception as e:
                logger.error("There was a problem trying to get the A records of %s" % (rdata_ns.to_text()))
                logger.error(e)
                ns_servers_ipv4.append((rdata_ns.to_text(), 'N/A'))
            for rdata in answer:
                ns_servers_ipv4.append((rdata_ns.to_text(), rdata))
            # Processing Ipv6 Addresses
            logger.info("Processing %s ipv6 nameserver" % (rdata_ns.to_text()))
            try:
                answer = dns_resolver.query(rdata_ns.to_text(), dns.rdatatype.AAAA)
            except Exception as e:
                logger.error("There was a problem trying to get the AAAA records of %s" % (rdata_ns.to_text()))
                logger.error(e)
                ns_servers_ipv6.append((rdata_ns.to_text(), 'N/A'))
            for rdata in answer:
                ns_servers_ipv6.append((rdata_ns.to_text(), rdata))

    logger.info("Query for SOA Record")
    # Query NS for the SOA Record
    try:
        answer_soa = dns_resolver.query(args.domain, dns.rdatatype.SOA)
    except Exception as e:
        logger.error("There was a problem trying to get the SOA records of the domain %s" % (args.domain))
        logger.error(e)
        soa_record = 'Error'
    else:
        soa_record = answer_soa.response.to_text()
        primary_ns = answer_soa.rrset[0].mname

    # logger.info("Query for A Records")
    # # Query NS for the A Record
    # try:
    #     print primary_ns
    #     query = dns.message.make_query(args.domain, dns.rdatatype.A)
    #     answer_a = dns.query.udp(query, primary_ns)
    # except Exception as e:
    #     logger.error("There was a problem trying to get the A records of the domain %s" % (args.domain))
    #     logger.error(e)
    #     a_record = 'Error'
    # else:
    #     print answer_a


    for server in mx_servers_ipv4:
        print "The domain %s has the %s Exchange server with an ipv4 address of %s" %(args.domain, server[0], server[1])
    for server in mx_servers_ipv6:
        print "The domain %s has the %s Exchange server with an ipv6 address of %s" %(args.domain, server[0], server[1])

    for server in ns_servers_ipv4:
        print "The domain %s has the %s Nameserver with an ipv4 address of %s" %(args.domain, server[0], server[1])
    for server in ns_servers_ipv6:
        print "The domain %s has the %s Nameserver with an ipv6 address of %s" %(args.domain, server[0], server[1])