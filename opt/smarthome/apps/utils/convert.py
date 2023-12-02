# -*- coding: utf-8 -*-
#########################################################
# SERVICE : convert.py                                  #
#           Converts analog to digigtal and vise versa  #
#                                                       #
#           I. Helwegen 2023                            #
#########################################################

####################### IMPORTS #########################

#########################################################

####################### GLOBALS #########################

# Not all analog values are listed for mqtt control
SmartHomeAnalog = ["brightness", "brightnessRelativePercent", "brightnessRelativeWeight", "temperatureK",
                   "spectrumRgb", "temperature", "spectrumRGB", "amount", "rawValue", "currentFanSpeedPercent",
                   "fanSpeedPercent", "fanSpeedRelativeWeight", "fanSpeedRelativePercent", "duration",
                   "humiditySetpointPercent", "humidityAmbientPercent", "humidity", "openPercent",
                   "rotationDegrees", "rotationPercent", "temperatureSetpointCelsius",
                   "temperatureAmbientCelsius", "thermostatTemperatureSetpoint", "currentVolume",
                   "volumeLevel", "relativeSteps"]

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : convert                                       #
#########################################################
class convert(object):
    def __init__(self):
        pass

    def __del__(self):
        pass

    def isDigital(self, data):
        digital = True
        if "state" in data:
            if data["state"] in SmartHomeAnalog:
                digital = False
        return digital

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
