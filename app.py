import os
import elasticsearch
import simplejson
from flask import Flask
from flask import Response

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello World!'

@app.route('/user/<username>')
def show_user_profile(username):
    # show the user profile for that user
    return 'Usser %s' % username

#   (r'^(?P<index>\w+)$', 'model'),
#   (r'^(?P<index>\w+)/dimensions$', 'dimensions'),
#   (r'^(?P<index>\w+)/dimensions/(?P<dimension>\w+)$', 'dimension'),
#   (r'^(?P<index>\w+)/dimensions/(?P<dimension>\w+)/query$', 'query'),


@app.route('/api/<index>/')
def model(index):
    model = {
    'id': 'mortality',
    'dimensions': [
            {
                'id': 'gender',
                'label': 'Gender',
                'type': 'bar',
                'width': 3,
                'status': {
                    'weight': 1,
                    'format': '<strong>$s</strong>',
                    'default': 'people',
                },
            },
            {
                'id': 'year',
                'label': 'Year',
                'type': 'bar',
                'width': 3,
                'status': {
                    'weight': 4,
                    'format': 'in <strong>$</strong>',
                    'default': 'between 2002 and 2009',
                },
            },
            {
                'id': 'disease',
                'label': 'Disease',
                'type': 'bubble',
                'width': 6,
                'status': {
                    'weight': 3,
                    'format': 'died from <strong>$</strong>',
                    'default': 'died',
                },
            },
            {
                'id': 'area',
                'label': 'Local Authority District',
                'type': 'geo',
                'width': 3,
                'status': {
                    'weight': 2,
                    'format': 'in <strong>$</strong>',
                    'default': 'in the UK',
                },
            },
        ]
    }
    return Response(simplejson.dumps(model), status=200, mimetype='application/json')

#TODO - proper error reporting when ElasticSearchException
@app.route('/api/<index>/dimensions/')
def dimensions(index):
    """ Return all dimension values for the requested type """

    # Fetch dimension names
    try:
        dimensions = elasticsearch.get_dimensions(index)
    except elasticsearch.ElasticSearchException, e:
        return Response(e, status=500, mimetype='text/plain')

    # Build query to return all values for each dimension
    params = {
        'size': 10000, # Hack: Assume there's less than 10000 values
        'filter': {
            'or': []
        }
    }

    for dimension in dimensions:
        params['filter']['or'].append({
            'type': {
                'value': dimension
            }
        })

    # Request all values for all dimensions
    try:
        response = elasticsearch.request('search', index, None, params)
    except elasticsearch.ElasticSearchException, e:
        return Response(e, status=500, mimetype='text/plain')

    # Build a dict of dimensions where each dimension is a dict
    # of all the dimension's values
    values = {}
    for value in response['hits']['hits']:

        if value['_type'] not in values:
            values[value['_type']] = {}

        values[value['_type']][value['_source']['id']] = value['_source']

    # Render response
    resp = Response(simplejson.dumps(values), status=200, mimetype='application/json')
    return resp





if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
   # app.debug = True
    app.run(host='0.0.0.0', port=port)


