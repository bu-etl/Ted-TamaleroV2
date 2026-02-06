#!/usr/bin/env python3
#
# User manual: https://siglentna.com/wp-content/uploads/dlm_uploads/2022/11/SPD3303X_QuickStart_E02A.pdf
#
import socket
import time

green = '\033[92m'
red = '\033[91m'
endc = '\033[0m'

topline = "┏━" + "━"*20 + "━┓"
botline = "┗━" + "━"*20 + "━┛"

class PowerSupply:
    def __init__(self,
                 name,
                 ip,
                 port=5025,
                 timeout=1,
                 ):

        self.name   = name
        self.ip     = ip
        self.port   = port
        self.channels = ['CH1', 'CH2', 'CH3']
        self.mon_channels = ['CH1', 'CH2'] # CH3 not working
        self.timeout = timeout
        self.connect()
        self.id()
        self.status()

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(self.timeout)
        self.s.connect((self.ip, self.port))

    def send(self, cmd, timeout=2, read=False):
        starttime = time.time()
        while True:
            try:
                self.s.sendall(cmd)
                if read:
                    reply = self.s.recv(4096).decode('utf-8').strip()
                    return reply
                else:
                    return True
            except socket.error:
                time.sleep(0.01)
                self.s.close()
                self.connect()
                if time.time() - starttime > timeout:
                    print ("Send command timed out")
                    break
        return None

    def id(self):
        # identical to "echo "*IDN?" | netcat -q 1 {IP} {PORT}"
        res = self.send('*IDN?'.encode('utf-8'), read=True).split(',')
        self.model = res[1]
        self.sn = res[2]
        self.firmware = res[3]
        self.hardware = res[4]

    def status(self):
        res = int(self.send('SYSTEM:STATUS?'.encode('utf-8'), read=True), 16)
        self.CH1 = (res >> 4) & 0x1
        self.CH2 = (res >> 5) & 0x1

    def measure(self, channel='CH1', parameter='VOLTAGE'):
        parameter = parameter.upper()
        channel = channel.upper()
        assert parameter in ['VOLTAGE', 'CURRENT', 'POWER'], f"Don't know what to do with parameter {parameter}"
        assert channel in self.mon_channels, f"Don't know what to do with channel {channel}"

        cmd = f"MEASURE:{parameter}? {channel}".encode("utf-8")
        return float(self.send(cmd, read=True))

    def measure_set(self, channel='CH1', parameter='VOLTAGE'):
        parameter = parameter.upper()
        channel = channel.upper()
        assert parameter in ['VOLTAGE', 'CURRENT', 'POWER'], f"Don't know what to do with parameter {parameter}"
        assert channel in self.mon_channels, f"Don't know what to do with channel {channel}"

        cmd = f"{channel}:{parameter}?".encode("utf-8")
        return float(self.send(cmd, read=True))


    def monitor(self):

        status = self.status()

        res = {}
        for channel in self.mon_channels:
            res[channel] = {}
            res[channel]['Voltage'] = self.measure(channel = channel, parameter = 'VOLTAGE')
            res[channel]['Current'] = self.measure(channel = channel, parameter = 'CURRENT')


        for channel in self.mon_channels:
            if getattr(self, channel) == 1: colored = green
            elif getattr(self, channel) == 0: colored = red
            print(colored + topline + endc)
            print(colored + "┃ {:10}{:10} ┃".format("Channel", channel) + endc)
            print(colored + "┃ {:10}{:10} ┃".format("Voltage", res[channel]["Voltage"]) + endc)
            print(colored + "┃ {:10}{:10} ┃".format("Current", res[channel]["Current"]) + endc)
            print(colored + botline + endc)

    def monitor_set(self):

        status = self.status()

        res = {}
        for channel in self.mon_channels:
            res[channel] = {}
            res[channel]['Voltage'] = self.measure_set(channel = channel, parameter = 'VOLTAGE')
            res[channel]['Current'] = self.measure_set(channel = channel, parameter = 'CURRENT')


        for channel in self.mon_channels:
            if getattr(self, channel) == 1: colored = green
            elif getattr(self, channel) == 0: colored = red
            print(colored + topline + endc)
            print(colored + "┃ {:10}{:10} ┃".format("Channel", channel) + endc)
            print(colored + "┃ {:10}{:10} ┃".format("Voltage", res[channel]["Voltage"]) + endc)
            print(colored + "┃ {:10}{:10} ┃".format("Current", res[channel]["Current"]) + endc)
            print(colored + botline + endc)

    def power_down(self, channel):
        assert channel.upper() in self.channels, "Selected channel does not exist"
        self.send(f"OUTPUT {channel.upper()},OFF".encode('utf-8'))

    def power_up(self, channel):
        assert channel.upper() in self.channels, "Selected channel does not exist"
        self.send(f"OUTPUT {channel.upper()},ON".encode('utf-8'))

    def cycle(self, channel=None, wait=2):
        print(f"Turning OFF channel {channel}.")
        self.power_down(channel)
        time.sleep(wait)
        print(f"Turning ON channel {channel}.")
        self.power_up(channel)

