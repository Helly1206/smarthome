# -*- coding: utf-8 -*-
#########################################################
# SERVICE : Apache2Config.py                            #
#           Python configure apache2 for smarthome      #
#           I. Helwegen 2019                            #
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
#########################################################

####################### GLOBALS #########################
VERSION="1.10"
XML_FILENAME = "smarthome.xml"
availablepath = "/etc/apache2/sites-available"
enabledpath = "/etc/apache2/sites-enabled"

#########################################################
# Class : Apache2Config                                 #
#########################################################
class Apache2Config(object):
    def __init__(self):
        self.ports=[]
        self.procs=[]

    def __del__(self):
        pass

    def run(self, argv):
        quick = False
        print("SmartHome webhook Apache2 configuration")
        try:
            opts, args = getopt(argv,"hq",["help","quick"])
        except GetoptError:
            print("Version: " + VERSION + "AH")
            print(" ")
            print("Enter 'Apache2Config -h' for help")
            exit(2)
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print("Version: " + VERSION + "AH")
                print(" ")
                print("Usage:")
                print("         Apache2Config <args>")
                print("         -h, --help: this help file")
                print("         -q, --quick: quick check for changes and if none, only restart")
                print("                      (no check for Prerequisites)")
                exit()
            elif opt in ("-q", "--quick"):
                quick = True

        self.IsRoot()
        if not quick:
            print("Testing Apache2 installation ...")
            self.PrereqInstalled()

        sites=self.GetAllSites()
        xmlsites=self.GetSiteFromXML()

        # Delete named sites with wrong port only
        # Delete content from content sites if port changes
        # Deleting old sites
        for site in sites:

            keep = False
            for xmlsite in xmlsites:
                if site[1] == xmlsite[1]:
                    keep = True

            if keep:
                if not quick:
                    print("Keeping site %s on port %d as it is still in %s"%(site[0], site[1], XML_FILENAME))
            else:
                sitename = site[0].split(".")[0]
                # Named site: delete
                if site[3]:
                    print("Deleting site %s on port %d"%(site[0], site[1]))
                    if site[2]:
                        self.A2DisSite(sitename)
                    self.RemovePort(site[1])
                    self.RemoveSite(site[0])
                else: # Content site: delete content from site
                    print("Deleting content from site %s on port %d"%(site[0], site[1]))
                    if self.DeleteContent(site[0]):
                        print("Site %s on port %d is empty, so delete it"%(site[0], site[1]))
                        if site[2]:
                            self.A2DisSite(sitename)
                        self.RemovePort(site[1])
                        self.RemoveSite(site[0])

        # If named site is disabled, enable
        # if content site is disabled, enable
        # if content site is enabled, then add to content site, check for prefix
        # Adding new sites
        sites=self.GetAllSites(True)
        for xmlsite in xmlsites:
            keep = False
            enabled = False
            named = False
            sitename = "SmartHome_%d.conf"%xmlsite[1]
            sitename2 = sitename.split(".")[0]
            for site in sites:
                if site[1] == xmlsite[1]:
                    if keep:
                        if not enabled and site[2]: # if new one is enabled, use this one
                            name = site[0]
                            enabled = site[2]
                            named = site[3]
                    else:
                        name = site[0]
                        enabled = site[2]
                        named = site[3]
                        keep = True

            if keep:
                if not quick:
                    print("Updating site %s on port %d"%(name, xmlsite[1]))
            else:
                named = True
                print("Adding site %s on port %d"%(sitename, xmlsite[1]))

            email = xmlsite[5]
            server = xmlsite[6]

            if not quick:
                if xmlsite[5] == "":
                    email = self.EmailInput()

                if xmlsite[6] == "":
                    server = self.ServerInput()

            content = ""
            prefix=self.GetPrefix()

            try:
                lctime = os.environ['LC_TIME']
            except:
                lctime = 'C'

            if (xmlsite[2]): # https
                content = self.GenConfHttps(named, xmlsite[1], email, server, lctime, xmlsite[3], xmlsite[4], prefix)
            else: #http
                content = self.GenConfHttp(named, xmlsite[1], email, server, lctime, prefix)

            if not keep: # add new site, always named
                self.AddSite(sitename, content)
                self.AddPort(xmlsite[1])
            elif not quick:
                if named:
                    other, rootpos = self.GetOtherContent(sitename)
                    if (other > 0):
                        if (xmlsite[2]): # https
                            content = self.GenConfHttps(False, xmlsite[1], email, server, lctime, xmlsite[3], xmlsite[4], prefix)
                        else: #http
                            content = self.GenConfHttp(False, xmlsite[1], email, server, lctime, prefix)
                        self.AddContent(name, content)
                    else:
                        self.AddSite(sitename,content)
                        self.AddPort(xmlsite[1])
                else:
                    # add content (prefix don't care)
                    self.AddContent(name, content)
            else: # quick and keep
                if named:
                    other, rootpos = self.GetOtherContent(sitename)
                    if (other > 0):
                        if (xmlsite[2]): # https
                            content = self.GenConfHttps(False, xmlsite[1], email, server, lctime, xmlsite[3], xmlsite[4], prefix)
                        else: #http
                            content = self.GenConfHttp(False, xmlsite[1], email, server, lctime, prefix)
                        rdcontent = self.GetContent(name)
                        if (rdcontent != content):
                            print("Content %s on port %d changed, update site"%(site[0], site[1]))
                            #check added content and maybe replace (prefix don't care)
                            self.AddContent(name, content)
                    else:
                        rdcontent = self.ReadSite(sitename)
                        if (rdcontent != content):
                            print("Site %s on port %d changed, update site"%(site[0], site[1]))
                            self.AddSite(sitename,content)
                            self.AddPort(xmlsite[1])
                else:
                    rdcontent = self.GetContent(name)
                    if (rdcontent != content):
                        print("Content %s on port %d changed, update site"%(site[0], site[1]))
                        #check added content and maybe replace (prefix don't care)
                        self.AddContent(name, content)

            if not enabled:
                self.A2EnSite(sitename2)

        print("Restarting Apache2 ...")
        self.A2Restart()
        print("Ready")
        exit()

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

    def IsRoot(self):
        if not os.geteuid() == 0:
            sys.exit("Apache2Config must be run as root")

    def PrereqInstalled(self):
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
            sys.stdout.write("Please enter E-mail address <%s>:"%email)

            try:
                line = sys.stdin.readline().strip()
            except KeyboardInterrupt:
                exit("Interrupted")

            if line != "":
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
            sys.stdout.write("Please enter server name <%s>:"%server)

            try:
                line = sys.stdin.readline().strip()
            except KeyboardInterrupt:
                exit("Interrupted")

            if line != "":
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
        sitepath = os.path.join(availablepath, site)
        if os.path.isfile(sitepath):
            os.remove(sitepath)

    def AddSite(self, site, content):
        sitepath = os.path.join(availablepath, site)

        with open(sitepath, "w") as f:
            f.write(content)

    def ReadSite(self, site):
        content = ""
        sitepath = os.path.join(availablepath, site)

        with open(sitepath, "r") as f:
            content = f.read()

        return content

    def AddPort(self, port):
        etcpath = "/etc/apache2/"
        conffile = "ports.conf"
        confpath = os.path.join(etcpath,conffile)
        if not os.path.isfile(confpath):
            exit("Configuration file '%s' does not exist, check apache installation"%confpath)

        with open(confpath, 'r') as f:
            content = f.read()

        if not self.FindPort(content, port):
            if (not content[-1:] == "\n"):
                content +="\n"
            content += "Listen %d\n"%port

            with open(confpath, "w") as f:
                f.write(content)

        return

    def RemovePort(self, port):
        # if not 80 or 443
        etcpath = "/etc/apache2/"
        conffile = "ports.conf"
        confpath = os.path.join(etcpath,conffile)
        if not os.path.isfile(confpath):
            exit("Configuration file '%s' does not exist, check apache installation"%confpath)

        if (port == 80) or (port == 443):
            print("Notice: system port %d not removed from apache2 config"%port)
            return

        with open(confpath, 'r') as f:
            content = f.read()

        if self.FindPort(content, port):
            content2 = ""
            last = False
            for line in content.split("\n"):
                if (line.strip() != "Listen %d"%port):
                    content2 += line + "\n"
                    last = True
                else:
                    last = False

            if last:
                content2 = content2[:-1]

            with open(confpath, "w") as f:
                f.write(content2)

        return

    def FindPort(self, content, port):
        Found = False

        for line in content.split("\n"):
            if (line.strip() == "Listen %d"%port):
                Found = True

        return Found

    def GetAllSites(self, all = False):
        sites = []
        if not os.path.isdir(availablepath):
            exit("Apache2 folder '%s' does not exist, check apache installation"%availablepath)
        # First find sites in name domain
        name = "SmartHome_"
        files = os.listdir(availablepath)
        for file in files:
            if (file.find(name)==0) and (file.find(".conf")>0):
                try:
                    portend=file.find(".conf")
                    port=int(file[len(name):portend])
                except:
                    port=0
                if os.path.isfile(os.path.join(enabledpath,file)):
                    enabled=True
                else:
                    enabled=False
                #pport = self.getConfFileDetails(file, sites, availablepath)
                #if (pport == port):
                sites.append((file, port, enabled, True))

        for site in sites:
            files.remove(site[0])

        # Then find sites in other domains
        for file in files:
            if (file.find(".conf")>0):
                port = self.getConfFileDetails(file, sites, availablepath, all)
                if os.path.isfile(os.path.join(enabledpath,file)):
                    enabled=True
                else:
                    enabled=False
                if (port > 0):
                    sites.append((file, port, enabled, False))
        return sites

    def getConfFileDetails(self, file, sites, path, all):
        AlreadyDone = False
        port = 0
        for site in sites:
            if file == site[0]:
                AlreadyDone = True
                break
        if not AlreadyDone:
            # First find port
            lstr, l, p = self.findInFile(os.path.join(path,file), "<VirtualHost")
            if (p>=0):
                p2 = lstr[p:].find(":")
                if (p2>=0):
                    p3 = lstr[p:].find(">")
                    port = int(lstr[p+p2+1:p+p3])
                    if not all:
                        lstr, l2, p = self.findInFile(os.path.join(path,file), "/var/www/smarthome/gsh.wsgi", l)
                        if (p<0):
                            port = 0

            # Find all hosts (aliases) later

        return port

    def findInFile(self, file, text, linestart=-1):
        line = 0
        pos = -1
        linestr = ""
        with open(file) as dataf:
            for l in dataf:
                if line > linestart:
                    pos = l.find(text)
                    if pos>=0:
                        p2 = l.find("#")
                        if (p2<0) or (p2>pos):
                            linestr = l
                            break
                        else:
                            pos = -1
                line += 1
        if pos<0:
            line = 0
        return linestr, line, pos

    def DeleteContent(self, file):
        lb, le = self.GetLines(file)
        #Do delete
        content = self.ReadSite(file)
        l = 0
        newcontent = ""
        for line in content.split("\n"):
            if (l<lb) or (l>le):
                newcontent = newcontent + line + "\n"
            l += 1

        self.AddSite(file, newcontent)

        lstr, l2, p = self.findInFile(os.path.join(availablepath,file), "WSGIDaemonProcess", 0)
        return (p<0)

    def GetLines(self, file, l = 0, All= False):
        p = 0
        lb = -1
        le = -1
        while (p>=0):
            lstr, l2, p = self.findInFile(os.path.join(availablepath,file), "WSGIDaemonProcess", l)
            if (p>=0):
                if not All:
                    lstr, l3, p2 = self.findInFile(os.path.join(availablepath,file), "/var/www/smarthome/gsh.wsgi", l2)
                    if (p2<0): # Incorrect file
                        l = l3+1
                        break
                else:
                    l3 = l2 + 1
                lstr, l4, p3 = self.findInFile(os.path.join(availablepath,file), "</Directory>", l3)
                if (p3>=0):
                    lb = l2
                    lstr, l5, p4 = self.findInFile(os.path.join(availablepath,file), "WSGIDaemonProcess", l4)
                    if (l5 == (l4 + 1)):
                        le = l4
                    else:
                        le = l4 + 1
                    p = -1
                l = l4
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

        while (lb >= 0):
            lb, le = self.GetLines(file, l, True)
            if (lb >= 0):
                lstr, l, p = self.findInFile(os.path.join(availablepath,file), "WSGIScriptAlias", lb)
                if (p>=0):
                    if (lstr.find("/var/www/smarthome/gsh.wsgi")<0):
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
                if line.find("</VirtualHost>"):
                    rootpos = p-1

                p += 1

        if rootpos < 0:
            rootpos = len(oldcontent)

        l=0
        newcontent = ""

        for i in range(0, rootpos):
            newcontent = newcontent + oldcontent[i] + "\n"
        for line in content.split("\n"):
            newcontent = newcontent + line + "\n"
        for i in range(rootpos, len(oldcontent)):
            newcontent = newcontent + oldcontent[i] + "\n"

        self.AddSite(file, newcontent)

    def GetSiteFromXML(self):
        ports=[]
        site = []
        tree = ET.parse(self.GetXML())
        root = tree.getroot()
        for child in root:
            name=child.tag
            if (name.lower() == "webserver"):
                ssl=False

                textdep=child.find('externaldeployment')
                if textdep != None:
                    if (textdep.text.lower() == "false"):
                        print(("Server [%s] not externally deployed, so not added to apache2"%name))
                        continue
                tssl=child.find('ssl')
                if tssl != None:
                    if (tssl.text.lower() == "true"):
                        ssl = True

                cert = ""
                key = ""
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

                port = 5000
                tport=child.find('port')
                if tport != None:
                    port=int(tport.text)
                while port in ports:
                    port +=1
                ports.append(port)

                email = ""
                temail=child.find('serveradmin')
                if temail != None:
                    email=temail.text

                server = ""
                tserver=child.find('servername')
                if tserver != None:
                    server=tserver.text

                site.append((name, port, ssl, cert, key, email, server))
                break

        return site

    def GenConfHttp(self, named, port, admin, server, lctime, prefix):
        if named:
            return "<VirtualHost *:%d>\n" \
            "    ServerAdmin %s\n" \
            "    ServerName %s\n" \
            "    \n" \
            "    SetEnv LC_TIME %s\n" \
            "    \n" \
            "    ErrorLog ${APACHE_LOG_DIR}/error.log\n" \
            "    CustomLog ${APACHE_LOG_DIR}/access.log combined\n" \
            "    \n" \
            "    WSGIDaemonProcess SmartHome_%d user=www-data group=www-data threads=5\n" \
            "    WSGIScriptAlias %s /var/www/smarthome/gsh.wsgi\n" \
            "    WSGIPassAuthorization On\n" \
            "    \n" \
            "    <Directory /var/www/smarthome>\n" \
            "        WSGIProcessGroup SmartHome_%d\n" \
            "        WSGIApplicationGroup %%{GLOBAL}\n" \
            "        Order deny,allow\n" \
            "        Allow from all\n" \
            "    </Directory>\n" \
            "    \n" \
            "</VirtualHost>\n"%(port, admin, server, lctime, port, prefix, port)
        else:
            return "    WSGIDaemonProcess SmartHome_%d user=www-data group=www-data threads=5\n" \
            "    WSGIScriptAlias %s /var/www/smarthome/gsh.wsgi\n" \
            "    WSGIPassAuthorization On\n" \
            "    \n" \
            "    <Directory /var/www/smarthome>\n" \
            "        WSGIProcessGroup SmartHome_%d\n" \
            "        WSGIApplicationGroup %%{GLOBAL}\n" \
            "        Order deny,allow\n" \
            "        Allow from all\n" \
            "    </Directory>\n"%(port, prefix, port)

    def GenConfHttps(self, named, port, admin, server, lctime, cert, key, prefix):
        if named:
            return "<VirtualHost *:%d>\n" \
            "    ServerAdmin %s\n" \
            "    ServerName %s\n" \
            "    \n" \
            "    SetEnv LC_TIME %s\n" \
            "    \n" \
            "    ErrorLog ${APACHE_LOG_DIR}/error.log\n" \
            "    CustomLog ${APACHE_LOG_DIR}/access.log combined\n" \
            "    \n" \
            "    WSGIDaemonProcess SmartHome_%d user=www-data group=www-data threads=5\n" \
            "    WSGIScriptAlias %s /var/www/smarthome/gsh.wsgi\n" \
            "    WSGIPassAuthorization On\n" \
            "    SSLEngine on\n" \
            "    \n" \
            "    SSLCertificateFile  %s\n" \
            "    SSLCertificateKeyFile %s\n" \
            "    \n" \
            "    <Directory /var/www/smarthome>\n" \
            "        WSGIProcessGroup SmartHome_%d\n" \
            "        WSGIApplicationGroup %%{GLOBAL}\n" \
            "        Order deny,allow\n" \
            "        Allow from all\n" \
            "    </Directory>\n" \
            "    \n" \
            "</VirtualHost>\n"%(port, admin, server, lctime, port, prefix, cert, key, port)
        else:
            return "    WSGIDaemonProcess SmartHome_%d user=www-data group=www-data threads=5\n" \
            "    WSGIScriptAlias %s /var/www/smarthome/gsh.wsgi\n" \
            "    WSGIPassAuthorization On\n" \
            "    SSLEngine on\n" \
            "    \n" \
            "    SSLCertificateFile  %s\n" \
            "    SSLCertificateKeyFile %s\n" \
            "    \n" \
            "    <Directory /var/www/smarthome>\n" \
            "        WSGIProcessGroup SmartHome_%d\n" \
            "        WSGIApplicationGroup %%{GLOBAL}\n" \
            "        Order deny,allow\n" \
            "        Allow from all\n" \
            "    </Directory>\n"%(port, prefix, cert, key, port)

    def GetPrefix(self):
        prefix ="/"
        direct ="/webhook"
        try:
            tree = ET.parse(self.GetXML())
            root = tree.getroot()
            for child in root:
                name=child.tag
                if (name.lower() == "webprefix"):
                    prefix = child.text.lower()
                elif (name.lower() == "webhookdirect"):
                    direct = child.text.lower()

            if prefix == None:
                prefix = "/"
            if prefix[:1] != "/":
                prefix = "/" + prefix
            if (len(prefix)>1):
                if (prefix[-1:] == "/"):
                    prefix = prefix[:-1]
                prefix = prefix + direct
            else:
                prefix = direct
        except:
            prefix = direct

        return prefix

#########################################################
if __name__ == "__main__":
    Apache2Config().run(sys.argv[1:])
