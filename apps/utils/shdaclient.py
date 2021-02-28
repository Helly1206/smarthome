# -*- coding: utf-8 -*-
#########################################################
# SERVICE : shdaclient.py                               #
#           Python socket client for devices that       #
#           access the server using SHDA access         #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
from threading import Thread, Event, Lock
from select import select
import queue
import os
import socket, errno
from json import dumps, loads
from time import sleep
import logging

#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : shdaclient                                    #
#########################################################
class shdaclient(Thread):
    def __init__(self, basename, device, port=60024, callback = None):
        self.logger = logging.getLogger('{}.shdaclient'.format(basename))
        self.device = device
        self.callback = callback
        self.server_address = ('localhost', int(port))

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
        self.peername = None
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
                            # Check communication with Domotion server
                            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            self.sock.connect(self.server_address)
                            self.sock.setblocking(0)
                            peername = self.sock.getpeername()
                            if int(peername[1]) == int(self.server_address[1]):
                                self.peername = "shdaserver"
                            self.introduced = False
                            self.connected = True
                            self.logger.info("Connected to {}, port {}".format(self.peername, self.server_address[1]))
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
                            data = self._load(self._receive(sock))
                            if data:
                                if (not self.introduced):
                                    iFail = False
                                    if "server" in data:
                                        if data["server"] == "shda":
                                            self._addtosendbuf(dumps({ "device" : self.device }))
                                            self.introduced = True
                                        else:
                                            iFail = True
                                    else:
                                        iFail = True
                                    if iFail:
                                        if (self.sock):
                                            self.sock.close()
                                        self.connected = False
                                        self.logger.error("Error: Incorrect socket introduction")
                                        self.logger.info("Disconnected from {}".format(self.peername))
                                        self.introfail = True
                                else:
                                    # A readable client socket has data
                                    if not self._execute(data):
                                        self.logger.warning("Invalid data")
                            else:
                                self.logger.info('Disconnected from {}'.format(self.peername))
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
                            success = self._send(sock, next_msg)
                            if (not success):
                                self.output = []
                                continue

                    # Handle "exceptional conditions"
                    for sock in exceptready:
                        self.logger.error('Handling exceptional condition for {}'.format(self.peername))
                        self.output = []
                        sock.close()
                        self.connected = False
                        self.logger.info("Disconnected from {}".format(self.peername))
                else:
                    sleep(self.timeout)

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
                    return None
                continue_recv = False
        return buf

    def _load(self, buf):
        data = {}
        try:
            data = loads(buf.decode("utf-8"))
        except:
            pass
        return data

    def _send(self, sock, arg):
        try:
            sock.sendall(bytes(arg,"utf-8"))
            return True
        except:
            return False

    def Send(self, data):
        rdata = None
        self.recd.clear()
        data["device"] = self.device
        self._addtosendbuf(dumps(data))
        os.write(self.unblockselect[1], b'x')

        if self.recd.wait(5):
            self.mutex.acquire()
            rdata = self.recddata
            self.mutex.release()
        else:
            if (self.sock):
                self.sock.close()
                self.connected = False
        return rdata

    def _execute(self, data):
        if "tag" in data:
            #"New command from server"
            sdata = {}
            if self.callback:
                sdata = self.callback(data)
            sdata["device"] = self.device
            self._addtosendbuf(dumps(sdata))
        else:
            #"Response"
            self.mutex.acquire()
            try:
                self.recddata = data
            except:
                self.recddata = None
            self.mutex.release()
            self.recd.set()

        return True
