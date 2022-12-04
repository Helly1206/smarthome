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

# Not all analog values are relevant for domotion control
SmartHomeAnalog = ["brightness", "brightnessRelativePercent", "brightnessRelativeWeight", "temperatureK",
                   "spectrumRgb", "temperature", "spectrumRGB", "amount", "rawValue", "currentFanSpeedPercent",
                   "fanSpeedPercent", "fanSpeedRelativeWeight", "fanSpeedRelativePercent", "duration",
                   "humiditySetpointPercent", "humidityAmbientPercent", "humidity", "openPercent",
                   "rotationDegrees", "rotationPercent", "temperatureSetpointCelsius",
                   "temperatureAmbientCelsius", "thermostatTemperatureSetpoint", "currentVolume",
                   "volumeLevel", "relativeSteps"]

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
        if tag in self.db:
            dbItem = self.db[tag]
            if dbItem["type"] != type:
                dbItem = {}

        return dbItem

    def processParam(self, dbItem, data):
        value = 0
        digital = True
        if "param" in data:
            if data["param"] in SmartHomeAnalog:
                digital = False
        if digital:
            if dbItem['digital']:
                value = 1 if self.digital2Digital(data, data["value"]) else 0
            else:
                value = self.digital2Analog(data, data["value"])
        else:
            if dbItem['digital']:
                value = 1 if self.analog2Digital(data, data["value"]) else 0
            else:
                value = self.analog2Analog(data, data["value"])
        return value

    def processValue(self, dbItem, data, value):
        newvalue = {}
        digital = True
        if "state" in data:
            if data["state"] in SmartHomeAnalog:
                digital = False
        if "const" in data:
            value = data["const"]
        else:
            if digital:
                if dbItem['digital']:
                    newvalue = self.digital2Digital(data, value)
                else:
                    newvalue = self.analog2Digital(data, value)
            else:
                if dbItem['digital']:
                    newvalue = self.digital2Analog(data, value)
                else:
                    newvalue = self.analog2Analog(data, value, True)
        return newvalue

    def set(self, tag, data):
        rdata = {}
        error = False
        value = 0
        if not self.checkDbValid():
            self.getDb()
        try:
            dbItem = self.checkDbItem(tag, data["type"])
            if dbItem and not "const" in data and data["param"]:
                value = self.processParam(dbItem, data)
                tag, value = self.bdaclient.Send(tag, value)
                if not tag:
                    error = True
            elif not "const" in data:
                error = True
            if not error:
                if "state" in data:
                    if data["state"]:
                        rdata["state"] = data["state"]
                    else:
                        error = True
                else:
                    rdata["state"] = "on"
            if not error:
                #rdata["tag"] = data["tag"]
                rdata["type"] = data["type"]
                rdata["value"] = self.processValue(dbItem, data, value)
        except:
            pass

        return rdata

    def get(self, tag, data):
        rdata = {}
        error = False
        value = 0
        if not self.checkDbValid():
            self.getDb()
        try:
            dbItem = self.checkDbItem(tag, data["type"])
            if dbItem and not "const" in data:
                if self.checkQueryValid():
                    value = dbItem["value"]
                    error = False
                else:
                    tag, value = self.bdaclient.Send(tag, None)
                    if not tag:
                        error = True
            elif not "const" in data:
                error = True
            if not error:
                if "state" in data:
                    if data["state"]:
                        rdata["state"] = data["state"]
                    else:
                        error = True
                else:
                    rdata["state"] = "on"
            if not error:
                #rdata["tag"] = data["tag"]
                rdata["type"] = data["type"]
                rdata["value"] = self.processValue(dbItem, data, value)
        except:
            pass

        return rdata

    def analog2Digital(self, data, value):
        trueop = "eq"
        opval = 1.0
        tstval = 1.0
        try:
            tstval = float(value)
        except:
            pass
        if "trueop" in data:
            trueop = data["trueop"]
        if "opval" in data:
            try:
                opval = float(data["opval"])
            except:
                pass
        retval = False
        if trueop == "eq":
            retval = (tstval == opval)
        elif trueop == "ne":
            retval = (tstval != opval)
        elif trueop == "lt":
            retval = (tstval < opval)
        elif trueop == "gt":
            retval = (tstval > opval)
        elif trueop == "le":
            retval = (tstval <= opval)
        elif trueop == "ge":
            retval = (tstval >= opval)
        else:
            retval = (tstval > 0)

        return retval

    def digital2Analog(self, data, value):
        falseval = 0.0
        trueval = 1.0
        tstval = 1.0
        try:
            tstval = float(value)
        except:
            pass
        if "falseval" in data:
            try:
                falseval = float(data["falseval"])
            except:
                pass
        if "trueval" in data:
            try:
                trueval = float(data["trueval"])
            except:
                pass
        retval = falseval
        if tstval:
            retval = trueval
        return retval

    def digital2Digital(self, data, value):
        newvalue = False
        if "falseval" in data or "trueval" in data:
            if self.digital2Analog(data, value):
                newvalue = True
            else:
                newvalue = False
        else:
            newvalue = self.analog2Digital(data, value)

        return newvalue

    def analog2Analog(self, data, value, inverse = False):
        newvalue = 0.0
        a = 1.0
        b = 0.0
        tstval = 1.0
        try:
            tstval = float(value)
        except:
            pass

        if "a" in data:
            try:
                a = float(data["a"])
            except:
                pass
        if "b" in data:
            try:
                b = float(data["b"])
            except:
                pass

        if inverse:
            newvalue = (tstval - b) / a
        else:
            newvalue = a * tstval + b
        return newvalue

######################### MAIN ##########################
if __name__ == "__main__":
    pass
