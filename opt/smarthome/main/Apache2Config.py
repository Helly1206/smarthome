# -*- coding: utf-8 -*-
#########################################################
# SERVICE : Apache2Config.py                            #
#           Python configure apache2 for smarthome,     #
#              Domotion or future apps (with sub-sites) #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
import subprocess
import xml.etree.ElementTree as ET
import sys
import os
import re
from getopt import getopt, GetoptError
from apt import Cache
from urllib.parse import urlparse
try:
    from database.db_read import db_read
    DBinstalled = True
except ImportError:
    DBinstalled = False

#########################################################

####################### GLOBALS #########################
APPNAME = "SmartHome"
LONGAPPNAME = "{} webhook".format(APPNAME)
VERSION = "2.00"
ETCPATH = "/etc/smarthome/"
XMLFILENAME = "smarthome.xml"
AVAILABLEPATH = "/etc/apache2/sites-available"
ENABLEDPATH = "/etc/apache2/sites-enabled"
WEBPATH = "/var/www/smarthome"
WSGIFILE = "{}/gsh.wsgi".format(WEBPATH)
WEBSERVERNAME = "webserver"
PREFIXNAME = "webprefix"
DIRECTNAME = "webhookdirect"
DEBUG = False

#########################################################
# Class : Apache2Config                                 #
#########################################################
class Apache2Config(object):
    def __init__(self):
        self.ports = []

    def __del__(self):
        pass

    def run(self, argv):
        quick = False
        print("{} Apache2 configuration".format(LONGAPPNAME))
        if DEBUG:
            print("DEBUG mode: only file creation, no apache functions executed")
        try:
            opts, args = getopt(argv, "hqc", ["help", "quick", "check"])
        except GetoptError:
            print("Version: {}".format(VERSION))
            print(" ")
            print("Enter 'Apache2Config -h' for help")
            exit(2)
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print("Version: {}".format(VERSION))
                print(" ")
                print("Usage:")
                print("         Apache2Config <args>")
                print("         -h, --help: this help file")
                print("         -q, --quick: quick check for changes and if none, only restart")
                print("                      (no check for Prerequisites)")
                print("         -c, --check: check for external deployment required sites (return > 0)")
                exit()
            elif opt in ("-q", "--quick"):
                quick = True
            elif opt in ("-c", "--check"):
                xmlsites = self.GetSitesFromXML()
                if len(xmlsites) > 0:
                    print("{} sites found requiring external deployment".format(len(xmlsites)))
                    exit(len(xmlsites))
                else:
                    print("No sites found requiring external deployment")
                    exit(0)

        self.IsRoot()
        if not quick:
            print("Testing Apache2 installation ...")
            self.PrereqInstalled()

        sites = self.GetAllSites()
        xmlsites = self.GetSitesFromXML()

        # Delete named sites with wrong port only
        # Delete content from content sites if port changes
        # Deleting old sites
        for site in sites:
            keep = False
            for xmlsite in xmlsites:
                if site["port"] == xmlsite["port"]:
                    keep = True

            if keep:
                if not quick:
                    print("Keeping site {} on port {} as it is still in {}".format(site["file"], site["port"], XMLFILENAME))
            else:
                sitename = site["file"].split(".")[0]
                # Named site: delete
                if site["named"]:
                    print("Deleting site {} on port {}".format(site["file"], site["port"]))
                    if site["enabled"]:
                        self.A2DisSite(sitename)
                    self.RemovePort(site["port"])
                    self.RemoveSite(site["file"])
                else: # Content site: delete content from site
                    print("Deleting content from site {} on port {}".format(site["file"], site["port"]))
                    if self.DeleteContent(site["file"]):
                        print("Site {} on port {} is empty, so delete it".format(site["file"], site["port"]))
                        if site["enabled"]:
                            self.A2DisSite(sitename)
                        self.RemovePort(site["port"])
                        self.RemoveSite(site["file"])

        # If named site is disabled, enable
        # if content site is disabled, enable
        # if content site is enabled, then add to content site, check for prefix
        # Adding new sites
        sites = self.GetAllSites(True)
        for xmlsite in xmlsites:
            conf = xmlsite.copy()
            keep = False
            conf["enabled"] = False
            conf["named"] = False
            sitename_short = "{}_{}".format(APPNAME, xmlsite["port"])
            sitename = "{}.conf".format(sitename_short)

            for site in sites:
                if site["port"] == xmlsite["port"]:
                    if keep:
                        if not conf["enabled"] and site["enabled"]: # if new one is enabled, use this one
                            name = site["file"]
                            conf["enabled"] = site["enabled"]
                            conf["named"] = site["named"]
                    else:
                        name = site["file"]
                        conf["enabled"] = site["enabled"]
                        conf["named"] = site["named"]
                        keep = True

            if keep:
                if not quick:
                    print("Updating site {} on port {}".format(name, xmlsite["port"]))
            else:
                conf["named"] = True
                print("Adding site {} on port {}".format(sitename, xmlsite["port"]))

            if not quick:
                if not conf["email"]:
                    conf["email"] = self.EmailInput()

                if not conf["server"]:
                    conf["server"] = self.ServerInput()

            content = ""
            conf["prefix"] = self.GetPrefix()

            try:
                conf["lctime"] = os.environ['LC_TIME']
            except:
                conf["lctime"] = 'C'

            content = self.GenContent(conf)

            if not keep: # add new site, always named
                self.AddSite(sitename, content)
                self.AddPort(conf["port"])
            elif not quick:
                if conf["named"]:
                    other, rootpos = self.GetOtherContent(sitename)
                    if (other > 0):
                        conf["named"] = False
                        content = self.GenContent(conf)
                        self.AddContent(name, content)
                    else:
                        self.AddSite(sitename, content)
                        self.AddPort(conf["port"])
                else:
                    # add content (prefix don't care)
                    self.AddContent(name, content)
            else: # quick and keep
                if conf["named"]:
                    other, rootpos = self.GetOtherContent(sitename)
                    if (other > 0):
                        conf["named"] = False
                        content = self.GenContent(conf)
                        rdcontent = self.GetContent(name)
                        if (rdcontent != content):
                            print("Content {} on port {} changed, update site".format(name, conf["port"]))
                            #check added content and maybe replace (prefix don't care)
                            self.AddContent(name, content)
                    else:
                        rdcontent = self.ReadSite(sitename)
                        if (rdcontent != content):
                            print("Site {} on port {} changed, update site".format(name, conf["port"]))
                            self.AddSite(sitename, content)
                            self.AddPort(conf["port"])
                else:
                    rdcontent = self.GetContent(name)
                    if (rdcontent != content):
                        print("Content {} on port {} changed, update site".format(name, conf["port"]))
                        #check added content and maybe replace (prefix don't care)
                        self.AddContent(name, content)

            if not conf["enabled"]:
                self.A2EnSite(sitename_short)

        print("Restarting Apache2 ...")
        self.A2Restart()
        print("Ready")
        exit()

    def GetXML(self):
        XMLpath = ""
        # first look in etc
        if os.path.isfile(os.path.join(ETCPATH,XMLFILENAME)):
            XMLpath = os.path.join(ETCPATH,XMLFILENAME)
        else:
            # then look in home folder
            if os.path.isfile(os.path.join(os.path.expanduser('~'),XMLFILENAME)):
                XMLpath = os.path.join(os.path.expanduser('~'),XMLFILENAME)
            else:
                # look in local folder, hope we may write
                if os.path.isfile(os.path.join(".",XMLFILENAME)):
                    if os.access(os.path.join(".",XMLFILENAME), os.W_OK):
                        XMLpath = os.path.join(".",XMLFILENAME)
                    else:
                        self.logger.critical("No write access to XML file, exit")
                        exit(1)
                else:
                    self.logger.critical("No XML file found, exit")
                    exit(1)
        return XMLpath

    def IsRoot(self):
        if not DEBUG and not os.geteuid() == 0:
            sys.exit("Apache2Config must be run as root")

    def PrereqInstalled(self):
        if not DEBUG:
            IsInstalled = False
            cache = Cache()

            for pkg in cache:
                if pkg.name == "apache2":
                    IsInstalled = pkg.is_installed

            if (not IsInstalled):
                sys.exit("Package 'apache2' is not installed, run 'install.sh -a' first or install manually")

            IsInstalled = False
            for pkg in cache:
                if pkg.name == "libapache2-mod-wsgi-py3":
                    IsInstalled = pkg.is_installed

            if (not IsInstalled):
                sys.exit("Package 'libapache2-mod-wsgi-py3' is not installed, run 'install.sh -a' first or install manually")

    def A2Restart(self):
        if self._RunShell("systemctl restart apache2"):
            sys.exit("Error restarting apache2, check logfile")

    def A2EnSite(self, site):
        #apache2ctl -S 2>&1|grep 8090
        if self._RunShell("a2ensite %s"%(site)):
            sys.exit("Error enabling site, check logfile")

    def A2DisSite(self, site):
        if self._RunShell("a2dissite %s"%(site)):
            sys.exit("Error disabling site, check logfile")

    def _RunShell(self, command):
        osstdout = 0
        if not DEBUG:
            with open(os.devnull, 'w')  as devnull:
                try:
                    osstdout = subprocess.check_call(command.split(), stdout=devnull, stderr=devnull)
                except subprocess.CalledProcessError:
                    return 1
        return osstdout

    def EmailInput(self):
        email = "webmaster@localhost"
        valid = None

        while not valid:
            try:
                line = input("Please enter E-mail address <{}>:".format(email)).strip()
            except KeyboardInterrupt:
                exit("Interrupted")

            if line:
                valid=re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", line)
                if not valid:
                    print("Invalid email address, try again")
                else:
                    email = line
            else:
                valid = True

        return email

    def ServerInput(self):
        server = "localhost"
        valid = False

        while not valid:
            try:
                line = input("Please enter server name <{}>:".format(server)).strip()
            except KeyboardInterrupt:
                exit("Interrupted")

            if line:
                try:
                    result = urlparse(line)
                    if not result.scheme:
                        result = urlparse("http://"+line)
                    valid = result.scheme and result.netloc
                except:
                    pass

                if not valid:
                    print("Invalid server name, try again")
                else:
                    server = line
            else:
                valid = True

        return server

    def RemoveSite(self, site):
        sitepath = os.path.join(AVAILABLEPATH, site)
        if os.path.isfile(sitepath):
            os.remove(sitepath)

    def AddSite(self, site, content):
        sitepath = os.path.join(AVAILABLEPATH, site)

        with open(sitepath, "w") as f:
            f.write(content)

    def ReadSite(self, site):
        content = ""
        sitepath = os.path.join(AVAILABLEPATH, site)

        with open(sitepath, "r") as f:
            content = f.read()

        return content

    def AddPort(self, port):
        etcpath = "/etc/apache2/"
        conffile = "ports.conf"
        confpath = os.path.join(etcpath, conffile)
        if not DEBUG:
            if not os.path.isfile(confpath):
                exit("Configuration file '{}' does not exist, check apache installation".format(confpath))

            with open(confpath, 'r') as f:
                content = f.read()

            if not self.ContainsPort(content, port):
                if (not content[-1:] == "\n"):
                    content +="\n"
                content += "Listen {}\n".format(port)

                with open(confpath, "w") as f:
                    f.write(content)

        return

    def RemovePort(self, port):
        # if not 80 or 443
        etcpath = "/etc/apache2/"
        conffile = "ports.conf"
        confpath = os.path.join(etcpath,conffile)
        if not DEBUG:
            if not os.path.isfile(confpath):
                exit("Configuration file '{}' does not exist, check apache installation".format(confpath))

            if (port == 80) or (port == 443):
                print("Notice: system port {} not removed from apache2 config".format(port))
                return

            with open(confpath, 'r') as f:
                content = f.read()

            if self.ContainsPort(content, port):
                content2 = ""
                last = False
                for line in content.split("\n"):
                    if (line.strip() != "Listen {}".format(port)):
                        content2 += line + "\n"
                        last = True
                    else:
                        last = False

                if last:
                    content2 = content2[:-1]

                with open(confpath, "w") as f:
                    f.write(content2)

        return

    def ContainsPort(self, content, port):
        Found = False

        for line in content.split("\n"):
            if (line.strip() == "Listen {}".format(port)):
                Found = True

        return Found

    def GetAllSites(self, all = False):
        sites = []
        if not os.path.isdir(AVAILABLEPATH):
            exit("Apache2 folder '{}' does not exist, check apache installation".format(AVAILABLEPATH))
        # First find sites in name domain
        name = "{}_".format(APPNAME)
        files = os.listdir(AVAILABLEPATH)
        for file in files:
            site = {}
            if (file.find(name) == 0) and (file.find(".conf") > 0):
                site["file"] = file
                try:
                    portend = file.find(".conf")
                    site["port"] = int(file[len(name):portend])
                except:
                    site["port"] = 0
                if os.path.isfile(os.path.join(ENABLEDPATH, file)):
                    site["enabled"] = True
                else:
                    site["enabled"] = False
                site["named"] = True
                sites.append(site)

        for site in sites:
            files.remove(site["file"])

        # Then find sites in other domains
        for file in files:
            site = {}
            if (file.find(".conf") > 0):
                site["file"] = file
                site["port"] = self.getConfFileDetails(file, sites, AVAILABLEPATH, all)
                if os.path.isfile(os.path.join(ENABLEDPATH, file)):
                    site["enabled"] = True
                else:
                    site["enabled"] = False
                site["named"] = False
                if (site["port"] > 0):
                    sites.append(site)
        return sites

    def getConfFileDetails(self, file, sites, path, all):
        AlreadyDone = False
        port = 0
        for site in sites:
            if file == site["file"]:
                AlreadyDone = True
                break
        if not AlreadyDone:
            # First find port
            linestr, line, pos = self.findInFile(os.path.join(path, file), "<VirtualHost")
            if pos >= 0:
                pos2 = linestr[pos:].find(":")
                if pos2 >= 0:
                    pos3 = linestr[pos:].find(">")
                    port = int(linestr[pos+pos2+1:pos+pos3])
                    if not all:
                        linestr, line, pos = self.findInFile(os.path.join(path, file), WSGIFILE, line)
                        if pos < 0:
                            port = 0

        return port

    def findInFile(self, file, text, linestart = -1):
        line = 0
        pos = -1
        linestr = ""
        with open(file) as dataf:
            for l in dataf:
                if line > linestart:
                    pos = l.find(text)
                    if pos >= 0:
                        pos2 = l.find("#")
                        if (pos2 < 0) or (pos2 > pos):
                            linestr = l
                            break
                        else:
                            pos = -1
                line += 1
        if pos < 0:
            line = 0
        return linestr, line, pos

    def DeleteContent(self, file):
        lb, le = self.GetLines(file)
        #Do delete
        content = self.ReadSite(file)
        l = 0
        newcontent = ""
        for line in content.split("\n"):
            if (l < lb) or (l > le):
                newcontent = newcontent + line + "\n"
            l += 1

        self.AddSite(file, newcontent)

        lstr, l2, p = self.findInFile(os.path.join(AVAILABLEPATH,file), "WSGIDaemonProcess", 0)
        return (p < 0)

    def GetLines(self, file, l = 0, All = False):
        p = 0
        lb = -1
        le = -1
        while p >= 0:
            lstr, l2, p = self.findInFile(os.path.join(AVAILABLEPATH, file), "WSGIDaemonProcess", l)
            if (p >= 0):
                if not All:
                    lstr, l3, p2 = self.findInFile(os.path.join(AVAILABLEPATH, file), "WSGIScriptAlias", l2)
                    if p2 < 0: # Incorrect file
                        l = l3 + 1
                        break
                    lstr, l4, p3 = self.findInFile(os.path.join(AVAILABLEPATH, file), WSGIFILE, l2)
                    if p3 < 0: # Incorrect file
                        l = l4 + 1
                        break
                    elif l3 != l4: # incorrect process, continue
                        l = l3 + 1
                        continue
                else:
                    l4 = l2 + 1
                lstr, l5, p4 = self.findInFile(os.path.join(AVAILABLEPATH, file), "</Directory>", l4)
                if p4 >= 0:
                    lb = l2
                    lstr, l6, p5 = self.findInFile(os.path.join(AVAILABLEPATH, file), "WSGIDaemonProcess", l5)
                    if l6 >= (l5 + 1):
                        le = l5
                    else:
                        le = l5 + 1
                    p = -1
                l = l5
        return lb, le

    def GetContent(self, file):
        lb, le = self.GetLines(file)

        content = self.ReadSite(file)
        l = 0
        newcontent = ""
        for line in content.split("\n"):
            if (l>=lb) and (l<le):
                newcontent = newcontent + line + "\n"
            l += 1
        return newcontent

    def GetOtherContent(self, file):
        l = 0
        lb = 0
        other = 0
        rootPos = -1

        while lb >= 0:
            lb, le = self.GetLines(file, l, True)
            if lb >= 0:
                lstr, l, p = self.findInFile(os.path.join(AVAILABLEPATH,file), "WSGIScriptAlias", lb)
                if p >= 0:
                    if lstr.find(WSGIFILE) < 0:
                        other += 1
                    pb = lstr.find("WSGIScriptAlias")+len("WSGIScriptAlias")+1
                    pe = pb + lstr[pb:].find(" /")
                    sitestr = lstr[pb:pe]
                    if sitestr == "/":
                        rootPos = l-1
            l = lb
        return other, rootPos

    def AddContent(self, file, content):
        self.DeleteContent(file)
        other, rootpos = self.GetOtherContent(file)
        oldcontent = self.ReadSite(file).split("\n")
        if rootpos < 0:
            p = 0
            for line in oldcontent:
                if line.find("</VirtualHost>") >= 0:
                    rootpos = p
                p += 1

        if rootpos < 0:
            rootpos = len(oldcontent)

        newcontent = ""

        for i in range(0, rootpos):
            newcontent += oldcontent[i] + "\n"
        for line in content.split("\n"):
            newcontent += line + "\n"
        for i in range(rootpos, len(oldcontent) - 1):
            newcontent += oldcontent[i]
            if i < (len(oldcontent) - 2):
                newcontent += "\n"

        self.AddSite(file, newcontent)

    def GetSitesFromXML(self):
        index = 0
        ports = []
        sites = []
        tree = ET.parse(self.GetXML())
        root = tree.getroot()
        for child in root:
            name = child.tag
            if (not WEBSERVERNAME) or (name.lower() == WEBSERVERNAME):
                if (name.lower() == PREFIXNAME) or (name.lower() == DIRECTNAME):
                    continue
                site = {}
                site["name"] = child.tag
                site["ssl"] = False

                if index > 4:
                    print("Server [{}] not started as maximum of 5 servers obtained".format(name))
                    continue
                else:
                    index += 1

                extdep = child.find('externaldeployment')
                if extdep != None:
                    if (extdep.text.lower() == "false"):
                        print("Server [{}] not externally deployed, so not added to apache2".format(name))
                        continue
                ssl = child.find('ssl')
                if ssl != None:
                    if ssl.text.lower() == "true":
                        site["ssl"] = True

                site["cert"] = ""
                site["key"] = ""
                if site["ssl"]:
                    cert = child.find('certificate')
                    if cert != None:
                        site["cert"] = cert.text
                    else:
                        site["ssl"] = False

                if site["ssl"]:
                    key = child.find('privatekey')
                    if key != None:
                        site["key"] = key.text
                    else:
                        site["ssl"] = False

                site["port"] = 5000
                port = child.find('port')
                if port != None:
                    site["port"] = int(port.text)
                while site["port"] in ports:
                    site["port"] += 1
                ports.append(site["port"])

                site["email"] = ""
                email = child.find('serveradmin')
                if email != None:
                    site["email"] = email.text

                site["server"] = ""
                server = child.find('servername')
                if server != None:
                    site["server"] = server.text

                sites.append(site)

        return sites

    def GenContent(self, conf):
        process = self.GenProcess(conf)

        if conf["named"]:
            return self.GenVirtualHost(conf, process)
        else:
            return process

    def GenVirtualHost(self, conf, process):
        return "<VirtualHost *:{}>\n" \
        "    ServerAdmin {}\n" \
        "    ServerName {}\n" \
        "    \n" \
        "    SetEnv LC_TIME {}\n" \
        "    \n" \
        "    ErrorLog ${{APACHE_LOG_DIR}}/error.log\n" \
        "    CustomLog ${{APACHE_LOG_DIR}}/access.log combined\n" \
        "    \n" \
        "{}" \
        "    \n" \
        "</VirtualHost>\n".format(conf["port"], conf["email"], conf["server"], conf["lctime"], process)

    def GenProcess(self, conf):
        sslcontent = ""
        if conf["ssl"]:
            sslcontent = "    SSLEngine on\n" \
            "    \n" \
            "    SSLCertificateFile {}\n" \
            "    SSLCertificateKeyFile {}\n".format(conf["cert"], conf["key"])

        return "    WSGIDaemonProcess {}_{} user=www-data group=www-data threads=5\n" \
        "    WSGIScriptAlias {} {}\n" \
        "    WSGIPassAuthorization On\n" \
        "{}" \
        "    \n" \
        "    <Directory {}>\n" \
        "        WSGIProcessGroup {}_{}\n" \
        "        WSGIApplicationGroup %{{GLOBAL}}\n" \
        "        Order deny,allow\n" \
        "        Allow from all\n" \
        "    </Directory>\n".format(APPNAME, conf["port"], conf["prefix"], WSGIFILE, sslcontent, WEBPATH, APPNAME, conf["port"])

    def GetPrefix(self):
        prefix = "/"
        direct = "" #"/webhook"
        db = None

        if DBinstalled:
            try:
                db = db_read(self.GetDB())
                prefix = db.GetSetting(PREFIXNAME)
                try:
                    direct = db.GetSetting(DIRECTNAME)
                except:
                    direct = ""
            except:
                prefix = "/"
            del db
        else:
            try:
                tree = ET.parse(self.GetXML())
                root = tree.getroot()
                for child in root:
                    name = child.tag
                    if name.lower() == PREFIXNAME:
                        prefix = child.text
                    elif name.lower() == DIRECTNAME:
                        direct = child.text
            except:
                prefix = "/"

        if prefix == None:
            prefix = "/"
        prefix = prefix.lower()
        if direct == None:
            direct = ""
        direct = direct.lower()
        if prefix[:1] != "/":
            prefix = "/" + prefix
        if len(prefix) > 1:
            if prefix[-1:] == "/":
                prefix = prefix[:-1]
            prefix = prefix + direct
        else:
            if direct:
                prefix = direct
            else:
                prefix = "/"

        return prefix

#########################################################
if __name__ == "__main__":
    Apache2Config().run(sys.argv[1:])
