# -*- coding: utf-8 -*-
#########################################################
# SERVICE : MqttHandler.py                              #
#           Handles communication and protocol with     #
#           MQTT                                        #
#           I. Helwegen 2023                            #
#########################################################

"""
TBD:
- What ha devices do we allow? --> Done
    - events: digital smarthome input (mqtt publish)
    - switch: digital smarthome status (mqtt subscribe)
    analog io is not implemented (yet), conversion however does work
    other inputs: sensor, digital sensor (publish) device_class is always none (don't fill)
    digital, analog for non ha
    for publish, only direct feedback to google???????
- check settings --> 433mqtt --> Done
- Check xml with 433mqtt --> Done
- implement discos (at start and 'online') --> Done
- how do we retrieve statuses? callback at received and store in memory for when requested. 
    If not retained, then value is default.
- MUTEX --> not required

Device info <hadevice>:
<name> device name = devicename key <TableLamp>
<mf> manufacturer = <deviceInfo> <manufacturer>domotion</manufacturer>
<mdl> model = <deviceInfo> <model>domotv</model>

check devices:
What do I want to do (from google)
* switch devices on or off
* switch blind percentage
* switch dimmer percentage
* read status
* read analog, digital

process flow: 
hey google, light on -> mqtt publish (from py) light on -> mqtt subscribe (ha) stat_t light on -> mqtt publish (ha) hw light on
type(s): sensor (power_factor % or none [generic sensor] ), binary_sensor (light or power), event (button, doorbell)

query whatever <- mqtt subscribe (from py) whatever <- mqtt publish (ha) whatever <- mqtt read from device
type(s): switch (none [generic switch]), number (none)

implement dir --> Done getDir
implement retain --> Done
publish retain if not event, get retained value is listen if no listenmqtt --> Done
subscribe to listenmqtt or retained publish --> Done
implement listenmqtt return --> Done
implement no maintopic -> Done
if subscribe, return cmd_t to stat_t --> Done

TBD: set try/ except in gshMux !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""

####################### IMPORTS #########################
import json
from .convert import convert
from threading import Lock
from webif.devices import devices
from uuid import getnode
try:
    import paho.mqtt.client as mqttclient
    ifinstalled = True
except ImportError:
    ifinstalled = False
#########################################################

####################### GLOBALS #########################
RETAIN       = True
RETAINEVENT  = False
QOS          = 0
HASTATUS     = "status"
HAONLINE     = "online"
CONFIG       = "config"
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : MqttHandler                                   #
#########################################################
class MqttHandler(object):
    def __init__(self, logger, settings, file = "", name = ""):
        self.logger = logger
        self.settings = settings
        self.file = file
        self.name = name
        self.doha = False
        self.convert = convert()
        self.subscribeList = {}
        self.mutex = Lock()
        if ifinstalled:
            self.client = mqttclient.Client("Smarthome_" + format(getnode(),'X')[-6:])  #create new instance
            self.client.on_message=self._onmessage #attach function to callback
            self.client.on_connect=self._onconnect  #bind call back function
            self.client.on_disconnect=self._ondisconnect  #bind call back function
            self.client.on_log=self._onlog
        else:
            self.client = None

    def __del__(self):
        del self.mutex
        if self.client:
            del self.client

    def connect(self):
        try:
            self.logger.info("running")

            if (not self.client):
                self.logger.warning("mqtt not installed, terminating")
                self.terminate()
            else:
                if "username" in self.settings and self.settings["username"]:
                    if "password" in self.settings and self.settings["password"]:
                        self.client.username_pw_set(self.settings["username"], password=self.settings["password"])
                    else:
                        self.client.username_pw_set(self.settings["username"], password=None)
                try:
                    self.client.connect(self.settings["brokeraddress"], port=int(self.settings["port"])) #connect to broker
                    self.client.loop_start() #start the loop
                except:
                    self.logger.error("Invalid connection, check server address")
                    return
        except Exception as e:
            self.logger.exception(e)
            return

        ####### Subscribe topics
        self.getSubscriptions()
        if "hatopic" in self.settings.keys():
            if self.settings["hatopic"]:
                self.client.subscribe(self.buildTopic(self.settings["hatopic"], HASTATUS), QOS)
                self.doha = True

        ####### Write disco topics
        if self.doha:
            for key, disco in self.getDiscoTopics().items():
                self.client.publish(disco["topic"], json.dumps(disco["disco"]), QOS, RETAIN)
                self.logger.debug("MQTT: HA Discovery [" + disco["topic"] + "]: " + json.dumps(disco["disco"]))

    def terminate(self):
        self.logger.info("terminating")
        if self.client:
            #self.client.wait_for_publish() # wait for all messages published
            self.client.loop_stop()    #Stop loop
            self.client.disconnect() # disconnect

    def _onlog(self, client, userdata, level, buf):
        self.logger.debug(buf)

    def _onmessage(self, client, userdata, message):
        if self.doha and self.buildTopic(self.settings["hatopic"], HASTATUS) == message.topic:
            if message.payload.decode('utf-8') == HAONLINE:
                self.logger.debug("MQTT: received HA online, issue HA Discovery")
                for key, disco in self.getDiscoTopics().items():
                    self.client.publish(disco["topic"], json.dumps(disco["disco"]), QOS, RETAIN)
                    self.logger.debug("MQTT: HA Discovery [" + disco["topic"] + "]: " + json.dumps(disco["disco"]))
        self.mutex.acquire()
        if message.topic in self.subscribeList.keys():
            self.subscribeList[message.topic] = message.payload.decode('utf-8')
        self.mutex.release()

    def _onconnect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected OK, Returned code = " + str(rc))
            self.connected = True
            self.rcDisconnect = 0
        else:
            if self.rcConnect != rc:
                self.logger.info("Bad connection, Returned code = " + str(rc))
            self.connected = False
        self.rcConnect = rc

    def _ondisconnect(self, client, userdata, rc):
        if rc == 0 or self.rcDisconnect != rc:
            self.logger.info("Disconnected, Returned code = " + str(rc))
            self.rcConnect = 0
        self.connected = False
        self.rcDisconnect = rc

    def subscribe(self, subTopicsList):
        if (self.client):
            qos = 0
            if "qos" in self.settings:
                qos = int(self.settings["qos"])
            for key in self.subscribeList.keys():
                if not key in subTopicsList:
                    try:
                        del self.subscribeList[key]
                    except:
                        pass
                    self.client.unsubscribe(key)
            for subTopic in subTopicsList:
                if subTopic not in self.subscribeList.keys():
                    self.client.subscribe(subTopic, qos)
                    self.subscribeList[subTopic] = None

    def publish(self, pubTopic, value, retain = RETAIN):
        qos = 0
        if "qos" in self.settings:
            qos = int(self.settings["qos"])
        if pubTopic:
            self.client.publish(pubTopic, value, qos, retain)

        #########################################################################################################33

    def getValueFromList(self, subTopic):
        error = True
        value = None
        if subTopic:
            if subTopic in self.subscribeList.keys():
                value = self.subscribeList[subTopic]
                error = False

        return error, value

    def getSubscriptions(self):
        subTopicsList = []
        myDevices = devices(self.file, self.name).getAll()
        for id, data in myDevices.items():
            if "backEnd" in data:
                if "device" in data["backEnd"]:
                    if data["backEnd"]["device"].lower() == "mqtt":
                        for tag, datum in data["backEnd"].items():
                            if tag != "device":
                                if self.getDir(datum): # send to HA
                                    subTopic = self.getSubListTopic(tag, datum)
                                else:
                                    subTopic = self.getSubTopic(tag, datum)
                                if subTopic:
                                    subTopicsList.append(subTopic)
        self.subscribe(subTopicsList)
        del myDevices

    def getDiscoTopics(self):
        discos = {}
        myDevices = devices(self.file, self.name).getAll()
        for idd, data in myDevices.items():
            try:
                #topic = ""
                if "backEnd" in data:
                    if "device" in data["backEnd"]:
                        if data["backEnd"]["device"].lower() == "mqtt":
                            for tag, datum in data["backEnd"].items():
                                if tag != "device" and "hadisco" in datum:
                                    disco = {}
                                    ids = format(getnode(),'X')[-6:]
                                    dev = {}
                                    dev["name"] = tag
                                    dev["mf"] = ""
                                    dev["mdl"] = ""
                                    if "deviceInfo" in data:
                                        if "manufacturer" in data["deviceInfo"]:
                                            dev["mf"] = data["deviceInfo"]["manufacturer"]
                                        if "model" in data["deviceInfo"]:
                                            dev["mdl"] = data["deviceInfo"]["model"]
                                    dev["ids"] = [ids + "_" + datum["hadisco"]["name"]]
                                    hadisco = datum["hadisco"]
                                    main_t = ""
                                    if "maintopic" in datum["itemmqtt"]:
                                        hadisco["~"] = datum["itemmqtt"]["maintopic"]
                                        main_t = "~"
                                    hadisco["uniq_id"] = ids + "_" + datum["hadisco"]["name"]
                                    isSend = self.getDir(datum)
                                    if not isSend:
                                        if "cmd_t" in datum["itemmqtt"].keys():
                                            hadisco["cmd_t"] = self.buildTopic(main_t,datum["itemmqtt"]["cmd_t"])
                                        elif "command_topic" in datum["itemmqtt"].keys():
                                            hadisco["cmd_t"] = self.buildTopic(main_t,datum["itemmqtt"]["command_topic"])
                                    if "stat_t" in datum["itemmqtt"].keys():
                                        hadisco["stat_t"] = self.buildTopic(main_t,datum["itemmqtt"]["stat_t"])
                                    elif "status_topic" in datum["itemmqtt"].keys():
                                        hadisco["stat_t"] = self.buildTopic(main_t,datum["itemmqtt"]["status_topic"])  
                                    haType = "none"
                                    if "type" in datum:
                                        digital = self.convert.isDigital(data)
                                        type = "digital" if digital else "analog"
                                        if "type" in datum and not datum["type"].lower() == "same":
                                            type = datum["type"].lower()
                                        if isSend:
                                            if type == "analog":
                                                haType = "sensor"
                                            elif type == "digital":
                                                haType = "binary_sensor"
                                                hadisco["pl_on"] = "1"
                                                hadisco["pl_off"] = "0"
                                            elif type == "event":
                                                haType = "event"
                                                hadisco["event_types"] = ["1", "0"]
                                        else:
                                            if type == "analog":
                                                haType = "number"
                                            elif type == "digital":
                                                haType = "switch"
                                                hadisco["pl_on"] = "1"
                                                hadisco["pl_off"] = "0"
                                    hadisco["dev"] = dev
                                    disco["disco"] = hadisco
                                    if "dev_cla" in datum["hadisco"]:
                                        dev_cla = datum["hadisco"]["dev_cla"]
                                    else:
                                        dev_cla = haType
                                    disco["topic"] = self.buildTopic(self.buildTopic(self.buildTopic(self.settings["hatopic"],haType), datum["hadisco"]["name"] + "_" + dev_cla), CONFIG)
                                    discos[tag] = disco
            except:
                pass
        return discos

    def getPubTopic(self, tag, tagdata, statOnly = False):
        topic = ""
        if "itemmqtt" in tagdata:
            main_t = ""
            if "maintopic" in tagdata["itemmqtt"]:
                main_t = tagdata["itemmqtt"]["maintopic"]
            if "stat_t" in tagdata["itemmqtt"]:
                pubtopic = tagdata["itemmqtt"]["stat_t"]
            elif statOnly:
                pubtopic = ""
            else:
                pubtopic = tag
            if pubtopic:
                topic = self.buildTopic(main_t, pubtopic)
        return topic

    def getSubTopic(self, tag, tagdata):
        topic = ""
        if "itemmqtt" in tagdata:
            main_t = ""
            if "maintopic" in tagdata["itemmqtt"]:
                main_t = tagdata["itemmqtt"]["maintopic"]
            if "cmd_t" in tagdata["itemmqtt"]:
                subtopic = tagdata["itemmqtt"]["cmd_t"]
            else:
                subtopic = tag
            topic = self.buildTopic(main_t, subtopic)
        return topic

    def getListenTopic(self, tag, tagdata):
        topic = ""
        if "listenmqtt" in tagdata:
            main_t = ""
            if "maintopic" in tagdata["listenmqtt"]:
                main_t = tagdata["listenmqtt"]["maintopic"]
            if "sub_t" in tagdata["listenmqtt"]:
                subtopic = tagdata["listenmqtt"]["sub_t"]
            else:
                subtopic = tag
            topic = self.buildTopic(main_t, subtopic)
        return topic
    
    def getSubListTopic(self, tag, tagdata):
        topic = ""
        if "listenmqtt" in tagdata:
            topic = self.getListenTopic(tag, tagdata)
        else: # subscribe to Publish topic
            topic = self.getPubTopic(tag, tagdata)
        return topic

    def getDir(self, data):
        isSend = True
        if "dir" in data:
            if data["dir"].lower() != "send":
                isSend = False
        return isSend

    def buildTopic(self, maintopic, subtopic):
        topic = ""
        if maintopic:
            if maintopic.startswith("/"):
                topic = maintopic[1:]
            else:
                topic = maintopic
            if topic.endswith("/"):
                topic = topic[0:-1]
        if subtopic:
            if not subtopic.startswith("/"):
                topic += "/"
            topic += subtopic
            if topic.endswith("/"):
                topic = topic[0:-1]
        return topic

    def processParam(self, data):
        value = 0
        retain = RETAIN
        if "retain" in self.settings:
            retain = self.settings["retain"]
        digital = self.convert.isDigital(data)
        type = "digital" if digital else "analog"
        if "type" in data and not data["type"].lower() == "same":
            type = data["type"].lower()
        if type == "event":
            retain = False
        if digital:
            if type == "digital" or type == "event":
                value = 1 if self.convert.digital2Digital(data, data["value"]) else 0
            else:
                value = self.convert.digital2Analog(data, data["value"])
        else:
            if type == "digital" or type == "event":
                value = 1 if self.convert.analog2Digital(data, data["value"]) else 0
            else:
                value = self.convert.analog2Analog(data, data["value"])
        return value, retain

    def processValue(self, data, value):
        newvalue = {}
        digital = self.convert.isDigital(data)
        type = "digital" if digital else "analog"
        if "type" in data and not data["type"].lower() == "same":
            type = data["type"].lower()
        if "const" in data:
            value = data["const"]
        else:
            if digital:
                if type == "digital" or type == "event":
                    newvalue = self.convert.digital2Digital(data, value)
                else:
                    newvalue = self.convert.analog2Digital(data, value)
            else:
                if type == "digital" or type == "event":
                    newvalue = self.convert.digital2Analog(data, value)
                else:
                    newvalue = self.convert.analog2Analog(data, value, True)
        return newvalue

    def set(self, tag, data):
        rdata = {}
        error = False
        value = 0
        try:
            if not "const" in data and data["param"]:
                value, retain = self.processParam(data)
                self.publish(self.getPubTopic(tag, data), value, retain)
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
                rdata["value"] = self.processValue(data, value)
                # always return setpoint, current on get only as processing delay may issue
        except:
            pass

        return rdata

    def get(self, tag, data):
        rdata = {}
        error = False
        value = 0
        try:
            if not "const" in data:
                error, value = self.getValueFromList(self.getSubListTopic(tag, data))
            if not error:
                if "state" in data:
                    if data["state"]:
                        rdata["state"] = data["state"]
                    else:
                        error = True
                else:
                    rdata["state"] = "on"
            if not error:
                if not self.getDir(data):
                    self.publish(self.getPubTopic(tag, data, True), value, False) # neever retain feedback value
                #rdata["tag"] = data["tag"]
                rdata["type"] = data["type"]
                rdata["value"] = self.processValue(data, value)
        except:
            pass

        return rdata

######################### MAIN ##########################
if __name__ == "__main__":
    pass
