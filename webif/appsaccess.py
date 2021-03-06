# -*- coding: utf-8 -*-
#########################################################
# SERVICE : appsaccess.py                               #
#           Python communication functions for gsh apps #
#           I. Helwegen 2017                            #
#########################################################

####################### IMPORTS #########################
import socket
from json import dumps, loads
from struct import pack, unpack
from threading import Timer
import logging
#########################################################

####################### GLOBALS #########################
TIMEOUT = 300.0
SEND_RETRIES = 3
#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : appsaccess                               #
#########################################################

class appsaccess(object):
    def __init__(self, basename = "", port = 60024):
        self.logger = logging.getLogger('{}.appsaccess'.format(basename))
        self.Timer = None
        self.bufsize = 1024
        self.server_address = ('localhost', port)
        self.connected = False
        self.logger.info('starting up on {}, port {}'.format(self.server_address[0], self.server_address[1]))
        self.FireTimer()
        self.initsock()

    def __del__(self):
        self.terminate()

    def initsock(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVTIMEO, pack('ll', 5, 0))
            self.sock.connect(self.server_address)
            peername = self.sock.getpeername()
            if int(peername[1]) == int(self.server_address[1]):
                self.logger.info("Connected to {}, port {}".format("gsh server", self.server_address[1]))
                self.connected = True
            else:
                self.sock.close()
                self.connected = False
        except:
            if (self.sock):
                self.sock.close()
                self.connected = False
                self.logger.error("Error trying to connect to socket")

        return self.connected

    def closesock(self):
        if (self.sock and self.connected):
            self.sock.close()
            self.connected = False
            self.logger.info("Closing connection to {}, port {}".format("gsh server", self.server_address[1]))

        return self.connected

    def terminate(self):
        self.closesock()

    def Send(self, device, data):
        rdata = None
        success = False
        retry = 0

        self.FireTimer()
        data["device"] = device
        while not success and retry < SEND_RETRIES:
            if not self.connected:
                self.initsock()

            if self.connected:
                success = self.send(self.sock, dumps(data))
                if success:
                    rdata = self._load(self.receive(self.sock))
                    if not rdata:
                        success = False
                        self.closesock()
            retry += 1
        return rdata

    def flush(self, sock):
        retval = True
        try:
            sock.setblocking(0)
            while len(sock.recv(self.bufsize)):
                pass
            sock.setblocking(1)
        except:
            retval = False
        return retval

    def receive(self, sock):
        try:
            raw_msglen = self.receivevalue(sock, 4)
            if not raw_msglen:
                return None
            msglen = unpack('>I', raw_msglen)[0]
            # Read the message data
            return self.receivevalue(sock, msglen).decode("utf-8")
        except:
            return None

    def receivevalue(self, sock, n):
        # Helper function to recv n bytes or return None if EOF is hit
        data = b''
        while len(data) < n:
            if (n- len(data) > self.bufsize):
                packet = sock.recv(self.bufsize)
            else:
                packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def send(self, sock, arg):
        try:
            msg = pack('>I', len(arg)) + bytes(arg,"utf-8")
            sock.sendall(msg)
            return True
        except Exception as e:
            return False

    def _load(self, buf):
        data = {}
        try:
            data = loads(buf)
        except:
            pass
        return data

    def FireTimer(self):
        self.CancelTimer()
        self.Timer = Timer(TIMEOUT, self.OnTimer)
        self.Timer.start()

    def CancelTimer(self):
        if (self.Timer != None):
            self.Timer.cancel()
            del self.Timer
            self.Timer = None

    def OnTimer(self):
        self.CancelTimer()
        self.closesock()
