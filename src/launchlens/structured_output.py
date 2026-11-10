"""Nebius schema dialect; backend remains authoritative for every constraint."""
from copy import deepcopy

def response_format(schema):
    def project(value):
        if type(value) is dict:return {k:project(v) for k,v in value.items() if k != 'uniqueItems'}
        if type(value) is list:return [project(v) for v in value]
        return value
    return {'type':'json_schema','json_schema':{'name':'launchlens_gtm','strict':True,'schema':project(deepcopy(schema))}}
