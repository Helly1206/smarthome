# -*- coding: utf-8 -*-
#########################################################
# SERVICE : shdaserver.py                               #
#           Python socket server serving devices that   #
#           access using SHDA access                    #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
from threading import Thread, Event, Lock
from select import select
import socket, errno
import queue
import os
from json import dumps, loads
import logging

#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : shdaserver                                    #
#########################################################
class shdaserver(Thread):
    def __init__(self, basename = "", port = 60024, callback = None, maxclients = 20):
        self.logger = logging.getLogger('{}.shdaserver'.format(basename))
        self.callback = callback

        Thread.__init__(self)
        self.term = Event()
        self.term.clear()
        self.mutexb = Lock()
        self.recd = Event()
        self.recd.clear()

        # Create a TCP/IP socket
        self.timeout = 1
        self.bufsize = 1024
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setblocking(0)
        self.server_address = ('localhost', port)
        self.logger.info('starting up on {}, port {}'.format(self.server_address[0], self.server_address[1]))
        self.server.bind(self.server_address)
        self.server.listen(maxclients)

        self.inputs = [ self.server ]
        self.outputs = [ ]
        self.send_buf = {}
        self.devices = {}
        self.peers = {}
        self.recddata = []
        self.unblockselect = os.pipe()

    def __del__(self):
        self.server.close()
        del self.send_buf

        del self.mutexb
        del self.term
        del self.recd
        self.logger.info("finished")

    def terminate(self):
        self.term.set()

    def run(self):
        try:
            self.logger.info("running")

            while (not self.term.isSet()):
                # Wait for at least one of the sockets to be ready for processing
                try:
                    self.mutexb.acquire()
                    ioutputs = self.outputs
                    self.mutexb.release()
                    inputready, outputready, exceptready = select(self.inputs + [self.unblockselect[0]], ioutputs, self.inputs, self.timeout)
                except:
                    self.mutexb.release()
                    continue

                if not (inputready or outputready or exceptready):
                    continue

                # Handle inputs
                for sock in inputready:
                    if sock is self.server:
                        # A "readable" server socket is ready to accept a connection
                        connection = self._connect(sock)
                        if connection:
                            self.logger.info('New connection from port {}'.format(str(self.peers[connection][1])))
                            self._addtosendbuf(connection, dumps({ "server": "shda" }))
                    elif sock is self.unblockselect[0]:
                        os.read(self.unblockselect[0], 1)
                    else:
                        data = self._load(self._receive(sock))
                        if data:
                            # A readable client socket has data
                            if self._execute(sock, data):
                                if self._addtodevices(sock, data):
                                    self.logger.info("Connected to: {}".format(str(self.devices[sock])))
                        else:
                            self.logger.info('Closing connection from {}'.format(str(self.devices[sock])))
                            if sock in outputready:
                                outputready.remove(sock)
                            self._disconnect(sock)

                # Handle outputs
                for sock in outputready:
                    try:
                        next_msg = self.send_buf[sock].get_nowait()
                    except queue.Empty:
                        self.outputs.remove(sock)
                    else:
                        success = self._send(sock, next_msg)
                        if (not success):
                            self.outputs.remove(sock)
                            continue

                # Handle "exceptional conditions"
                for sock in exceptready:
                    self.logger.error('Handling exceptional condition for {}'.format(str(self.devices[sock])))
                    self._disconnect(sock)
                    del self.send_buf[sock]

            self.logger.info("terminating")
            for sock in inputready:
                self._disconnect(sock)
            for sock in outputready:
                self._disconnect(sock)
            for sock in exceptready:
                self._disconnect(sock)
            self.server.close()
        except Exception as e:
            pass

    def _connect(self, sock):
        try:
            connection, client_address = sock.accept()
            connection.setblocking(0)
        except:
            return None, None
        self.inputs.append(connection)
        self.send_buf[connection] = queue.Queue()
        self.peers[connection] = client_address
        return connection

    def _disconnect(self, sock):
        if sock in self.outputs:
            self.outputs.remove(sock)
        if sock in self.devices:
            self.devices.pop(sock)
        if sock in self.peers:
            self.peers.pop(sock)
        self.inputs.remove(sock)
        sock.close()
        del self.send_buf[sock]

    def _addtosendbuf(self, sock, data):
        self.mutexb.acquire()
        if self.send_buf[sock]:
            self.send_buf[sock].put(data)
            # Add output channel for response
            if sock not in self.outputs:
                self.outputs.append(sock)
        self.mutexb.release()

    def _addtodevices(self, sock, data):
        newsock = False
        if "device" in data:
            newsock = not sock in self.devices
            self.devices[sock] = data["device"]
        return newsock

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

    def Send(self, device, data):
        rdata = None
        self.recd.clear()
        try:
            sock = [k for k, v in list(self.devices.items()) if v == device][0]
        except:
            sock = None
        if sock:
            self._addtosendbuf(sock, dumps(data))
            os.write(self.unblockselect[1], b'x')

            if self.recd.wait(5):
                self.mutexb.acquire()
                rdata = self.recddata
                self.mutexb.release()
            else:
                self._disconnect(sock)
        return rdata

    def _execute(self, sock, data):
        if "command" in data:
            #"New command from client"
            sdata = {}
            if self.callback:
                sdata = self.callback(data)
            self._addtosendbuf(sock, dumps(sdata))
        else:
            #"Response"
            self.mutexb.acquire()
            try:
                self.recddata = data
            except:
                self.recddata = None
            self.mutexb.release()
            self.recd.set()

        return True
