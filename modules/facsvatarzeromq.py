"""FACSvatar base classes"""

# Copyright (c) Stef van der Struijk.
# License: GNU Lesser General Public License

import os
import sys
import traceback
import logging
from abc import ABC, abstractmethod
import asyncio
import zmq.asyncio
from zmq.asyncio import Context
import time
import json
import csv


# setup ZeroMQ publisher / subscriber
class FACSvatarZeroMQ(abstractmethod(ABC)):
    """Base class for initializing FACSvatar ZeroMQ sockets"""

    def __init__(self, pub_ip='127.0.0.1', pub_port=None, pub_key='', pub_bind=True,
                 sub_ip='127.0.0.1', sub_port=None, sub_key='', sub_bind=False,
                 deal_ip='127.0.0.1', deal_port=None, deal_key='', deal_topic='', deal_bind=False,
                 deal2_ip='127.0.0.1', deal2_port=None, deal2_key='', deal2_topic='', deal2_bind=False,
                 deal3_ip='127.0.0.1', deal3_port=None, deal3_key='', deal3_topic='', deal3_bind=False,
                 rout_ip='127.0.0.1', rout_port=None, rout_bind=True,
                 **misc):
        """Sets-up a socket bound/connected to an url

        xxx_ip: ip of publisher/subscriber/dealer/router
        xxx_port: port of publisher/subscriber/dealer/router
        xxx_key: key for filtering out messages (leave empty to receive all) (pub/sub only)
        xxx_bind: True for bind (only 1 socket can bind to 1 address) or false for connect (many can connect)
        """

        # get ZeroMQ version
        print("Current libzmq version is %s" % zmq.zmq_version())
        print("Current  pyzmq version is %s" % zmq.pyzmq_version())

        self.pub_socket = None
        self.sub_socket = None

        # set-up publish socket only if a port is given
        if pub_port:
            print("Publisher port is specified")
            #self.pub_socket = self.zeromq_context(pub_ip, pub_port, zmq.PUB, pub_bind)
            # add variable with key
            #self.pub_key = pub_key

            self.pub_socket = FACSvatarSocket(self.zeromq_context(pub_ip, pub_port, zmq.PUB, pub_bind),
                                              pub_key, "pub0.csv")
            print("Publisher socket set-up complete")
        else:
            print("pub_port not specified, not setting-up publisher")

        # set-up subscriber socket only if a port is given
        if sub_port:
            print("Subscriber port is specified")
            # self.sub_socket = self.zeromq_context(sub_ip, sub_port, zmq.SUB, sub_bind)
            self.sub_key = sub_key  # TODO use sub_topic() instead
            # self.sub_socket.setsockopt(zmq.SUBSCRIBE, self.sub_key.encode('ascii'))

            self.sub_socket = FACSvatarSocket(self.zeromq_context(sub_ip, sub_port, zmq.SUB, sub_bind),
                                              sub_key, "sub0.csv")
            self.sub_socket.sub_topic()
            print("Subscriber socket set-up complete")
        else:
            print("sub_port not specified, not setting-up subscriber")

        # set-up dealer socket only if a port is given
        if deal_port:
            print("Dealer port is specified")
            self.deal_socket = self.zeromq_context(deal_ip, deal_port, zmq.DEALER, deal_bind)
            self.deal_socket.setsockopt(zmq.IDENTITY, deal_key.encode('ascii'))
            # add variable with key f
            self.deal_topic = deal_topic
            print("Dealer socket set-up complete")
        else:
            print("deal_port not specified, not setting-up dealer")

        # set-up dealer socket only if a port is given; TODO better solution for multiple same sockets
        if deal2_port:
            print("Dealer port 2 is specified")
            self.deal2_socket = self.zeromq_context(deal2_ip, deal2_port, zmq.DEALER, deal2_bind)
            self.deal2_socket.setsockopt(zmq.IDENTITY, deal2_key.encode('ascii'))
            # add variable with key f
            self.deal2_topic = deal2_topic
            print("Dealer 2 socket set-up complete")
        else:
            print("deal2_port not specified, not setting-up dealer")

        # set-up dealer socket only if a port is given; TODO better solution for multiple same sockets
        if deal3_port:
            print("Dealer port 3 is specified")
            self.deal3_socket = self.zeromq_context(deal3_ip, deal3_port, zmq.DEALER, deal3_bind)
            self.deal3_socket.setsockopt(zmq.IDENTITY, deal3_key.encode('ascii'))
            # add variable with key f
            self.deal3_topic = deal3_topic
            print("Dealer 3 socket set-up complete")
        else:
            print("deal3_port not specified, not setting-up dealer")

        # set-up router socket only if a port is given
        if rout_port:
            print("Router port is specified")
            self.rout_socket = self.zeromq_context(rout_ip, rout_port, zmq.ROUTER, rout_bind)
            print("Router socket set-up complete")
        else:
            print("rout_port not specified, not setting-up router")

        print("ZeroMQ sockets successfully set-up\n")

        # extra named arguments
        self.misc = misc

    def zeromq_context(self, ip, port, socket_type, bind):
        """Returns a bound / connected ZeroMQ socket through tcp with given ip and port

        ip+port: tcp://{ip}:{port}
        socket_type: ZeroMQ socket type; e.g. zmq.PUB / zmq.SUB
        bind: True for bind (only 1 socket can bind to 1 address) or false for connect (many can connect)
        """

        url = "tcp://{}:{}".format(ip, port)
        print("Creating ZeroMQ context on: {}".format(url))
        ctx = Context.instance()
        socket = ctx.socket(socket_type)
        if bind:
            socket.bind(url)
            print("Bind to {} successful".format(url))
        else:
            socket.connect(url)
            print("Connect to {} successful".format(url))

        return socket

    def start(self, async_func_list=None):
        """Starts asynchronously any given async function"""

        # activate publishers / subscribers
        if async_func_list:
            # capture ZeroMQ errors; ZeroMQ using asyncio doesn't print out errors
            # TODO working properly?
            try:
                asyncio.get_event_loop().run_until_complete(asyncio.wait(
                    [func() for func in async_func_list]
                ))
            except Exception as e:
                print("Error with async function")
                # print(e)
                logging.error(traceback.format_exc())
                print()

            finally:
                # TODO disconnect pub/sub
                pass

        else:
            print("No functions given, nothing to start")


