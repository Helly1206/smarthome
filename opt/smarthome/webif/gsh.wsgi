#!/usr/bin/python3
from sys import path
from os import environ

path.insert(0,"/var/www/smarthome")

def application(req_environ, start_response):
    try:
        environ['LC_TIME'] = req_environ['LC_TIME']
    except:
        environ['LC_TIME'] = ''

    from gsh import app as _application
    return _application(req_environ, start_response)
