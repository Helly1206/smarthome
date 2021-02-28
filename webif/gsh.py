# -*- coding: utf-8 -*-
#########################################################
# SERVICE : gsh.py (Google Smart Home)                  #
#           Containing the web application for          #
#           smarthome                                   #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
from os import path, urandom, kill, getpid
from flask import Flask, request, redirect, render_template, make_response, jsonify, abort, session
from websettings import websettings as settings
from smarthome import smarthome
from common import common
import ssl
from urllib.parse import quote, unquote
from sys import argv, exit, stdout
from getopt import getopt, GetoptError
import requests
import logging
import logging.handlers
import locale
import atexit

#########################################################

####################### GLOBALS #########################
context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
VERSION = "0.81"
HOMEGRAPH_URL = 'https://homegraph.googleapis.com/'
REQUEST_SYNC_BASE_URL = HOMEGRAPH_URL + 'v1/devices:requestSync'
APP_NAME = "smarthome"

#########################################################
# Class : FalskApp                                      #
#########################################################
class FlaskApp(Flask):

    def __init__(self, *args, **kwargs):
        super(FlaskApp, self).__init__(*args, **kwargs)
        self.secret_key = urandom(24)
        self.settings = settings(__file__, APP_NAME)
        self.common = common(self.settings)
        self.logger = logging.getLogger("SmartHome")
        if self.settings.getSetting('debuglog'):
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        ch = logging.StreamHandler(stdout)
        self.logger.addHandler(ch)
        locale.setlocale(locale.LC_TIME,'')
        strformat=("{} {}".format(locale.nl_langinfo(locale.D_FMT),locale.nl_langinfo(locale.T_FMT)))
        strformat=strformat.replace("%y", "%Y")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', strformat)
        ch.setFormatter(formatter)
        self.smarthome = smarthome(__file__, APP_NAME)
        prefix = self.settings.getSetting('webprefix')
        if prefix == None:
            prefix = "/"
        direct = self.settings.getSetting('webhookdirect')

        self.prefix="/"
        if prefix[:1] != "/":
            prefix = "/" + prefix
        if (len(prefix)>1):
            if (prefix[-1:] == "/"):
                prefix = prefix[:-1]
            self.prefix = prefix + direct
        else:
            self.prefix = direct

    def p(self, route):
        return "%s%s"%(self.prefix,route)

    def pr(self, route):
        if __name__ == "__main__":
            return "%s%s"%(self.prefix,route)
        else:
            return route

    def c(self, route):
        if (len(route) > 1) and (route[-1:] == "/"):
            return route[:-1]
        else:
            return route

    def getp(self):
        return self.prefix

app = FlaskApp(__name__)

#########################################################
# app functions                                         #
#########################################################

@app.errorhandler(400)
def page_not_found(e):
    return "400-Bad Request", 400

@app.errorhandler(401)
def page_not_found(e):
    return "401-Unauthorized", 401

@app.errorhandler(404)
def page_not_found(e):
    return "404-Not found", 404

@app.errorhandler(500)
def page_not_found(e):
    return "500-Internal Server Error", 500

@app.errorhandler(503)
def page_not_found(e):
    return "503-Service Unavailable", 503

@app.errorhandler(504)
def page_not_found(e):
    return "504-Gateway timeout", 504

@app.before_request
def before_request_func():
    session["SessionId"] = app.common.sessionData(session.get("SessionId", ""))

