#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : shDomotion.py                                #
#          Domotion app for smarthome                   #
#          I. Helwegen 2021                             #
#########################################################

####################### IMPORTS #########################
import signal
import logging
import logging.handlers
import locale
from .utils.bdaclient import bdaclient
from .utils.DomoHandler import DomoHandler
from .utils.xmlsettings import xmlsettings
#########################################################

####################### GLOBALS #########################
appName  = "Domotion"
XML_NAME = "smarthomeDomotion.xml"
#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : Domotion                                      #
#########################################################
class Domotion(object):
    def __init__(self, file = "", name = ""):
        self.bdaclient = None
        self.DomoHandler = None
        self.file = file
        self.name = name
        self.logger = logging.getLogger("{}.{}".format(self.name, appName))
        if xmlsettings(XML_NAME, self.file, self.name).get("debuglog"):
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.logger.info("Loaded app {}".format(appName))

    def __del__(self):
        pass

    def run(self):
        self.startBdaClient()

        self.DomoHandler = DomoHandler(self.bdaclient)

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

    def handle(self, data):
        rdata = {}
        self.logger.debug("<: {}".format(str(data)))
        for tag, datum in data.items():
            if tag != "device":
                rdatum = {}
                if "param" in datum: # execute
                    if not "state" in datum:
                        datum["state"] = datum["param"]
                    rdatum = self.DomoHandler.set(tag, datum)
                else:
                    rdatum = self.DomoHandler.get(tag, datum)
                rdata[tag] = rdatum.copy()
        self.logger.debug(">: {}".format(str(rdata)))
        return rdata

    def callback(self, data):
        #not implemented
        return None, None

    def terminate(self):
        if (self.bdaclient != None):
            self.bdaclient.terminate()
            self.bdaclient.join(5)

#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    Domotion().run()
