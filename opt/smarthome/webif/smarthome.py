# -*- coding: utf-8 -*-
#########################################################
# SERVICE : smarthome.py                                #
#           Python smarthome functions for web app      #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
from appsaccess import appsaccess
from devices import devices
from itertools import product
from threading import Lock
import logging

#########################################################

####################### GLOBALS #########################
# Error codes used for SmartHomeError class
# https://developers.google.com/actions/smarthome/create-app#error_responses
ERR_DEVICE_OFFLINE = "deviceOffline"
ERR_DEVICE_NOT_FOUND = "deviceNotFound"
ERR_VALUE_OUT_OF_RANGE = "valueOutOfRange"
ERR_NOT_SUPPORTED = "notSupported"
ERR_PROTOCOL_ERROR = "protocolError"
ERR_UNKNOWN_ERROR = "unknownError"
ERR_FUNCTION_NOT_SUPPORTED = "functionNotSupported"
ERR_CHALLENGE_NEEDED = "challengeNeeded"

INTENT_SYNC       = 'action.devices.SYNC'
INTENT_QUERY      = 'action.devices.QUERY'
INTENT_EXECUTE    = 'action.devices.EXECUTE'
INTENT_DISCONNECT = 'action.devices.DISCONNECT'

#########################################################

###################### FUNCTIONS ########################
class SmartHomeError(Exception):
    """Google Assistant Smart Home errors.
    https://developers.google.com/actions/smarthome/create-app#error_responses
    """
    def __init__(self, code, msg):
        """Log error code."""
        super().__init__(msg)
        self.code = code

#########################################################

