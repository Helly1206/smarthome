# -*- coding: utf-8 -*-
#########################################################
# SERVICE : common.py                                   #
#           Python common functions for web app         #
#           I. Helwegen 2019                            #
#                                                       #
#########################################################

####################### IMPORTS #########################
from hashlib import sha256
from base64 import b64encode
from re import match
import uuid
import time

#########################################################

####################### GLOBALS #########################
SESSION_TIMEOUT = 3600
AUTH_CODE_TIMEOUT = 600
#########################################################

###################### FUNCTIONS ########################

#########################################################

class password(object):
    secret_key = "@%^&123_assistanthook_$%#!@"

    # Password
    def GetKey(self):
        return self.secret_key

    def HashPass(self, password):
        salted_password = (password + self.secret_key).encode("utf-8")
        return sha256(salted_password).hexdigest()

    def IsPassword(self, password):
        result = None
        if (len(password)==64):
            try: result = match(r"([a-fA-F\d]{64})", password).group(0)
            except: pass
        return result is not None

#########################################################
# Class : common                                        #
#########################################################
class common(object):
    def __init__(self, settings):
        self.settings = settings
        self.cookies = {}
        self.userdata = {}
        self.authcodes = {}
        self.users = {
            '1234': {
                'uid': '1234',
                'name': self.settings.getSetting('username'),
                'password': self.settings.getSetting('password'),
                'tokens': ['ZsokmCwKjdhk7qHLeYd2'],
            }
        } # TBD: Possibility for multiple users later
        self.clients = {
            self.settings.getSetting('googleclientid'): {
                'clientId':       self.settings.getSetting('googleclientid'),
                'clientSecret':   self.settings.getSetting('googleclientsecret'),
            }
        } # TBD: Possibility for multiple clients later
        self.tokens = {
            'ZsokmCwKjdhk7qHLeYd2': {
                'uid': '1234',
                'accessToken': 'ZsokmCwKjdhk7qHLeYd2',
                'refreshToken': 'ZsokmCwKjdhk7qHLeYd2',
                'userAgentId': '1234',
            }
        } # TBD: Possibility for multiple tokens later

    def __del__(self):
        pass

    def generateCookie(self):
        c = {}
        c[uuid.uuid4().hex] = time.time()
        return c

    def sessionData(self, sessionId = ""):
        #check if new cookie is required
        if not sessionId or not sessionId in self.cookies or time.time() - self.cookies[sessionId] > SESSION_TIMEOUT:
            c = self.generateCookie()
            sessionId = list(c.keys())[0]
            self.cookies.update(c)
            self.userdata[sessionId]={}

        #update cookies and userdata
        self.cookies = {k: v for k, v in self.cookies.items() if time.time()-v < SESSION_TIMEOUT}
        common = self.cookies.keys() & self.userdata.keys()
        self.userdata = {k: v for k, v in self.userdata.items() if k in common}

        return sessionId

    def getSessionUser(self, sessionId):
        return self.userdata.get(sessionId, None)

    def setSessionUser(self, sessionId, user):
        self.userdata[sessionId] = user

    def generateAuthCode(self, uid, client_id):
        authCode = uuid.uuid4().hex
        c = { 'type': 'AUTH_CODE', 'uid': uid, 'clientId': client_id,
              'expiresAt': time.time() + AUTH_CODE_TIMEOUT}
        self.authcodes[authCode] = c
        return authCode

    def authCode(self, code):
        self.authcodes = {k: v for k, v in self.authcodes.items() if v['expiresAt'] > time.time()}

        ac = self.authcodes.get(code, "")
        if ac != "":
            if ac['expiresAt'] > time.time():
                return ac
        return None

    def getUser(self, username, passwd):
        userId = None
        for key, value in self.users.items():
            if value['name'] == username:
                userId = value['uid']
                break
        if userId != None:
            user = self.getUserById(userId)
            if user != None:
                if user['password'] == password().HashPass(passwd):
                    return user
        return None

    def getUserById(self, userId):
        if userId != None:
            user = self.users.get(userId, None)
            if user != None:
                return user
        return None

    def getTokens(self, tokenId):
        if tokenId != None:
            tokens = self.tokens.get(tokenId, None)
            if tokens != None:
                return tokens
        return None

    def getClient(self, clientId, clientSecret):
        client = self.clients.get(clientId, None)
        if client == None or client['clientSecret'] != clientSecret:
            return None
        return client

    def getClientId(self, clientId):
        client = self.clients.get(clientId, None)
        return client != None

    def getUserAgent(self, sessionId):
        user = self.getSessionUser(sessionId)
        if user == None or user.get('uid', '') == '':
            return None
        accessToken = self.tokens.get(user['tokens'][0], None)
        if accessToken == None:
            return None

        return accessToken['userAgentId']

######################### MAIN ##########################
if __name__ == "__main__":
    pass
