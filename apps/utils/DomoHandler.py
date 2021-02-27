# -*- coding: utf-8 -*-
#########################################################
# SERVICE : DomeHandler.py                              #
#           Handles communication and protocol with     #
#           Domotion                                    #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
import time
#########################################################

####################### GLOBALS #########################
SensorTypes = {
    1: "key",
    2: "voltage",
    3: "percentage",
    4: "current",
    5: "pressure",
    6: "temperature",
    7: "rain",
    8: "wind",
    9: "humidity"
}

ActuatorTypes = {
    1: "light",
    2: "socket",
    3: "blind",
    4: "doorlock",
    5: "amplifier",
    6: "tv",
    7: "voltage",
    8: "percentage"
}

SmartHomeResponses = {
    "key": {"set": ["on"], "get": ["on"]},
    "voltage": {"set": [], "get": []},
    "percentage": {"set": [], "get": []},
    "current": {"set": [], "get": []},
    "pressure": {"set": [], "get": []},
    "temperature": {"set": [], "get": []},
    "rain": {"set": [], "get": []},
    "wind": {"set": [], "get": []},
    "humidity": {"set": [], "get": []},
    "light": {"set": ["on"], "get": ["on"]},
    "socket": {"set": ["on"], "get": ["on"]},
    "blind": {"set": ["openPercent"], "get": ["openPercent"]},
    "doorlock": {"set": ["lock"], "get": ["isLocked","isJammed"]},
    "amplifier": {"set": ["on"], "get": ["on"]},
    "tv": {"set": ["on"], "get": ["on"]}
}

# timer for db reload #time.time()
DB_LIFETIME = 60
#timer for query from db
QUERY_LIFETIME = 3
# check whether types and traits are applicable, otherwise generate error

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : DomoHandler                                   #
#########################################################
class DomoHandler(object):
    def __init__(self, bdaclient):
        self.bdaclient = bdaclient
        self.db = {}
        self.dbvalidtime = 0
        self.queryvalidtime = 0

    def __del__(self):
        pass

    def getDb(self):
        self.db = {}
        info = []
        devices = []
        #sensors
        tag, info, error = self.tda(self.bdaclient.SendInfoRequest(True,"sensors"))
        if not error:
            tag, devices, error = self.tda(self.bdaclient.SendInfoRequest(False, "sensors"))
        if not error:
            try:
                for inf in info[1]:
                    dbitem = {}
                    dbitem['description'] = inf[2]
                    dbitem['type'] = SensorTypes[inf[3]]
                    dbitem['digital'] = True if inf[4] else False
                    dbitem['value'] = devices[str(inf[0])]
                    self.db[inf[1]] = dbitem
            except:
                error = True
        if not error:
            tag, info, error = self.tda(self.bdaclient.SendInfoRequest(True, "actuators"))
        if not error:
            tag, devices, error = self.tda(self.bdaclient.SendInfoRequest(False, "actuators"))
        if not error:
            try:
                for inf in info[1]:
                    dbitem = {}
                    dbitem['description'] = inf[2]
                    dbitem['type'] = ActuatorTypes[inf[3]]
                    dbitem['digital'] = True if inf[4] else False
                    dbitem['value'] = devices[str(inf[0])]
                    self.db[inf[1]] = dbitem
            except:
                pass
        if not error:
            self.dbvalidtime = time.time() + DB_LIFETIME
            self.queryvalidtime = time.time() + QUERY_LIFETIME
        return

    def tda(self, rdata):
        error = False
        tag = ""
        data = {}
        try:
            Error = True if rdata[0] == "ERROR" else False
            tag = rdata[1]
            if rdata[0] == "ALL":
                data = rdata[3]
            else:
                data = rdata[2]
        except:
            error = True
        return tag, data, error

    def checkDbValid(self):
        return time.time() < self.dbvalidtime

    def checkQueryValid(self):
        valid = False
        if time.time() < self.queryvalidtime:
            valid = True
            self.queryvalidtime = time.time() + QUERY_LIFETIME
        return valid

    def checkDbItem(self, tag, type):
        dbItem = {}
        #'BlindsManual': {'Description': 'Blinds Manual', 'Type': 'blind', 'Digital': True, 'value': 0}
        if tag in self.db:
            dbItem = self.db[tag]
            if dbItem["type"] != type:
                dbItem = {}

        return dbItem

    def processParams(self, type, params):
        value = 0
        if type in SmartHomeResponses:
            for response in SmartHomeResponses[type]['set']:
                if response in params:
                    # TBD: more in future
                    if response == "openPercent":
                        if params[response] > 50:
                            value = 0
                        else:
                            value = 1
                    else:
                        value = 1 if params[response] else 0
        return value

    def processValues(self, type, value):
        values = {}
        if type in SmartHomeResponses:
            for response in SmartHomeResponses[type]['get']:
                newvalue = {}
                # TBD: more in future
                if response == "openPercent":
                    if int(value) > 0:
                        newvalue[response] = 0
                    else:
                        newvalue[response] = 100
                elif response == "isJammed":
                    newvalue[response] = False
                else:
                    newvalue[response] = True if int(value) > 0  else False
                values.update(newvalue)
        return values

    def set(self, data):
        rdata = {}
        error = False
        if not self.checkDbValid():
            self.getDb()
        try:
            dbItem = self.checkDbItem(data["tag"], data["type"])
            if dbItem:
                value = self.processParams(data["type"], data["params"])
                tag, value = self.bdaclient.Send(data["tag"], value)
                if not tag:
                    error = True
            else:
                error = True
            if not error:
                rdata["tag"] = data["tag"]
                rdata["type"] = data["type"]
                rdata["values"] = self.processValues(data["type"], value)
        except:
            pass

        return rdata

    def get(self, data):
        rdata = {}
        error = False
        if not self.checkDbValid():
            self.getDb()
        try:
            dbItem = self.checkDbItem(data["tag"], data["type"])
            if dbItem:
                if self.checkQueryValid():
                    value = dbItem["value"]
                    error = False
                else:
                    tag, value = self.bdaclient.Send(data["tag"], None)
                    if not tag:
                        error = True
            else:
                error = True
            if not error:
                rdata["tag"] = data["tag"]
                rdata["type"] = data["type"]
                rdata["values"] = self.processValues(data["type"], value)
        except:
            pass

        return rdata


######################### MAIN ##########################
if __name__ == "__main__":
    pass
