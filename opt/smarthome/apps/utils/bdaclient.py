# -*- coding: utf-8 -*-
#########################################################
# SERVICE : bdaclient.py                                #
#           Python socket client for devices that       #
#           access the server using BDA access          #
#           I. Helwegen 2018                            #
#########################################################

####################### IMPORTS #########################
from threading import Thread, Event, Lock
from select import select
import queue
import os
import socket, errno
from json import dumps, loads
from time import sleep
from .bdauri import bdauri
import logging

# todo: correct handling of true and false (also for server)
#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : bdaclient                                     #
#########################################################
class bdaclient(Thread):
    def __init__(self, basename, callback, url="/foo", port=60004, server="", host="", username="", password="", usehostname=False):
        self.logger = logging.getLogger('{}.bdaclient'.format(basename))
        self.callback = callback
        self.deviceurl = url
        self.username = username
        self.password = password
        self.server = server
        self.host = host
        self.port = int(port)
        self.url = url
        self.server_address = None

        Thread.__init__(self)
        self.term = Event()
        self.term.clear()
        self.mutex = Lock()
        self.recd = Event()
        self.recd.clear()

        self.timeout = 1
        self.bufsize = 1024
        self.connected = False
        self.introduced = False

        self.output = []
        self.send_buf = queue.Queue()
        self.peername = ()
        self.unblockselect = os.pipe()
        self.introfail = False
        self.introcount = 0

    def __del__(self):
        del self.send_buf

        del self.mutex
        del self.term

        if (self.sock):
            self.sock.close()
            self.connected = False

    def terminate(self):
        self.term.set()

    def isConnected(self):
        return self.connected and self.introduced

    def run(self):
        try:
            self.logger.info("running")

            while (not self.term.isSet()):
                if (not self.connected):
                    if self.introfail:
                        if self.introcount > 30:
                            self.introfail = False
                            self.introcount = 0
                        else:
                            self.introcount += 1
                    else:
                        try:
                            if not self.server or not self.host:
                                ip = None
                                while (not self.term.isSet()) and (not ip):
                                    ip = bdauri.find_ip_address()
                                    sleep(self.timeout)
                                if not self.server:
                                    self.server = ip
                                if not self.host:
                                    self.host = ip

                            if not self.term.isSet():
                                self.deviceurl = bdauri.BuildURL(self.host, self.url)
                                self.server_address = (self.server, self.port)

                                # Check communication with Domotion server
                                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                self.sock.connect(self.server_address)
                                self.sock.setblocking(0)
                                self.peername = self.sock.getpeername()
                                self.introduced = False
                                self.connected = True
                                self.logger.info("Connected to %s", self.peername)
                        except:
                            if (self.sock):
                                self.sock.close()
                                self.connected = False
                                self.introduced = False

                if self.connected:
                    self.mutex.acquire()
                    if (not self.send_buf.empty()) and self.introduced:
                        self.output = [self.sock]
                    self.mutex.release()

                    # Wait for at least one of the sockets to be ready for processing
                    try:
                        inputready, outputready, exceptready = select([self.sock, self.unblockselect[0]], self.output, [self.sock], self.timeout)
                    except:
                        continue

                    if not (inputready or outputready or exceptready):
                        continue

                    # Handle inputs
                    for sock in inputready:
                        if sock is self.unblockselect[0]:
                            os.read(self.unblockselect[0], 1)
                        else:
                            data = self._receive(sock)
                            if data:
                                if (not self.introduced):
                                    if not bdauri.TestAuth(data, self.username, self.password) or not bdauri.TestDeviceUrl(data,self.server_address[0],"/Domotion/"):
                                        if (self.sock):
                                            self.sock.close()
                                        self.connected = False
                                        self.logger.error("Error: Incorrect socket introduction")
                                        self.logger.info("Disconnected from %s",self.peername)
                                        self.introfail = True
                                    else:
                                        self.logger.debug('received "%s" from %s', data, self.peername)
                                        self._addtosendbuf(bdauri.BuildURI(self.deviceurl, "", self.username, self.password))
                                        self.introduced = True
                                else:
                                    # A readable client socket has data
                                    if self._execute(data):
                                        self.logger.debug('received "%s" from %s', data, self.peername)
                                    else:
                                        self.logger.error("Invalid data")
                            else:
                                self.logger.info('Disconnected from %s', self.peername)
                                if (self.sock):
                                    self.sock.close()
                                    self.connected = False

                    # Handle outputs
                    for sock in outputready:
                        try:
                            next_msg = self.send_buf.get_nowait()
                        except queue.Empty:
                            self.output = []
                        else:
                            self.logger.debug('sending "%s" to %s', next_msg, self.peername)
                            success = self._send(sock, next_msg)
                            if (not success):
                                self.output = []
                                continue

                    # Handle "exceptional conditions"
                    for sock in exceptready:
                        self.logger.error('Handling exceptional condition for %s', self.peername)
                        self.output = []
                        sock.close()
                        self.connected = False
                        self.logger.info("Disconnected from %s", self.peername)
                else:
                    sleep(1)

            self.logger.info("terminating")
        except Exception as e:
            self.logger.exception(e)

    def _addtosendbuf(self, data):
        self.mutex.acquire()
        if self.send_buf:
            self.send_buf.put(data)
        self.mutex.release()

    def _receive(self, sock):
        buf = b''
        continue_recv = True
        while continue_recv:
            try:
                recd = sock.recv(self.bufsize)
                buf += recd
                continue_recv = len(recd) > 0
            except socket.error as e:
                if e.errno != errno.EWOULDBLOCK:
                    self.logger.exception(e)
                    return None
                continue_recv = False
        return buf.decode("utf-8")

    def _send(self, sock, arg):
        try:
            sock.sendall(bytes(arg,"utf-8"))
            return True
        except:
            return False

    def Send(self, tag, value):
        rtag = None
        rvalue = None
        self.recd.clear()

        self._addtosendbuf(bdauri.BuildURI(self.deviceurl, bdauri.BuildData(tag, value), self.username, self.password))
        os.write(self.unblockselect[1], b'x')

        if self.recd.wait(5):
            self.mutex.acquire()
            recddata = self.recddata
            self.mutex.release()
            if recddata[0] == 'STORED':
                if (recddata[1] == tag):
                    rtag = tag
                    rvalue = value
            elif recddata[0] == 'VALUE':
                if recddata[1] == tag:
                    rtag = tag
                    rvalue = recddata[2]
        else:
            if (self.sock):
                self.sock.close()
                self.connected = False
        return rtag, rvalue

    def SendInfoRequest(self, info, tag):
        recddata = ["ERROR", tag, "NULL"]
        data = None
        self.recd.clear()

        if info:
            data = bdauri.BuildInfoData(tag)
        else:
            data = bdauri.BuildAllData(tag)

        self._addtosendbuf(bdauri.BuildURI(self.deviceurl, data, self.username, self.password))
        os.write(self.unblockselect[1], b'x')

        if self.recd.wait(5):
            self.mutex.acquire()
            recddata = self.recddata
            self.mutex.release()
        else:
            if (self.sock):
                self.sock.close()
                self.connected = False
        return recddata

    def _execute(self, data):
        if bdauri.IsUri(data):
            if not bdauri.TestAuth(data, self.username, self.password):
                return False
            #print "New command from server"
            pdata = bdauri.ParseData(bdauri.GetData(data))
            if pdata[0]:
                tag, value = self.callback(pdata)
                if tag:
                    if pdata[1]: #set
                        self._addtosendbuf(dumps(['STORED', tag, value]))
                    else: #get
                        self._addtosendbuf(dumps(['VALUE', tag, value]))
                else:
                    self._addtosendbuf(dumps(["ERROR", pdata[0], "NULL"]))
        else:
            #print "Response"
            self.mutex.acquire()
            try:
                self.recddata = loads(data)
            except:
                self.recddata = None
            self.mutex.release()
            self.recd.set()

        return True