# TODO option to enable / disable debugging
class FACSvatarSocket:
    """Simplify sending messages according to FACSvatar format

    Automatically attempts to encode / decode, and data from/to JSON if not done so yet
    `key` should be string or already encoded as 'ascii'
    `data` should be a dict, JSON formatted string or already encoded as 'utf8'
    Access ZeroMQ socket functionality through `FACSvatarSocket.socket.xxx` (e.g. `.setsockopt()`
    """

    def __init__(self, socket, key='', csv_filename="test0.csv"):
        self.socket = socket
        self.key = key.encode('ascii')
        # time previous message send or useful for start-up time before first message
        self.pub_timestamp_old = self.time_now()
        self.sub_time_received = 0
        self.frame_count = -1

        csv_filename = "timestamps_" + csv_filename

        # increase file name number if file exist
        print("Write timestamps to: {}".format(csv_filename))
        while os.path.exists(csv_filename):
            csv_filename = csv_filename[:-5] + str(int(csv_filename[-5]) + 1) + csv_filename[-4:]

        with open(csv_filename, 'a') as file:
            writer = csv.writer(file, delimiter=',')
            writer.writerow(["msg", "time_prev", "time_now"])

        self.csv_filename = csv_filename

    async def pub(self, data, key=None):
        """ Publish data async

        :param data: dict, JSON formatted string or bytes encoded as 'utf-8'
        :param key: string or bytes encoded as 'ascii'; send specified key instead of default
        :return:
        """

        if not key:
            key = self.key
        else:
            # check if not yet encoded
            if not isinstance(key, bytes):
                key = key.encode('ascii')

        # not b''
        if data:
            # if data not yet bytes
            if not isinstance(data, bytes):
                # if data != JSON:
                if not isinstance(data, str):
                    # change to json string
                    data = json.dumps(data)

                # change from string to bytes
                data = data.encode('utf-8')

            timestamp = self.time_now()
            timestamp_enc = str(timestamp).encode('ascii')

            # print(f"Key type: {type(key)}\nTimestamp type: {type(timestamp)}\nData type: {type(data)}")
            await self.socket.send_multipart([key, timestamp_enc, data])

            print("PUB: Time prev msg:\t\t\t{}".format(self.pub_timestamp_old))
            print("PUB: Time publishing:\t\t\t{}".format(timestamp))
            print("PUB: Difference prev msg nanosec:\t{}".format(timestamp - self.pub_timestamp_old))
            print("PUB: Difference prev msg seconds:\t{}".format((timestamp - self.pub_timestamp_old) / 1000000000))

            # NOT WORKING due to pub and sub not using same instance of this class
            # assume module: receive msg sub --> process --> pub when sub_time_received != 0
            # print(self.sub_time_received)
            # if self.sub_time_received:
            #     print("Module performance diff sub-pub:\t{}".format(timestamp - self.sub_time_received))

            self.write_to_csv([self.pub_timestamp_old, timestamp])

            self.pub_timestamp_old = timestamp

        # send message with no timestamp or data
        else:
            print("PUB: Data finished")
            await self.socket.send_multipart([key, b'', b''])

        print()

    async def sub(self, raw=False):
        """ Wait for subscribed data async

        :param raw: if False, decode (and json.loads()) key, timestamp and data; if True, return as-is (bytes)
        :return: key, timestamp, data
        """

        key, timestamp, data = await self.socket.recv_multipart()

        # not received finish message b''
        if timestamp:
            self.sub_time_received = self.time_now()
            timestamp_decoded = int(timestamp.decode('ascii'))
            time_difference = self.sub_time_received - timestamp_decoded
            print("SUB: Time data published:\t\t{}\nSUB: Time subscribed data received:\t{}\n"
                  "SUB: Difference nanoseconds:\t\t{}\nSUB: Difference seconds:\t\t{}"
                  .format(timestamp_decoded, self.sub_time_received, time_difference, time_difference / 1000000000))

            self.write_to_csv([timestamp_decoded, self.sub_time_received])

            # byte data
            if raw:
                return key, timestamp, data
            # decode data
            else:
                data = data.decode('utf-8')
                # # check not empty byte string b''
                # if data:
                data = json.loads(data)

                return key.decode('ascii'), timestamp_decoded, data

        else:
            # key, '', ''
            return key.decode('ascii'), timestamp.decode('ascii'), data.decode('utf-8')

    # TODO check if single key or list
    def sub_topic(self, key=None, unsub_all=False):
        """ Subscribe to a (new) key

        :param key: set new self.key and subscribe; if None, only subscribe to self.key
        :param unsub_all: if True, unsubscribe all keys
        """

        # TODO multiple sub keys
        if unsub_all:
            self.socket.setsockopt(zmq.UNSUBSCRIBE, self.key)

        if isinstance(key, str):
            self.key = key.encode('ascii')
        elif isinstance(key, bytes):
            self.key = key

        self.socket.setsockopt(zmq.SUBSCRIBE, self.key)

    @staticmethod
    def time_now():
        """Return time as nanoseconds (more precise with >= python 3.7)"""

        # Python 3.7 or newer use nanoseconds
        if (sys.version_info.major == 3 and sys.version_info.minor >= 7) or sys.version_info.major >= 4:
            time_now = time.time_ns()
        else:
            # timestamp = int(time.time() * 1000)
            # timestamp = timestamp.to_bytes((timestamp.bit_length() + 7) // 8, byteorder='big')
            # match nanoseconds
            time_now = int(time.time() * 1000000000)  # time.time()
            #time_now = time.time()

        return time_now

    def write_to_csv(self, data):
        print("Storing time data to csv")

        with open(self.csv_filename, 'a') as file:
            writer = csv.writer(file, delimiter=',')
            # add frame no to beginning of data list
            data.insert(0, self.frame_count)
            # write data to csv
            writer.writerow(data)
            # writer.writerow(self.frame_count, data)

        self.frame_count += 1
