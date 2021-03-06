# -*- coding: utf-8 -*-
#########################################################
# SERVICE : shdaserver.py                               #
#           Python socket server serving devices that   #
#           access using SHDA access                    #
#           I. Helwegen 2021                            #
#########################################################

####################### IMPORTS #########################
from threading import Thread, Event
from select import select
import socket
import queue
import logging
from json import dumps, loads
from struct import pack, unpack

#########################################################

####################### GLOBALS #########################

#########################################################

###################### FUNCTIONS ########################

#########################################################

#########################################################
# Class : webserveraccess                               #
#########################################################
class webserveraccess(Thread):
    def __init__(self, basename = "", port = 60024, callback = None, maxclients = 5):
        self.logger = logging.getLogger('{}.webserveraccess'.format(basename))
        self.callback = callback
        Thread.__init__(self)
        self.term = Event()
        self.term.clear()

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
        self.peers = {}
        self.return_args = {}

    def __del__(self):
        self.server.close()
        del self.return_args
        del self.term
        self.logger.info("finished")

    def terminate(self):
        self.term.set()

    def run(self):
        try:
            self.logger.info("running")

            while (not self.term.isSet()):
                try:
                    inputready, outputready, exceptready = select(self.inputs, self.outputs, self.inputs, self.timeout)
                except:
                    continue

                if not (inputready or outputready or exceptready):
                    continue

                for sock in inputready:
                    if sock is self.server:
                        try:
                            connection, client_address = sock.accept()
                            connection.setblocking(0)
                        except:
                            continue
                        self.logger.info('New connection from port {}'.format(str(client_address[1])))
                        self.inputs.append(connection)
                        self.return_args[connection] = queue.Queue()
                        self.peers[connection] = client_address

                    else:
                        data = self._load(self.receive(sock))
                        if data:
                            argout = self.execute(data)
                            if argout:
                                self.return_args[sock].put(argout)
                                if sock not in self.outputs:
                                    self.outputs.append(sock)
                        else:
                            self.logger.info('Closing connection from {}'.format(str(self.peers[sock][1])))
                            if sock in self.outputs:
                                self.outputs.remove(sock)
                            if sock in outputready:
                                outputready.remove(sock)
                            self.inputs.remove(sock)
                            sock.close()
                            del self.peers[sock]
                            del self.return_args[sock]

                for sock in outputready:
                    try:
                        next_msg = self.return_args[sock].get_nowait()
                    except queue.Empty:
                        self.outputs.remove(sock)
                    else:
                        success = self.send(sock, next_msg)
                        if (not success):
                            self.outputs.remove(sock)
                            continue

                for sock in exceptready:
                    self.logger.error('Handling exceptional condition for {}'.format(str(self.peers[sock][1])))
                    self.inputs.remove(sock)
                    if sock in self.outputs:
                        self.outputs.remove(sock)
                    sock.close()
                    del self.peers[sock]
                    del self.return_args[sock]

            self.logger.info("terminating")
        except Exception as e:
            self.logger.exception(e)

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

    def _load(self, buf):
        data = {}
        try:
            data = loads(buf)
        except:
            pass
        return data

    def send(self, sock, arg):
        try:
            msg = pack('>I', len(arg)) + bytes(arg,"utf-8")
            sock.sendall(msg)
            return True
        except:
            return False

    def execute(self, data):
        sdata = {}
        if self.callback:
            sdata = self.callback(data)

        return dumps(sdata)
