import glob
import json
import os
import sys
import multiprocessing
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__))+'/lib/pygeoip')
import settings
import pygeoip
from webob import Request
from cgi import parse_qs

def application(environ, start_response):
    if "Firefox" in environ["HTTP_USER_AGENT"]:
        content = 'text/plain'
    else:
        content = 'application/json'
    
    start_response('200 OK',
    [('Content-type', content ), 
    ('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'),
    ('Pragma', 'no-cache'),
    ('Expires', '02 Jan 2010 00:00:00 GMT' )])
    
    try:
        client_ip = environ['HTTP_X_CLUSTER_CLIENT_IP']
    except KeyError:
        client_ip = environ['REMOTE_ADDR']

    if Request(environ).path_info_peek() == 'suggest':
        yield suggestFromName(environ, Request(environ).query_string, client_ip)
        return
    
    if Request(environ).path_info_peek() == 'list':
        for out in listProviders(environ, environ['HTTP_ACCEPT_LANGUAGE'].split(',')[0].lower()):
            yield out
        return
        
    yield '{"error": "Function not supported."}'


def langstr(locale):
    return '  "languages" : %s,\n' % locale


def listProviders(environ, locale):

    gandi_lang = langstr('["en", "*"]')

    path = os.path.dirname(os.path.abspath(__file__)) + '/json'
    n = 0
    nfiles = len(os.walk(path).next()[2])
    yield '['
    for infile in sorted(glob.glob(os.path.join(path,'*.json'))):
        f = open(infile)

        for line in f:
            if line.strip() == '"languages" : ["en-GB", "fr", "es-ES"],':
                yield gandi_lang
            else:
                yield line
        
        if n < nfiles-1:
            yield ','
            n += 1
        f.close() 
    yield ']'

    
def suggestFromName(environ, query_string, client_ip):
    form = parse_qs(query_string, keep_blank_values=True)
    
    if not ("first_name" in form and "last_name" in form and "providers" in form):
        return json.dumps({"error": "Missing first name, last name, or providers."})

    firstname = form["first_name"][0].lower().replace(" ","")
    lastname = form["last_name"][0].lower().replace(" ","")
    providers = form["providers"][0].lower().split(",")

    gi = pygeoip.GeoIP(os.path.dirname(os.path.abspath(__file__))+'/GeoIP.dat', pygeoip.MEMORY_CACHE)
    client_ip = gi.country_code_by_addr(client_ip)
    
    valid_providers = []
    raw_provider_data = {}
    for value in settings.PROVIDERS.keys():
        raw_provider_data[value] = "{}"
    results = {}

    #verify that client-requested providers are allowed and exist
    for value in providers:
        if value in settings.PROVIDERS.keys():
            valid_providers.append(value)
            
    # create one process per provider to speed up the blocking IO
    pool = multiprocessing.Pool(2)
    for value in valid_providers:
        results[value] = pool.apply_async(settings.PROVIDERS[value].suggest, (Request(environ).query_string, client_ip))
    
    for value in valid_providers:
        raw_provider_data[value] = results[value].get()

    pool.close()
    pool.join()

    #load JSON data from provider
    providerData = {
        "gandi":json.loads(raw_provider_data["gandi"]),
    }
    
    out = []
    for provider in valid_providers:
            rv = {"provider":provider}
            if firstname in ("test", "error"):
                rv["succeeded"] = False
                rv["errors"] = {"first_name": "Invalid first name."}
            else:
                for key,value in providerData[provider].items():
                    rv[key] = value
            out.append(rv)
    
    return json.dumps(out)
    
    
if __name__ == '__main__':
    #this runs when script is started directly from commandline
    try:
        #   create a simple WSGI server and run the application
        from wsgiref import simple_server
        print   "Running test   application -   point   your browser at http://localhost:8000/ ..."
        httpd   =   simple_server.WSGIServer(('',   8000), simple_server.WSGIRequestHandler)
        httpd.set_app(application)
        httpd.serve_forever()
    except ImportError:
        #wsgiref not installed, just output html to stdout
        for content in application({}, lambda status, headers: None):
            print content
