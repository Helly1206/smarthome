#!/usr/bin/python3

# -*- coding: utf-8 -*-
#########################################################
# SERVICE : gshWebStarter.py                            #
#           Python starting gsh web application         #
#           I. Helwegen 2017                            #
#########################################################
####################### IMPORTS #########################
import subprocess
import xml.etree.ElementTree as ET
import signal
import sys
import os
from getopt import getopt, GetoptError
#########################################################

####################### GLOBALS #########################
VERSION="1.00"
XML_FILENAME = "smarthome.xml"
#########################################################
# Class : gshWebStarter                                 #
#########################################################
class gshWebStarter(object):
    def __init__(self):
        self.ports=[]
        self.procs=[]
        signal.signal(signal.SIGINT, self.exit_app)
        signal.signal(signal.SIGTERM, self.exit_app)

    def __del__(self):
        pass

    def run(self, argv):
        Debug=False
        index = 0
        try:
            opts, args = getopt(argv,"hd",["help","debug"])
        except GetoptError:
            print("gsh web starter")
            print("Version: " + VERSION)
            print(" ")
            print("Enter 'gshWebStarter -h' for help")
            exit(2)
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print("gsh web starter")
                print("Version: " + VERSION)
                print(" ")
                print("Usage:")
                print("         gshWebStarter <args>")
                print("         -h, --help: this help file")
                print("         -d, --debug: start in debug mode on port 5000")
                exit()
            elif opt in ("-d", "--debug"):
                Debug=True
        if Debug:
            print ("Starting debug http server on port 5000")
            index = 1
            self.procs.append(subprocess.Popen(["python3", "webif/gsh.py","-p 5000"]))
        else:
            tree = ET.parse(self.GetXML())
            root = tree.getroot()
            for child in root:
                if child.tag == "webserver":
                    name=child.tag
                    ssl=False
                    if index>4:
                        print(("Server [%s] not started as maximum of 5 servers obtained"%name))
                        continue

                    textdep=child.find('externaldeployment')
                    if textdep != None:
                        if (textdep.text.lower() == "true"):
                            print(("Server [%s] externally deployed"%name))
                            continue
                    index += 1
                    tssl=child.find('ssl')
                    if tssl != None:
                        if (tssl.text.lower() == "true"):
                            ssl = True
                    if ssl:
                        tcert=child.find('certificate')
                        if tcert != None:
                            cert = tcert.text
                        else:
                            ssl=False
                        tkey=child.find('privatekey')
                        if tkey != None:
                            key = tkey.text
                        else:
                            ssl=False
                    port=5000
                    tport=child.find('port')
                    if tport != None:
                        port=int(tport.text)
                    while port in self.ports:
                        port +=1
                    self.ports.append(port)

                    if ssl:
                        print(("Starting https server [%s] on port: %d"%(name,port)))
                        self.procs.append(subprocess.Popen(["python3", self.GetGshWeb(),"-p {p}".format(p=port), "-s", "-c {c}".format(c=cert), "-k {k}".format(k=key)]))
                    else:
                        print(("Starting http server [%s] on port: %d"%(name,port)))
                        self.procs.append(subprocess.Popen(["python3", self.GetGshWeb(),"-p {p}".format(p=port)]))

        if index>0:
            signal.pause()

    def GetXML(self):
        etcpath = "/etc/smarthome/"
        XMLpath = ""
        # first look in etc
        if os.path.isfile(os.path.join(etcpath,XML_FILENAME)):
            XMLpath = os.path.join(etcpath,XML_FILENAME)
        else:
            # then look in home folder
            if os.path.isfile(os.path.join(os.path.expanduser('~'),XML_FILENAME)):
                XMLpath = os.path.join(os.path.expanduser('~'),XML_FILENAME)
            else:
                # look in local folder, hope we may write
                if os.path.isfile(os.path.join(".",XML_FILENAME)):
                    if os.access(os.path.join(".",XML_FILENAME), os.W_OK):
                        XMLpath = os.path.join(".",XML_FILENAME)
                    else:
                        self.logger.critical("No write access to XML file, exit")
                        exit(1)
                else:
                    self.logger.critical("No XML file found, exit")
                    exit(1)
        return (XMLpath)

    def GetGshWeb(self):
        path=os.path.dirname(os.path.abspath(__file__))
        main_pos=path.find("main")
        if (main_pos>0):
            path=path[:main_pos-1]

        return os.path.join(path,"webif","gsh.py")

    def exit_app(self, signum, frame):
        print ("Exit")
        for proc in self.procs:
            proc.terminate()

#########################################################
if __name__ == "__main__":
    gshWebStarter().run(sys.argv[1:])
