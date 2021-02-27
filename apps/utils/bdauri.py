# -*- coding: utf-8 -*-
#########################################################
# SERVICE : bdauri.py                                   #
#           Builds and extracts uri for bda access      #
#           I. Helwegen 2018                            #
#########################################################

# URI API (no ports are allowed in URI):
# auth and host bda://username:password@address/deviceurl/set?....
# no auth bda://address/deviceurl/set?....
# no host (=localhost) bda://username:password@/deviceurl/set?....
# no auto and no host bda:///deviceurl/set?...

####################### IMPORTS #########################
from builtins import str
from builtins import object
import ifaddr
from fcntl import ioctl
from struct import pack
from hashlib import sha256

#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : bdarui                                        #
#########################################################
class bdauri(object):
    prefix = "bda://"
    secret_key = "@%^&123_bdasocket_$%#!@"

    @classmethod
    def BuildURI(cls, deviceurl, data="", username="", password=""):
        uri = cls.prefix

        if username:
            uri += username

        if password:
            uri += ":" + cls._HashPass(password)

        if username or password:
            uri += "@"

        if deviceurl:
            uri += deviceurl

        if data:
            uri += data

        return uri

    @classmethod
    def BuildURL(cls, address, purl):
        if not address or not purl:
            return None

        url = address.strip().translate((None," :/@()[]<>"))
        if purl[0] != "/":
            url += "/"
        url += purl.strip().translate((None," :@()[]<>"))
        if purl[-1] != "/":
            url += "/"

        return url

    @classmethod 
    def IsUri(cls, uri):    
        pos = uri.find(cls.prefix)
        return (pos==0)

    @classmethod 
    def TestAuth(cls, uri, username="", password=""):
        AuthOk = False
        pos = uri.find("@")
        if cls.IsUri(uri):
            if pos >= len(cls.prefix):
                urisub = uri[len(cls.prefix):pos]
                pos = urisub.find(":")
                if pos >= 0:
                    extusr = urisub[0:pos]
                    extpwd = urisub[pos+1:]
                else:
                    extusr = urisub
                    extpwd = ""
                if (extusr.lower()==username.lower()) and (extpwd == cls._HashPass(password)):
                    AuthOk = True
            elif not username and not password and pos < 0:
                AuthOk = True
        return AuthOk

    @classmethod 
    def GetDeviceUrl(cls, uri):
        url = ""
        if cls.IsUri(uri):
            urisub = uri[len(cls.prefix):]
            pos = urisub.find("@")
            
            urisub = urisub[pos+1:]
            pos = urisub.rfind("/")
            if pos >= 0:
                url = urisub[0:pos+1]
            else:
                url = urisub + "/"

        return url

    @classmethod
    def PrettyDeviceUrl(cls, url):
        purl = ""
        if url:
            pos = url.find("/")
            if pos < 0:
                purl = "/"
            purl += url
            if url[-1] != "/":
                purl += "/" 

        return purl

    @classmethod
    def TestDeviceUrl(cls, uri, host, purl):
        UrlOk = False
        url = cls.GetDeviceUrl(uri)
        if url:
            turl = cls.BuildURL(host, purl)
            UrlOk = (url.lower() == turl.lower())
        return UrlOk

    @classmethod
    def IsTrusted(cls, uri, trusted):
        TrustedOk = False
        url = ""
        purl = cls.GetDeviceUrl(uri).split("/")
        if len(purl)>1:
            url = purl[1]
        if url:
            for turl in trusted:
                if (url.lower() == turl.lower()):
                    TrustedOk = True
                    break
        return TrustedOk

    @classmethod 
    def GetData(cls, uri):
        data = ""
        if cls.IsUri(uri):
            urisub = uri[len(cls.prefix):]
            pos = urisub.find("?")
            if pos >= 0:
                pos = urisub.rfind("/")
                if pos >= 0:
                    data = urisub[pos+1:]
        return data

    @classmethod
    def BuildData(cls, tag="", value=None):
        data = ""
        if tag:
            if value != None:
                data = "set?tag=" + tag + "&value=" + str(value)
            else:
                data = "get?tag=" + tag

        return data

    @classmethod
    def BuildInfoData(cls, tag=""):
        return "getinfo?tag=" + tag

    @classmethod
    def BuildAllData(cls, tag=""):
        return "getall?tag=" + tag

    @classmethod
    def ParseData(cls, data):
        tag = ""
        value = None
        request = ""
        pos = data.find("?")
        if pos >= 0:
            request = data[0:pos]
        pos = data.find("set")
        if pos == 0:
            pos = data.find("&value=")
            if pos >= 0:
                tagdata = data[0:pos]
                value = cls._toType(data[pos+len("&value="):])
                pos = tagdata.find("tag=")
                if pos >= 0:
                    tag = tagdata[pos+len("tag="):]
        else:
            pos = data.find("tag=")
            if pos >= 0:
                tag = data[pos+len("tag="):]
        return tag, value, request

    @classmethod
    def get_ip_address(cls, ifname):
        ip = None
        adapters = ifaddr.get_adapters()
        for adapter in adapters:
            if (adapter.name == ifname):
                ip = adapter.ips[0].ip
        return ip

    @classmethod
    def find_ip_address(cls):
        ip=None
        try:
            ip=cls.get_ip_address('eth0')
            if not ip:
                ip=cls.get_ip_address('wlan0')
                if not ip:
                    ip=cls.get_ip_address('lo')
        except:
            pass
        return ip

    @classmethod
    def _HashPass(cls, password):
        if password:
            salted_password = password + cls.secret_key
            return sha256(salted_password).hexdigest()
        else:
            return password

    @classmethod
    def _toType(cls, value):
        ivalue = None
        try:
            ivalue = int(value)
        except ValueError:
            try:
                ivalue = float(value)
            except ValueError:
                if value.lower()=="true":
                    ivalue = True
                elif value.lower()=="false":
                    ivalue = False
                else:
                    ivalue = value
        return ivalue
