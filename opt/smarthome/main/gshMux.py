#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SERVICE : gshMux.py                                   #
#           Python gsh mux                              #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
import signal
import logging
import logging.handlers
import locale
import sys
from apps.Domotion import Domotion
from apps.Mqtt import Mqtt
from webif.devices import devices
from apps.utils.webserveraccess import webserveraccess
#########################################################

####################### GLOBALS #########################
VERSION = "1.00"
APP_NAME = "smarthome"

#########################################################
# Class : gshMux                                        #
#########################################################
class gshMux(object):
    def __init__(self, file):
        self.file = file
        self.apps = {}
        self.server = None
        self.logger = logging.getLogger(APP_NAME)
        self.logger.setLevel(logging.INFO)
        ch = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(ch)
        locale.setlocale(locale.LC_TIME,'')
        strformat=("{} {}".format(locale.nl_langinfo(locale.D_FMT),locale.nl_langinfo(locale.T_FMT)))
        strformat=strformat.replace("%y", "%Y")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', strformat)
        ch.setFormatter(formatter)
        self.logger.info("{} app, version {}".format(APP_NAME, VERSION))

    def __del__(self):
        pass

    def run(self):
        self.server=webserveraccess(APP_NAME, callback = self.update)
        self.server.start()

        signal.signal(signal.SIGINT, self.exit_app)
        signal.signal(signal.SIGTERM, self.exit_app)

        devlist = self.getDevices()
        for dev in devlist:
            try:
                app = globals()[dev](self.file, APP_NAME)
                app.run()
                self.apps[dev] = app
            except:
                self.logger.error("App not available: {}".format(dev))

        signal.pause()

    def getDevices(self):
        devlist = []
        Devices = devices(__file__, APP_NAME).getAll()
        for key, value in Devices.items():
            if "backEnd" in value:
                if "device" in value["backEnd"]:
                    if value["backEnd"]["device"] not in devlist:
                        devlist.append(value["backEnd"]["device"].title())
        return devlist

    def update(self, data): # Callback function
        rdata = {}
        if "device" in data:
            device = data["device"].title()
            if device in self.apps.keys():
                rdata = self.apps[device].handle(data)
        rdata["device"] = device
        return rdata

    def exit_app(self, signum, frame):
        for key, app in self.apps.items():
            if (app != None):
                app.terminate()
        self.apps = {}
        if (self.server != None):
            self.server.terminate()
            self.server.join(5)

#########################################################
if __name__ == "__main__":
    gshMux().run()
