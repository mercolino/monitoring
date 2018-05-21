from flask import Flask, jsonify, make_response, abort
import yaml
import os
from lib.sqlite import SQLite

app = Flask(__name__)


@app.errorhandler(404)
def page_not_found(error):
    return make_response(jsonify({'error': error.description}), 404)


@app.route('/api/v1.0/get_last/<type>/<int:n>', methods=['GET'])
def get_last(type, n=1):
    if type == 'ping':
        g = SQLite(db_name)
        g.create_table('ping_table', ('id integer PRIMARY KEY', 'created_at DATE', 'version integer', 'dst_ip text',
                                      'rtt real', 'pkt_sent integer', 'pkt_loss integer'))
        columns = g.get_columns_from_table('ping_table')
        last_data = g.get_last_n('ping_table', n)
        result = []
        for l in last_data:
            data = {}
            i = 0
            for v in l:
                data[columns[i]] = v
                i += 1
            result.append(data)
    elif type == 'tcp':
        g = SQLite(db_name)
        g.create_table('tcp_table', ('id integer PRIMARY KEY', 'created_at DATE', 'version integer', 'url text',
                                  'response_code integer'))
        columns = g.get_columns_from_table('tcp_table')
        last_data = g.get_last_n('tcp_table', n)
        result = []
        for l in last_data:
            data = {}
            i = 0
            for v in l:
                data[columns[i]] = v
                i += 1
            result.append(data)
    else:
        abort(make_response(jsonify(message="Type %s does not exist, only ping or tcp" % type), 404))

    return jsonify(result)

if __name__ == '__main__':
    yaml_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')

    # Load the config.yaml file
    with open(yaml_file, 'r') as f:
        config = yaml.load(f)

    global db_name
    db_name = os.path.join(os.path.dirname(os.path.dirname(__file__)), config['db_name'])

    app.secret_key = config['api']['secret_key']
    app.run(host=config['api']['host'], debug=config['api']['debug'])