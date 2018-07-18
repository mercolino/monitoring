import lib.sqlite as db
import datetime
import argparse
import logging
import yaml
import sys
import requests
import json

LEVEL = {'debug': logging.DEBUG,
         'info': logging.INFO,
         'warning': logging.WARNING,
         'error': logging.ERROR,
         'critical': logging.CRITICAL}

def parse_prefixes_from_as(resp, logger):
    logger.info("Parsing Data")
    v4_prefixes = resp['data']['prefixes']['v4']['originating']
    v6_prefixes = resp['data']['prefixes']['v6']['originating']
    query_time = resp['data']['query_time']
    return v4_prefixes, v6_prefixes, query_time


if __name__ == "__main__":

    # Create the parser for the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="Turn on verbosity on the output", action="store_true", default=False)
    parser.add_argument("--ssl", help="Enforce ssl verification", action="store_true", default=False)
    parser.add_argument("--list_prefixes", help="List prefixes announced by the AS", action="store_true", default=False)
    parser.add_argument("-a", "--autonomous_system", help="Specify the BGP Autonomous system to find out if prefixes are announced", action="store")

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
    logger = logging.getLogger('bgp_check')
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

    # Building the URL
    if args.list_prefixes:
        url = 'https://stat.ripe.net/data/ris-prefixes/data.json?resource=%s&list_prefixes=true' %args.autonomous_system
    else:
        url = 'https://stat.ripe.net/data/ris-prefixes/data.json?resource=%s&list_prefixes=false' %args.autonomous_system

    logger.info("Sending GET request to RIPE")
    r = requests.get(url, verify=args.ssl)

    logger.info("Checking the result status code")
    if r.status_code == 200:
        logger.info("Status code 200 retrieving data")
        response = r.json()
        v4_prefx, v6_prefx, qtime = parse_prefixes_from_as(response, logger)
    else:
        logger.Error("Error connecting to the url status code %i" %r.status_code)
        sys.exit(1)

    # Create database
    logger.info('Creating Database if does not exist')
    p = db.SQLite(db_name)
    # Create table
    logger.info('Creating bgp_table if does not exist')
    p.create_table('bgp_table', ('id integer PRIMARY KEY', 'created_at DATETIME', 'v4_prefixes text',
                                 'v6_prefixes text', 'query_time text'))
    # Insert data in database table
    logger.info('Inserting data in bgp_table')
    p.insert('bgp_table', (datetime.datetime.utcnow(), json.dumps(v4_prefx), json.dumps(v6_prefx),  qtime))
    p.close()