#########################################################
# Class : smarthome                                     #
#########################################################
class smarthome(object):
    def __init__(self, file = "", name = "", basename = "SmartHome"):
        self.logger  = logging.getLogger('{}.smarthome'.format(basename))
        self.devices = devices(file, name)
        self.client  = appsaccess(basename)
        self.mutex   = Lock()

    def __del__(self):
        del self.client
        del self.devices
        del self.mutex

    def terminate(self):
        if self.client:
            self.client.terminate()

    def process(self, message, token):

        request_id = message.get('requestId')  # type: str
        inputs = message.get('inputs')  # type: list

        if len(inputs) != 1:
            return {'requestId': request_id, 'payload': {'errorCode': ERR_PROTOCOL_ERROR}}

        intent = inputs[0].get('intent')

        if intent == INTENT_SYNC:
            handler = self.smarthome_sync
        elif intent == INTENT_QUERY:
            handler = self.smarthome_query
        elif intent == INTENT_EXECUTE:
            handler = self.smarthome_exec
        else: # disconnect not implemented yet
            return {'requestId': request_id, 'payload': {'errorCode': ERR_PROTOCOL_ERROR}}

        try:
            self.mutex.acquire()
            result = handler(inputs[0].get('payload'), token)
            self.mutex.release()
            return {'requestId': request_id, 'payload': result}

        except SmartHomeError as err:
            self.logger.error("SmartHome Error on request, error code: {}".format(err.code))
            return {'requestId': request_id, 'payload': {'errorCode': err.code}}

        except Exception as e:
            self.logger.exception(e)
            return {'requestId': request_id, 'payload': {'errorCode': ERR_UNKNOWN_ERROR}}


    def smarthome_sync(self, payload, token):
        """Handle action.devices.SYNC request.
        https://developers.google.com/assistant/smarthome/reference/intent/sync
        """
        devices = []
        self.devices.reload()
        for deviceId, device in self.devices.getAll().items():
            try:
                dev = {}
                dev["id"] = deviceId
                dev["type"] = device["type"]
                dev["traits"] = device["traits"].split(",")
                names = {}
                names["name"] = device["name"]["name"]
                if "defaultNames" in device["name"] and len(device["name"]["defaultNames"]) > 0:
                    names["defaultNames"] = device["name"]["defaultNames"].split(",")
                if "nickNames" in device["name"] and len(device["name"]["nickNames"]) > 0:
                    names["nicknames"] = device["name"]["nickNames"].split(",")
                dev["name"]= names
                dev["willReportState"] = device["willReportState"]
                if "attributes" in device and len(device["attributes"]) > 0:
                    dev["attributes"]= device["attributes"]
                if "roomHint" in device and len(device["roomHint"]) > 0:
                    dev["roomHint"]= device["roomHint"]
                dev["deviceInfo"] = device["deviceInfo"]

                devices.append(dev)
            except:
                self.logger.error("Protocol error SYNC: Incorrect parameter format for {}".format(deviceId))
                raise SmartHomeError(ERR_PROTOCOL_ERROR,
                    'Incorrect parameter format for {}'.format(deviceId))
        return {
            'agentUserId': token.get('userAgentId', None),
            'devices': devices,
        }


    def smarthome_query(self, payload, token):
        """Handle action.devices.QUERY request.
        https://developers.google.com/assistant/smarthome/reference/intent/query
        """
        devices = {}
        try:
            for device in payload.get('devices', []):
                devid = device['id']
                devOnline = False
                status = "SUCCESS"
                errorCode = ERR_FUNCTION_NOT_SUPPORTED
                shdadevice, shdadata = self.setshdaData(devid)
                if not shdadata:
                    status = "ERROR"
                    errorCode = ERR_DEVICE_NOT_FOUND
                else:
                    rdata = self.client.Send(shdadevice, shdadata)
                    if rdata:
                        if self.checkshdaData(devid, rdata):
                            values = self.getshdaValues(rdata)
                            if values:
                                devOnline = True
                        else:
                            status = "ERROR"
                            errorCode = ERR_UNKNOWN_ERROR

                if status == "SUCCESS":
                    devices[devid] = {
                        "status": status,
                        "online": devOnline
                    }
                    devices[devid].update(values)
                else:
                    self.logger.error("Smarthome Error QUERY, error code: {}".format(errorCode))
                    devices[devid] = {
                        "status": status,
                        "online": devOnline,
                        "errorCode": errorCode
                    }
        except:
            self.logger.error("Protocol error QUERY: Incorrect parameter format in devices")
            raise SmartHomeError(ERR_PROTOCOL_ERROR,
                'Incorrect parameter format in devices')

        return {'devices': devices}

    def smarthome_exec(self, payload, token):
        """Handle action.devices.EXECUTE request.
        https://developers.google.com/assistant/smarthome/reference/intent/execute
        """
        entities = {}
        results = []

        try:
            for command in payload['commands']:
                for device, execution in product(command['devices'],
                                                 command['execution']):
                    devid = device['id']
                    devOnline = False
                    status = "SUCCESS"
                    errorCode = ERR_FUNCTION_NOT_SUPPORTED
                    shdadevice, shdadata = self.setshdaData(devid, execution)
                    if not shdadata:
                        status = "ERROR"
                        errorCode = ERR_DEVICE_NOT_FOUND
                    else:
                        rdata = self.client.Send(shdadevice, shdadata)
                        if rdata:
                            if self.checkshdaData(devid, rdata):
                                values = self.getshdaValues(rdata)
                                if values:
                                    devOnline = True
                            else:
                                status = "ERROR"
                                errorCode = ERR_UNKNOWN_ERROR

                    result = {}
                    if status == "SUCCESS":
                        result = {
                            "ids": [devid],
                            "status": status,
                            "states": {
                                "online": devOnline
                            }
                        }
                        result["states"].update(values)
                    else:
                        self.logger.error("Smarthome Error EXECUTE, error code: {}".format(errorCode))
                        result = {"ids": [devid], "status": status, "errorCode": errorCode}


                    results.append(result)
        except:
            self.logger.error("Protocol error EXECUTE: Incorrect parameter format in devices or execution")
            raise SmartHomeError(ERR_PROTOCOL_ERROR,
                'Incorrect parameter format in devices or execution')

        return {'commands': results}

    def setshdaData(self, devid, exec = {}):
        device = ""
        data = {}
        try:
            backend = self.devices.get(devid)["backEnd"]
            device = backend["device"]
            if exec:
                for param, value in exec["params"].items():
                    for tag, item in backend.items():
                        if tag != "device":
                            if item["param"] == param:
                                data[tag] = item.copy()
                                data[tag]["value"] = value
                                if "state" in data[tag]:
                                    if data[tag]["state"] == data[tag]["param"]:
                                        del data[tag]["state"]
                                else:
                                    data[tag]["state"] = ""
                                break

            for tag, item in backend.items():
                if tag != "device" and not tag in data:
                    if "state" in item:
                        data[tag] = item.copy()
                        if "param" in data[tag]:
                            del data[tag]["param"]
        except:
            pass
        return device, data

    def checkshdaData(self, devid, rdata):
        dataOk = False
        try:
            backend = self.devices.get(devid)['backEnd']
            if rdata['device'] == backend['device']:
                for tag, item in rdata.items():
                    for btag, bitem in backend.items():
                        if tag != "device":
                            if btag == tag and item["type"] == bitem["type"]:
                                dataOk = True
                                break
        except:
            pass
        return dataOk

    def getshdaValues(self, rdata):
        values = {}
        try:
            for tag, item in rdata.items():
                if tag != "device":
                    values.update({item["state"]: item["value"]})
        except:
            pass
        return values