@app.route(app.pr('/login'), methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        return render_template("login.html", prefix=app.getp())
    if request.method == "POST":
        user = app.common.getUser(request.form.get("username", None), request.form.get("password", None))
        if user == None:
            return redirect('%s?client_id=%s&redirect_uri=%s&redirect=%s&state=%s' %
                (app.p('/login'), request.form.get("client_id", None), request.form.get("redirect_uri", None),
                request.form.get("redirect", None), request.form.get("state", None)), 301)

        app.common.setSessionUser(session['SessionId'], user)
        authCode = app.common.generateAuthCode(user['uid'], request.form.get("client_id", None));

        if authCode != None:
            return redirect('%s?code=%s&state=%s' %
                (unquote(request.form.get("redirect_uri", None)), authCode, request.form.get("state", None)), 301)

    return abort(500)

@app.route(app.pr('/oauth'), methods=['GET', 'POST'])
def oauth():
    client_id = request.args.get("client_id", "")
    redirect_uri = request.args.get("redirect_uri", "")
    state = request.args.get("state", "")
    response_type = request.args.get("response_type", "")
    authCode = request.args.get("code", "")

    if 'code' != response_type:
        s = 'response_type %s must equal "code"' % response_type
        return s, 500

    if not app.common.getClientId(client_id):
        s = 'client_id %s invalid' % client_id
        return s, 500

    #if there is an authcode use it
    if authCode != "":
        return redirect('%s?code=%s&state=%s' % (redirect_uri, authCode, state))

    user = app.common.getSessionUser(session['SessionId'])
    if user == None or user.get('uid', '') == '':
        app.logger.info('No user data')
        return redirect('%s?client_id=%s&redirect_uri=%s&redirect=%s&state=%s' %
            (app.p('/login'), client_id, quote(redirect_uri, safe=''),
            request.path, state), 301) # is request.path correct?

    authCode = app.common.generateAuthCode(user['uid'], client_id);

    if authCode != None:
        return redirect('%s?code=%s&state=%s' % (redirect_uri, authCode, state))

    return abort(400)

# /**
# * client_id=GOOGLE_CLIENT_ID
# * &client_secret=GOOGLE_CLIENT_SECRET
# * &response_type=token
# * &grant_type=authorization_code
# * &code=AUTHORIZATION_CODE
# *
# * OR
# *
# *
# * client_id=GOOGLE_CLIENT_ID
# * &client_secret=GOOGLE_CLIENT_SECRET
# * &response_type=token
# * &grant_type=refresh_token
# * &refresh_token=REFRESH_TOKEN
# */
@app.route(app.pr('/token'), methods=['GET', 'POST'])
def token():
    client_id = request.args.get("client_id", request.form.get("client_id", None))
    client_secret = request.args.get("client_secret", request.form.get("client_secret", None))
    grant_type = request.args.get("grant_type", request.form.get("grant_type", None))

    if client_id == None or client_secret == None:
        s = "missing required parameter"
        return s, 400

    client = app.common.getClient(client_id, client_secret)
    if client == None:
        s = "incorrect client data"
        return s, 400

    if 'authorization_code' == grant_type:
        return handleAuthCode()
    elif 'refresh_token' == grant_type:
        return handleRefreshToken()
    else:
        s = 'grant_type ' + grant_type + ' is not supported'
        return s, 400

# /**
# * @return {{}}
# * {
# *   token_type: "bearer",
# *   access_token: "ACCESS_TOKEN",
# *   refresh_token: "REFRESH_TOKEN"
# * }
# */
def handleAuthCode():
    client_id = request.args.get("client_id", request.form.get("client_id", None))
    client_secret = request.args.get("client_secret", request.form.get("client_secret", None))
    code = request.args.get("code", request.form.get("code", None))

    if code == None:
        s = "missing required parameter"
        return s, 400

    client = app.common.getClient(client_id, client_secret)
    if client == None:
        s = "incorrect client data"
        return s, 400

    authCode = app.common.authCode(code)
    if authCode == None:
        s = "invalid or expired code"
        return s, 400

    if authCode['clientId'] != client_id:
        s = "invalid code - wrong client"
        return s, 400

    token = getAccessToken(code)
    if token == None:
        s = "unable to generate a token"
        return s, 400

    return make_response(token, 200)

# /**
# * @return {{}}
# * {
# *   token_type: "bearer",
# *   access_token: "ACCESS_TOKEN",
# * }
# */
def handleRefreshToken():
    client_id = request.args.get("client_id", request.form.get("client_id", None))
    client_secret = request.args.get("client_secret", request.form.get("client_secret", None))
    refresh_token = request.args.get("refresh_token", request.form.get("refresh_token", None))

    client = app.common.getClient(client_id, client_secret)
    if client == None:
        s = "incorrect client data"
        return s, 500

    if refresh_token == None:
        s = "missing required parameter"
        return s, 500

    returnToken = {'token_type': 'bearer', 'access_token': refresh_token}
    return make_response(jsonify(returnToken), 200)


# Helper function
def getAccessToken(code):
    authCode = app.common.authCode(code)
    if authCode == None:
        return None

    user = app.common.getUserById(authCode['uid'])
    if user == None:
        return None

    accessToken = app.common.getTokens(user['tokens'][0])
    if accessToken == None:
        return None

    returnToken = {'token_type': 'bearer'}
    returnToken['access_token'] = accessToken['accessToken']
    returnToken['refresh_token'] = accessToken['refreshToken']
    return jsonify(returnToken)

@app.route(app.pr('/sync'), methods=['GET'])
def syncDevices():
    user = app.common.getSessionUser(session['SessionId'])
    if user == None or user.get('uid', '') == '':
        return redirect('{}?redirect_uri={}'.format(app.p('/login'),app.p('/sync')))

    userAgent = app.common.getUserAgent(session['SessionId'])

    if userAgent == None:
        return abort(500) #internal error

    url = REQUEST_SYNC_BASE_URL + '?key=' + app.settings.getSetting('googleapikey')
    j = {"agentUserId": userAgent}

    r = requests.post(url, json=j)

    s = 'Synchronization request sent, status_code: ' + str(r.status_code)
    return s, 200

@app.route(app.pr('/'), methods=['GET', 'POST'])
def webhook():
    if request.method == "GET":
        s = "not supported"
        return s, 500
    if request.method == "POST":
        a = request.headers.get('Authorization', None)
        token = None
        if a != None:
            type, tokenH = a.split()
            if type.lower() == 'bearer':
                token = app.common.getTokens(tokenH)
        if token == None:
            return abort(401) # raise error? 'not authorized access!!'
        # return response
        json = request.get_json(force=True)
        app.logger.debug("Request: {}".format(json))
        response = app.smarthome.process(json, token)
        app.logger.debug("Response: {}".format(response))
        try:
            if 'errorCode' in response['payload']:
                app.logger.error('Error handling message %s: %s' % (message, response['payload']))
        except:
            pass

        return jsonify(response), 200

def terminate():
    app.smarthome.terminate()

atexit.register(terminate)

#########################################################
# main                                                  #
#########################################################
def main(argv):
    ssl = False
    port = 5000
    crt = ""
    key = ""
    try:
        opts, args = getopt(argv,"hsp:c:k:",["help","ssl","port=","crt=","key="])
    except GetoptError:
        print("Google smarthome webhook server for google smarthome access")
        print("Version: " + VERSION)
        print(" ")
        print("Enter 'gsh.py -h' for help")
        exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print("smarthome web interface")
            print("Version: " + VERSION)
            print(" ")
            print("Usage:")
            print("         gsh.py -s -p <portnumber> -c <certificate file> -k <key file>")
            print("         -h, --help: Print this help file")
            print("         -s, --ssl: Start server in ssl mode")
            print("         -p, --port: Enter port number for server")
            print("         -c, --crt: Location of the certificate file (required for ssl)")
            print("         -k, --key: Location of the key file (required for ssl)")
            print(" ")
            print("For production, don't run this service as standalone, but configure Apache2")
            exit()
        elif opt in ("-s", "--ssl"):
            ssl = True
        elif opt in ("-p", "--port"):
            port = arg.strip()
        elif opt in ("-c", "--crt"):
            crt = arg.strip()
        elif opt in ("-k", "--key"):
            key = arg.strip()

    if (ssl):
        if (crt == ""):
            ssl = False
            print ("No certificate file entered, ssl disabled")
        elif (key == ""):
            ssl = False
            print ("No key file entered, ssl disabled")
        elif (not path.isfile(crt)):
            ssl = False
            print ("Invalid or non existing certificate file, ssl disabled")
        elif (not path.isfile(key)):
            ssl = False
            print ("Invalid or non existing key file, ssl disabled")
        else:
            context.load_cert_chain(crt, key)

    try:
        if (ssl):
            app.run(host="0.0.0.0", debug=False, use_reloader=False, port=port, ssl_context=context)
        else:
            app.run(host="0.0.0.0", debug=False, use_reloader=False, port=port)
        #app.smarthome.terminate()
    except Exception as e:
        print(e)

#########################################################
if __name__ == "__main__":
    main(argv[1:])
