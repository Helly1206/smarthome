#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : shDomotion.py                                #
#          Domotion app for smarthome                   #
#          I. Helwegen 2021                             #
#########################################################

####################### IMPORTS #########################
import signal
import sys
import logging
import logging.handlers
import locale
from .utils.shdaclient import shdaclient
from .utils.bdaclient import bdaclient
from .utils.DomoHandler import DomoHandler
from .utils.xmlsettings import xmlsettings
#########################################################

####################### GLOBALS #########################
appName  = "Domotion"
version  = "0.81"
XML_NAME = "smarthomeDomotion.xml"
#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : Domotion                                      #
#########################################################
class Domotion(object):
    def __init__(self, file = "", name = ""):
        self.client = None
        self.bdaclient = None
        self.DomoHandler = None
        self.file = file
        self.name = name
        self.logger = logging.getLogger("DomotionSmartHome")
        if xmlsettings(XML_NAME, self.file, self.name).get("debuglog"):
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        ch = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(ch)
        locale.setlocale(locale.LC_TIME,'')
        strformat=("{} {}".format(locale.nl_langinfo(locale.D_FMT),locale.nl_langinfo(locale.T_FMT)))
        strformat=strformat.replace("%y", "%Y")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', strformat)
        ch.setFormatter(formatter)
        self.logger.info("SmartHome app {}, version {}".format(appName, version))

    def __del__(self):
        pass

    def run(self, argv):
        self.startBdaClient()

        self.DomoHandler = DomoHandler(self.bdaclient)
        self.client=shdaclient("DomotionSmartHome", appName, callback = self.update)
        self.client.start()

        signal.pause()

    def startBdaClient(self):
        server = ""
        port = 60004
        username = ""
        password = ""
        settings = xmlsettings(XML_NAME, self.file, self.name).getAll()

        try:
            if settings["server"]:
                server = settings["server"]
            if settings["port"]:
                port = int(settings["port"])
            if settings["username"]:
                username = int(settings["username"])
            if settings["password"]:
                password = int(settings["password"])
        except:
            pass
        self.bdaclient = bdaclient("DomotionSmartHome", self.callback, url="/smarthome", port=port, server=server, username=username, password=password)
        self.bdaclient.start()

    def terminate(self):
        if (self.bdaclient != None):
            self.bdaclient.terminate()
            self.bdaclient.join(5)
        if (self.client != None):
            self.client.terminate()
            self.client.join(5)

    def callback(self, data):
        #not implemented
        return None, None

    def update(self, data): # Callback function
        self.logger.debug("<: {}".format(str(data)))
        rdata = {}
        if "params" in data: # execute
            rdata = self.DomoHandler.set(data)
        else:
            rdata = self.DomoHandler.get(data)
        rdata["device"] = appName
        self.logger.debug(">: {}".format(str(rdata)))
        return rdata
#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    Domotion().run(sys.argv[1:])
