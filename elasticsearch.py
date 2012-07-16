import httplib
import hashlib
import simplejson
#from django.core.cache import cache

caching = False
es_host = 'localhost:9200'

def get_dimensions(index):
    """ Get all dimensions """

    # Build query for all types in index
    params = {
        'size': 0,
        'facets': {
            'types': {
                'terms': {
                    'field': '_type'
                }
            }
        }
    }

    # Make request
    response = request('search', index, None, params)

    # Map dimensions to list
    dimensions = map(lambda x: x['term'], response['facets']['types']['terms'])

    # Remove "observation" as this is the data itself (not a dimension)
    dimensions = filter(lambda x: x != 'observation', dimensions)

    return dimensions

def request(action, index, type, params):
    """ Make request to elastic search REST API"""

    # Build path for REST API
    path = '/' + index + '/'
    if type is not None:
        path += type + '/'
    path += '_' + action

    # Generate JSON representation of params
    params = simplejson.dumps(params)

    # Generate caching key by hashing the request's path and parameters
    # TODO: Find a better way to do this
    cache_key = hashlib.md5(path + ':' + params).hexdigest()

    # Attempt to get response from cache
    if caching:
        obj = cache.get(cache_key)
        if obj is not None:
            return obj

    try:
        # Connect to API
        conn = httplib.HTTPConnection(es_host)
        conn.set_debuglevel(100)

        # Make the request:
        # Note that according to the elastic search specs this should be a GET request
        # but HTTPConnection doesn't seem to support GET requests that have request bodies
        conn.request('POST', path, params)

        # Read response
        response = conn.getresponse()

    except httplib.HTTPException:
        raise ElasticSearchException('Unable to contact elastic search API')

    # Load in reponse JSON
    try:
        obj = simplejson.loads(response.read())
    except simplejson.JSONDecodeError:
        raise ElasticSearchException('Unable to parse response as JSON')

    # Cache response
    if caching:
        cache.add(cache_key, obj)

    return obj

class ElasticSearchException(Exception):
    pass
