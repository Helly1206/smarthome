# -*- coding: utf-8 -*-
#########################################################
# SERVICE : xmlsettings.py                              #
#           Load xml settings files                     #
#                                                       #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
from os import path, getcwd
import xml.etree.ElementTree as ET

#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : xmlsettings                                   #
#########################################################
class xmlsettings(object):
    def __init__(self, xmlfile, file = "", name = ""):
        self.settings = {}
        self.xmlfile = xmlfile
        self.file = file
        self.name = name
        self._readXML()

    def __del__(self):
        del self.settings

    def get(self, setting):
        retdevice = ""
        try:
            retdevice = self.settings[setting]
        except:
            pass
        return retdevice

    def getAll(self):
        return self.settings

    def _readXML(self):
        del self.settings
        self.settings = {}
        try:
            xmlfile=self._getXML()
            if path.isfile(xmlfile):
                tree = ET.parse(xmlfile)
                root = tree.getroot()
                self.settings = self.parseKids(root, True)
        except:
            pass

    def gettype(self, text, txtype = True):
        try:
            retval = int(text)
        except:
            try:
                retval = float(text)
            except:
                if text:
                    if text.lower() == "false":
                        retval = False
                    elif text.lower() == "true":
                        retval = True
                    elif txtype:
                        retval = text
                    else:
                        retval = ""
                else:
                    retval = ""

        return retval

    def parseKids(self, item, isRoot = False):
        db = {}
        if self.hasKids(item):
            for kid in item:
                if self.hasKids(kid):
                    db[kid.tag] = self.parseKids(kid)
                else:
                    db.update(self.parseKids(kid))
        elif not isRoot:
            db[item.tag] = self.gettype(item.text)
        return db

    def hasKids(self, item):
        retval = False
        for kid in item:
            retval = True
            break
        return retval

    def _getXML(self):
        etcpath = path.join("/etc", self.name)
        xmlfile = self.xmlfile
        basepath = path.dirname(path.abspath(self.file))
        if path.isfile(path.join(etcpath,xmlfile)): # first look in etc
            xmlfile = path.join(etcpath,xmlfile)
        elif path.isfile(path.join(path.expanduser('~'),xmlfile)): # then look in home folder
                xmlfile = path.join(path.expanduser('~'),xmlfile)
        elif path.isfile(path.join(basepath,xmlfile)): # then look in home folder
                xmlfile = path.join(basepath,xmlfile)
        return xmlfile

######################### MAIN ##########################
if __name__ == "__main__":
    pass
