# Gandi-specific API Functions
import json
import os
import sys
import urllib2
from webob import Request

SUGGEST_URL = 'https://suggest.api.gandi.net/v1'

def suggest(query_string, client_ip):

    url = SUGGEST_URL + '?' + query_string + '&country=' + client_ip
    #headers = {SPECIAL_HEADER_TYPE:SPECIAL_HEADER_TEXT}

    #dbg = urllib2.urlopen(url).info().getheader('Content-Type')
    #print >>   environ['wsgi.errors'], dbg
    remote_req = urllib2.Request(url)
    try:
        response = urllib2.urlopen(remote_req, timeout=10)
    except Exception,   e:  
        #emsg   =   {"succeeded":   false, "errors": {"HTTPError": str(e.reason)}}
        #print   >> environ['wsgi.errors'], e
        emsg = {"succeeded": False, "errors": {"Network Error": "Backend timed out."}}
        return json.dumps(emsg)
        
    ctype = response.info().getheader('Content-Type')
    if ctype.partition(';')[0] == 'application/json':
        sdata = response.read()
        sdata = json.loads(sdata)
            
        if "offer" in sdata:
            sdata["quote"] = sdata["offer"]
            del(sdata["offer"])
        if "price" in sdata:
            sdata["price"] = "" + sdata["price"]
            
        return json.dumps(sdata)

    emsg = {"succeeded": False, "errors":   {"HTTPError": "Backend returned invalid content type."}}
    #return json.dumps(emsg)
