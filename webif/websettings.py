# -*- coding: utf-8 -*-
#########################################################
# SERVICE : websettings.py                              #
#           Load settings, equal to settings.py         #
#           I. Helwegen 2019                            #
#                                                       #
#########################################################

####################### IMPORTS #########################
from os import path
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

#########################################################

####################### GLOBALS #########################
ENCODING      = 'utf-8'
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : websettings                                   #
#########################################################
class websettings(object):
    def __init__(self, file = "", name = ""):
        self.settings = {}
        self.file = file
        self.name = name
        self._readSettingsXML()

    def __del__(self):
        del self.settings

    def update(self):
        self._updateXML()

    def getSetting(self, setting):
        retsetting = ""
        try:
            retsetting = self.settings[setting]
        except:
            pass
        return retsetting

    def setSetting(self, setting, value):
        try:
            self.settings[setting] = value
        except:
            pass
        return

    def _readSettingsXML(self):
        del self.settings
        self.settings = {}
        try:
            xmlfile=self._getXML()
            if path.isfile(xmlfile):
                tree = ET.parse(xmlfile)
                root = tree.getroot()
                self.settings = self._parseKids(root, True)
        except:
            pass

    def _parseKids(self, item, isRoot = False):
        db = {}
        if self._hasKids(item):
            for kid in item:
                if self._hasKids(kid):
                    db[kid.tag] = self._parseKids(kid)
                else:
                    db.update(self._parseKids(kid))
        elif not isRoot:
            db[item.tag] = self._gettype(item.text)
        return db

    def _hasKids(self, item):
        retval = False
        for kid in item:
            retval = True
            break
        return retval

    def _updateXML(self):
        db = ET.Element('smarthome')
        self._buildXML(db, self.settings)

        XMLpath = self._getXML()

        with open(XMLpath, "w") as xml_file:
            xml_file.write(self._prettify(db))

    def _buildXML(self, xmltree, item):
        if isinstance(item, dict):
            for key, value in item.items():
                kid = ET.SubElement(xmltree, key)
                self._buildXML(kid, value)
        else:
            xmltree.text = self._settype(item)

    def _prettify(self, elem):
        """Return a pretty-printed XML string for the Element.
        """
        rough_string = ET.tostring(elem, ENCODING)
        reparsed = parseString(rough_string)
        return reparsed.toprettyxml(indent="\t").replace('<?xml version="1.0" ?>','<?xml version="1.0" encoding="%s"?>' % ENCODING)

    def _gettype(self, text, txtype = True):
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

    def _settype(self, element):
        retval = ""
        if type(element) == bool:
            if element:
                retval = "true"
            else:
                retval = "false"
        elif element != None:
            retval = str(element)

        return retval

    def _getXML(self):
        etcpath = path.join("/etc", self.name)
        xmlfile = self.name + '.xml'
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
