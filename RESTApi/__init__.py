from flask import Flask, jsonify, make_response, abort, request
import yaml
import os
import random
import string
from datetime import datetime, timedelta
from lib.sqlite import SQLite

app = Flask(__name__)


@app.errorhandler(404)
def page_not_found(error):
    return make_response(jsonify({'error': error.description}), 404)


@app.route('/api/v1.0/get_token', methods=['POST'])
def get_token():
    # Create the Token
    token = ''.join(random.SystemRandom().choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(48))

    # Create table if does not exists
    d = SQLite(db_name)
    d.create_table('tokens_table', ('id integer PRIMARY KEY', 'token TEXT', 'expiration DATETIME'))

    # Insert token in table
    d.insert('tokens_table', (token, datetime.utcnow() + timedelta(minutes=token_timeout)))

    # Close the database
    d.close()

    # Return JSON response
    return jsonify({'date': datetime.utcnow(), 'token': token, 'expiration': datetime.utcnow() + timedelta(minutes=token_timeout)})


@app.route('/api/v1.0/test_token', methods=['GET'])
def test_token():
    token = request.headers.get('token')
    if token is None:
        abort(make_response(jsonify(error="Unauthorized"), 401))
    else:
        # Create table if does not exists
        d = SQLite(db_name)
        d.create_table('tokens_table', ('id integer PRIMARY KEY', 'token text', 'expiration DATETIME'))

        # Query to check if token is valid
        sql = '''SELECT * FROM tokens_table WHERE token=?'''
        resp = d.query(sql, (token,))

        # Close Database
        d.close()

        # Check if token is valid
        if datetime.utcnow() >= datetime.strptime(resp[0][2], '%Y-%m-%d %H:%M:%S.%f'):
            return jsonify({'date': datetime.now(), 'token': token, 'status': 'Token is Expired!'})
        else:
            return jsonify({'date': datetime.now(), 'token': token, 'status': 'Token is valid'})


@app.route('/api/v1.0/get_last/<mon_type>', defaults={'n': 1}, methods=['GET'])
@app.route('/api/v1.0/get_last/<mon_type>/<int:n>', methods=['GET'])
def get_last(mon_type, n):
    # Get the Token on the request
    token =request.headers.get('token')

    # If no token on the request header abort
    if token is None:
        abort(make_response(jsonify(error="Unauthorized, Token not present"), 401))

    # Continue if token is present
    g = SQLite(db_name)
    g.create_table('tokens_table', ('id integer PRIMARY KEY', 'token text', 'expiration DATETIME'))

    # Query to check if token is valid
    sql = '''SELECT * FROM tokens_table WHERE token=?'''
    resp = g.query(sql, (token,))

    # Check if token is valid
    if datetime.utcnow() >= datetime.strptime(resp[0][2], '%Y-%m-%d %H:%M:%S.%f'):
        # Close Database
        g.close()

        abort(make_response(jsonify(error="Unauthorized, Token not valid"), 401))

    if mon_type == 'ping':
        g.create_table('ping_table', ('id integer PRIMARY KEY', 'created_at DATE', 'version integer', 'dst_ip text',
                                      'rtt real', 'pkt_sent integer', 'pkt_loss integer'))
        columns = g.get_columns_from_table('ping_table')
        last_data = g.get_last_n('ping_table', n)

        # Close Database
        g.close()

        result = []
        for l in last_data:
            data = {}
            i = 0
            for v in l:
                data[columns[i]] = v
                i += 1
            result.append(data)
    elif mon_type == 'tcp':
        g = SQLite(db_name)
        g.create_table('tcp_table', ('id integer PRIMARY KEY', 'created_at DATE', 'version integer', 'url text',
                                  'response_code integer'))
        columns = g.get_columns_from_table('tcp_table')
        last_data = g.get_last_n('tcp_table', n)

        # Close Database
        g.close()

        result = []
        for l in last_data:
            data = {}
            i = 0
            for v in l:
                data[columns[i]] = v
                i += 1
            result.append(data)
    else:
        abort(make_response(jsonify(error="Type %s does not exist, only ping or tcp" % mon_type), 400))

    # Create table if does not exists
    d = SQLite(db_name)
    d.create_table('tokens_table', ('id integer PRIMARY KEY', 'token text', 'expiration DATETIME'))

    # Update the expiration datetime for the token
    sql = '''UPDATE tokens_table SET expiration = ? WHERE token = ?'''
    resp = d.query(sql, (datetime.utcnow() + timedelta(minutes=token_timeout), token))

    # Close Database
    d.close()

    return jsonify(result)


if __name__ == '__main__':
    yaml_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')

    # Load the config.yaml file
    with open(yaml_file, 'r') as f:
        config = yaml.load(f)

    global db_name
    db_name = os.path.join(os.path.dirname(os.path.dirname(__file__)), config['db_name'])

    global token_timeout
    token_timeout = config['api']['token_timeout']

    app.secret_key = config['api']['secret_key']
    app.run(host=config['api']['host'], debug=config['api']['debug'])