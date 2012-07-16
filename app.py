import os
import simplejson
from flask import Flask
from flask import Response
from flask import request
import elasticsearch

app = Flask(__name__)

#TODO   - proper error reporting when ElasticSearchException
#       - caching, we're hitting ES every request atm

@app.route('/')
def hello():
    return 'All valid paths begin with "/api/"'

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
    return Response(simplejson.dumps(values), status=200, mimetype='application/json')

@app.route('/api/<index>/dimensions/<dimension>/')
def dimension(index, dimension):
    """ Return values for the requested dimension """

    # Build query to return values for dimension
    params = {
        'size': 10000, # Hack: Assume there's less than 10000 values
        'filter': {
            'or': [{
                'type': {
                    'value': dimension
                }
             }]
        }
    }

    # Request values for dimension
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
    return Response(simplejson.dumps(values), status=200, mimetype='application/json')

@app.route('/test/')
def test():
    print 'test'
    print request.args
    print 'nothing'

    return request.args

@app.route('/api/<index>/dimensions/<dimension>/query/')
def query(index, dimension):
    """ Return aggregates of measures the requested dimension """
    print request.args

    # Build query to return stats for the dimension
    params = {
        'size': 0,
        'query': {
            'match_all': {}
        },
        'facets': {}
    }

    # Build filters from requested cut
    filters = []
    for key in request.args.keys():
        print 'inley'
        print key
        if key != dimension:
            filters.append({
                'term': {
                    key: request.args.get(key, '')
                }
            })

    params['facets'][dimension] = {
        'terms_stats': {
            'key_field': dimension,
            'value_field': 'value',
            'all_terms': True
        },
    }

    # Filter dimension by requested cut
    if len(filters) > 0:
        params['facets'][dimension]['facet_filter'] = {
            'and': filters
        }

    # Make request
    try:
        response = elasticsearch.request('search', index, 'observation', params)
    except elasticsearch.ElasticSearchException, e:
     return Response(e, status=500, mimetype='text/plain')

    # Build a dict of dimensions where each dimension is a list
    # of all the dimension's values' IDs and stats
    aggregates = {}
    for facet in response['facets']:
        aggregates[facet] = []

        for value in response['facets'][facet]['terms']:
            aggregates[facet].append({
                'id': value['term'],
                'min': value['min'],
                'max': value['max'],
                'total': value['total'],
                'mean': value['mean']
            })

    # Render response
    return Response(simplejson.dumps(aggregates), status=200, mimetype='application/json')

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
   # app.debug = True
    app.run(host='0.0.0.0', port=port)


