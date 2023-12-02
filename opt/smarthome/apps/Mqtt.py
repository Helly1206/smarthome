#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SCRIPT : Mqtt.py                                      #
#          MQTT app for smarthome                       #
#          I. Helwegen 2023                             #
#########################################################

####################### IMPORTS #########################
import signal
import logging
import logging.handlers
import locale
from .utils.MqttHandler import MqttHandler
from .utils.xmlsettings import xmlsettings
#########################################################

####################### GLOBALS #########################
appName  = "Mqtt"
XML_NAME = "smarthomeMqtt.xml"
#########################################################

###################### FUNCTIONS ########################

#########################################################
# Class : Mqtt                                          #
#########################################################
class Mqtt(object):
    def __init__(self, file = "", name = ""):
        self.MqttHandler = None
        self.file = file
        self.name = name
        self.logger = logging.getLogger("{}.{}".format(self.name, appName))
        self.settings = {}
        if xmlsettings(XML_NAME, self.file, self.name).get("debuglog"):
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.logger.info("Loaded app {}".format(appName))

    def __del__(self):
        pass

    def run(self):
        self.settings = xmlsettings(XML_NAME, self.file, self.name).getAll()
        self.MqttHandler = MqttHandler(self.logger, self.settings, self.file, self.name)
        self.MqttHandler.connect()

    def handle(self, data):
        rdata = {}
        self.logger.debug("<: {}".format(str(data)))
        for tag, datum in data.items():
            if tag != "device":
                rdatum = {}
                if "param" in datum: # execute
                    if not "state" in datum:
                        datum["state"] = datum["param"]
                    rdatum = self.MqttHandler.set(tag, datum)
                else:
                    rdatum = self.MqttHandler.get(tag, datum)
                rdata[tag] = rdatum.copy()
        self.logger.debug(">: {}".format(str(rdata)))
        return rdata

    def callback(self, data):
        #not implemented
        return None, None

    def terminate(self):
        self.MqttHandler.terminate()

#########################################################

######################### MAIN ##########################
if __name__ == "__main__":
    Mqtt().run()
