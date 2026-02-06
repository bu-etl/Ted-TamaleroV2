#############################################################################
# zlib License
#
# (C) 2024 Murtaza Safdari <musafdar@cern.ch>, Cristóvão Beirão da Cruz e Silva <cbeiraod@cern.ch>
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.
#############################################################################

import pyvisa
import time
from threading import Timer
import signal
import sys
import datetime
import pandas
import sqlite3
import yaml
from pathlib import Path
import warnings
from supplyDict import supplyDict
from config import supplyConfig, channelConfig, ignore_list

import os
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
try:
    from log_action import log_action_v2
except:
    from scripts.log_action import log_action_v2

# This class from stackoverflow Q 474528
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

class DeviceMeasurements():
    _power_supplies = {}
    _channels = {}

    _rt = None
    _file_name = "PowerHistory_v2.sqlite"

    def __init__(
            self,
            outdir: Path,
            interval: int,
            config_file: Path,
            baudrate: int = 9600,
            reset_inst: bool = True,
            file_name: str = None,
                 ):
        self._rm = pyvisa.ResourceManager()
        self._interval = interval
        self._outdir = outdir
        self._baudrate = baudrate
        self._config_file = config_file
        if file_name is not None:
            self._file_name = file_name

        if self._interval < 3:
            self._interval = 3

        with open(config_file, 'r') as file:
            config_info = yaml.safe_load(file)

            self.ignore_list = config_info["ignore_list"]

            for key, val in dict(config_info["power_supplies"]).items():
                self.add_instrument(val["resource"], key, val["manufacturer"], val["model"], val["serial"])
                for ckey, cval in dict(val["channels"]).items():
                    self.add_channel(key, cval["channel"], ckey, config=cval)

        self.find_devices(reset_inst = reset_inst)

    def add_instrument(self, resource_str: str, name: str, manufacturer: str, model: str, serial: str, config: dict[str, str] = {}):
        self._power_supplies[name] = {
            "type": "regular",
            "manufacturer": manufacturer,
            "model": model,
            "serial": serial,
            "config": config,
            "resource": resource_str,
            "resource_found": False,
            "handle": None,
        }

    def add_tcp_instrument(self, resource_str: str, name: str, manufacturer: str, model: str, serial: str, config: dict[str, str] = {}):
        self._power_supplies[name] = {
            "type": "tcp",
            "manufacturer": manufacturer,
            "model": model,
            "serial": serial,
            "config": config,
            "resource": resource_str,
            "resource_found": False,
            "handle": None,
        }

    def add_channel(self, name: str, channel: int, alias: str, config: dict[str, str] = {}):
        if name not in self._power_supplies:
            raise RuntimeError(f"A power supply with the name {name} does not exist")

        if name not in self._channels:
            self._channels[name] = {}

        if channel in self._channels[name]:
            raise RuntimeError(f"You are defining the channel {channel} for power supply {name} twice")

        self._channels[name][channel] = {
            "alias": alias,
            "config": config,
            "Vset": None,
            "Ilimit": None,
            "on": False,
        }

    def set_channel_voltage(self, name: str, channel: int, voltage: float):
        self._channels[name][channel]["Vset"] = voltage
        if self._channels[name][channel]["on"]:
            supply_model = self._power_supplies[name]["model"]
            if supplyDict[supply_model]["set_voltage"] and supply_model in supplyDict.keys():
                if("channel" in supplyDict[supply_model]["set_voltage"]):
                    self._power_supplies[name]["handle"].write(supplyDict[supply_model]["set_voltage"].format(channel=channel,voltage=voltage))
                else:
                    self._power_supplies[name]["handle"].write(supplyDict[supply_model]["set_voltage"].format(voltage=voltage))
            else:
                raise RuntimeError("Unknown power supply model for setting voltage")

    def set_channel_current_limit(self, name: str, channel: int, current: float):
        self._channels[name][channel]["Ilimit"] = current
        if self._channels[name][channel]["on"]:
            supply_model = self._power_supplies[name]["model"]
            if supplyDict[supply_model]["set_current"] and supply_model in supplyDict.keys():
                if("channel" in supplyDict[supply_model]["set_current"]):
                    self._power_supplies[name]["handle"].write(supplyDict[supply_model]["set_current"].format(channel=channel,current=current))
                else:
                    self._power_supplies[name]["handle"].write(supplyDict[supply_model]["set_current"].format(current=current))
            else:
                raise RuntimeError("Unknown power supply model for setting current")


    def find_devices(self, reset_inst=True):
        resources = self._rm.list_resources()
        flag = True
        found_supply = False
        for resource in resources:
            flag = True
            found_supply = False
            for ignored in self.ignore_list:
                if ignored in resource:
                    flag = False
                    break
            if(flag):
                with self._rm.open_resource(resource) as instrument:
                    try:
                        instrument.baud_rate = self._baudrate
                        instrument.timeout = 2000
                        # instrument.write_termination = self._write_termination
                        # instrument.read_termination = self._read_termination
                        idn: str = instrument.query('*IDN?')
                        print(idn)
                        # idn format: <company name>, <model number>, <serial number>, <firmware revision>
                        idn_info = idn.split(",")
                        idn_info = [inf.strip() for inf in idn_info]
                        if(idn_info[1] in supplyDict.keys()):
                            instrument.write_termination = supplyDict[idn_info[1]]["write_termination"]
                            instrument.read_termination = supplyDict[idn_info[1]]["read_termination"]
                        for supply in self._power_supplies:
                            if idn_info[0] == self._power_supplies[supply]["manufacturer"] and idn_info[1] == self._power_supplies[supply]["model"] and idn_info[2] == self._power_supplies[supply]["serial"]:
                                if(self._power_supplies[supply]["resource"] and self._power_supplies[supply]["resource"]==resource):
                                    found_supply = True
                                    break
                                elif(self._power_supplies[supply]["resource"] and self._power_supplies[supply]["resource"]!=resource):
                                    pass
                                elif(not self._power_supplies[supply]["resource"]):
                                    self._power_supplies[supply]["resource"] = resource
                                    found_supply = True
                                    break
                        if(found_supply):
                            self._power_supplies[supply]["resource_found"] = True
                    except:
                        print(f"Could not connect to resource: {resource}")
                        print("  Perhaps the device is not VISA compatible, or termination characters are wrong")
                        continue

        for supply in self._power_supplies:
            if not self._power_supplies[supply]["resource_found"]:
                self._power_supplies[supply]["resource"] = None
            if self._power_supplies[supply]["resource"] is None:
                raise RuntimeError(f"Unable to find the power supply for {supply}")

        # This loop separate from above because of the lock
        for supply in self._power_supplies:
            supply_model = self._power_supplies[supply]["model"]
            self._power_supplies[supply]["handle"] = self._rm.open_resource(self._power_supplies[supply]["resource"])
            self._power_supplies[supply]["handle"].baud_rate = self._baudrate
            self._power_supplies[supply]["handle"].timeout = 5000
            self._power_supplies[supply]["handle"].write_termination = supplyDict[supply_model]["write_termination"]
            self._power_supplies[supply]["handle"].read_termination = supplyDict[supply_model]["read_termination"]

            self._power_supplies[supply]["handle"].write("*CLS")
            if(reset_inst):
                # self._power_supplies[supply]["handle"].write("*RST?")
                self._power_supplies[supply]["handle"].write("*RST") # changed for Belgium EDU36311A

            for channel in self._channels[supply]:
                if(supply_model in supplyDict.keys()):
                    if(supplyDict[supply_model]["get_state"]):
                        if("channel" in supplyDict[supply_model]["get_state"]):
                            state: str = self._power_supplies[supply]["handle"].query(supplyDict[supply_model]["get_state"].format(channel=channel))
                        else:
                            state: str = self._power_supplies[supply]["handle"].query(supplyDict[supply_model]["get_state"])
                    else:
                        state: str = ""
                else:
                    raise RuntimeError("Unknown power supply model for checking channel status")
                #state = state.strip()
                if(not state):
                    self._channels[supply][channel]['on'] = True
                elif state in supplyDict[supply_model]["states"]:
                    self._channels[supply][channel]['on'] = supplyDict[supply_model]["states"][state]
                else:
                    raise RuntimeError(f"An impossible state was found for {supply} channel {channel}: \"{state}\"")

            if(supplyDict[supply_model]["set_remote"]):
                if(supplyDict[supply_model]["lock_query"]):
                    self._power_supplies[supply]["handle"].query(supplyDict[supply_model]["set_remote"])  # Lock the device
                else:
                    self._power_supplies[supply]["handle"].write(supplyDict[supply_model]["set_remote"])
            else:
                # print(f"Unknown power supply {supply_model} for locking the power supply, not locking")
                pass
            if("init" in supplyDict[supply_model].keys()) and reset_inst:
                for init_line in supplyDict[supply_model]["init"]:
                    self._power_supplies[supply]["handle"].write(init_line)
            else:
                # print(f"No Init for {supply_model}")
                pass

    def turn_on(self):
        for supply in self._power_supplies:
            supply_model = self._power_supplies[supply]["model"]

            for channel in self._channels[supply]:
                if(supply_model not in supplyDict.keys()):
                    raise RuntimeError("Unknown power supply model for turn_on function")

                ### Temporary solution to control individual channel
                if not self._channels[supply][channel]["config"]["turn_on"]:
                    continue

                self._channels[supply][channel]['on'] = True
                voltage = self._channels[supply][channel]["Vset"]
                if voltage is None:
                    voltage = self._channels[supply][channel]["config"]["Vset"]
                    if voltage is None:
                        voltage = 0
                self.set_channel_voltage(supply, channel, voltage)

                current = self._channels[supply][channel]["Ilimit"]
                if current is None:
                    current = self._channels[supply][channel]["config"]["Ilimit"]
                    if current is None:
                        current = 0.01
                self.set_channel_current_limit(supply, channel, current)

                if "IRange" in self._channels[supply][channel]["config"].keys():
                    if "IRange" in supplyDict[supply_model].keys() and "IRange_states" in supplyDict[supply_model].keys():
                        if self._channels[supply][channel]["config"]["IRange"] in supplyDict[supply_model]["IRange_states"].keys():
                            self._power_supplies[supply]["handle"].write(supplyDict[supply_model]["IRange"].format(channel=channel,state=supplyDict[supply_model]["IRange_states"][self._channels[supply][channel]["config"]["IRange"]]))
                        else: 
                            raise RuntimeError(f'Unknown IRange option: {self._channels[supply][channel]["config"]["IRange"]}')
                    else:
                        raise RuntimeError(f'No IRange options given for {supply_model}, but IRange sent in Channel Config')
                if "Mode" in self._channels[supply][channel]["config"].keys():
                    if "Mode" in supplyDict[supply_model].keys() and "Mode_states" in supplyDict[supply_model].keys():
                        if self._channels[supply][channel]["config"]["Mode"] in supplyDict[supply_model]["Mode_states"].keys():
                            self._power_supplies[supply]["handle"].write(supplyDict[supply_model]["Mode"].format(channel=channel,state=supplyDict[supply_model]["Mode_states"][self._channels[supply][channel]["config"]["Mode"]]))
                        else:
                            raise RuntimeError(f'Unknown Mode option: {self._channels[supply][channel]["config"]["Mode"]}')
                    else:
                        raise RuntimeError(f'No Mode options given for {supply_model}, but Mode sent in Channel Config')

            self._power_supplies[supply]["handle"].write("*CLS")

            for channel in self._channels[supply]:
                self.log_action("Power", "On", f"{supply} {channel}")
                if(supplyDict[supply_model]["power_on"]):
                    if("channel" in supplyDict[supply_model]["power_on"]):
                        self._power_supplies[supply]["handle"].write(supplyDict[supply_model]["power_on"].format(channel=channel))
                    else:
                        self._power_supplies[supply]["handle"].write(supplyDict[supply_model]["power_on"])
                else:
                    raise RuntimeError("Unknown power supply type for turning on the power supply")

    def start_log(self):
        time.sleep(0.5)
        self._rt = RepeatedTimer(self._interval, self.log_measurement)
        self.log_action("Power", "Logging", "Start")

    def stop_log(self):
        if self._rt is not None:
            self._rt.stop()
            self._rt = None
            self.log_action("Power", "Logging", "Stop")

    def turn_off(self):
        for supply in self._power_supplies:
            supply_model = self._power_supplies[supply]["model"]
            for channel in self._channels[supply]:
                if(supply_model not in supplyDict.keys()):
                    raise RuntimeError("Unknown power supply model for turn_off function")

                self.log_action("Power", "Off", f"{supply} {channel}")
                self._channels[supply][channel]['on'] = False
                if(supplyDict[supply_model]["power_off"]):
                    if("channel" in supplyDict[supply_model]["power_off"]):
                        self._power_supplies[supply]["handle"].write(supplyDict[supply_model]["power_off"].format(channel=channel))
                    else:
                        self._power_supplies[supply]["handle"].write(supplyDict[supply_model]["power_off"])
                else:
                    raise RuntimeError("Unknown power supply type for turning off the power supply")

                voltage = 0
                self.set_channel_voltage(supply, channel, voltage)
                current = 0.01
                self.set_channel_current_limit(supply, channel, current)

    def release_devices(self):
        for supply in self._power_supplies:
            supply_model = self._power_supplies[supply]["model"]
            if(supply_model not in supplyDict.keys()):
                raise RuntimeError("Unknown power supply model for release_devices function")
            if(supplyDict[supply_model]["set_local"]):
                if(supplyDict[supply_model]["lock_query"]):
                    self._power_supplies[supply]["handle"].query(supplyDict[supply_model]["set_local"])
                else:
                    self._power_supplies[supply]["handle"].write(supplyDict[supply_model]["set_local"])
            else:
                # print(f"Unknown power supply {supply_model} for unlocking the power supply, skipping unlocking")
                pass

    def log_action(self, action_system: str, action_type: str, action_message: str):
        log_action_v2(self._outdir, action_system, action_type, action_message)
        # data = {
        #    'timestamp': [datetime.datetime.now().isoformat(sep=' ')],
        #    'type': [action_type],
        #    'action': [action_message],
        # }
        # df = pandas.DataFrame(data)
        # outfile = self._outdir / 'PowerHistory_v2.sqlite'
        # with sqlite3.connect(outfile) as sqlconn:
        #    df.to_sql('actions', sqlconn, if_exists='append', index=False)

    def log_measurement(self):
        measurement = self.do_measurement()
        df = pandas.DataFrame(measurement)
        outfile = self._outdir / self._file_name
        with sqlite3.connect(outfile) as sqlconn:
            df.to_sql('power_v2', sqlconn, if_exists='append', index=False)

    def do_measurement(self):
        measurement = {
            'timestamp': [],
            'V': [],
            'I': [],
            'Instrument': [],
            'Channel': [],
            'channel_id': [],
        }

        for supply in self._power_supplies:
            supply_model = self._power_supplies[supply]["model"]
            if(supply_model not in supplyDict.keys()):
                if(not(supplyDict[supply_model["get_voltage"]] and supplyDict[supply_model["get_current"]])):
                    raise RuntimeError("Unknown power supply model for do_measurement function")
            for channel in self._channels[supply]:
                V = self._power_supplies[supply]["handle"].query(supplyDict[supply_model]["get_voltage"].format(channel=channel))
                I = self._power_supplies[supply]["handle"].query(supplyDict[supply_model]["get_current"].format(channel=channel))
                time = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')

                channel_name = self._channels[supply][channel]["alias"]
                if channel_name is None:
                    channel_name = f"Channel{channel}"

                measurement["timestamp"] += [time]
                measurement["V"] += [V]
                measurement["I"] += [I]
                measurement["Instrument"] += [supply]
                measurement["Channel"] += [channel_name]
                measurement["channel_id"] += [channel]

        return measurement

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
                    prog='Read Current',
                    description='Control them!\nBy default, this script will take no action apart from finding and attempting to connect to the configured power supplies. Use the --turn-on --log --turn-off options to control what actions the script takes',
                    #epilog='Text at the bottom of help'
                    )

    parser.add_argument(
        '-l',
        '--list',
        action = 'store_true',
        help = 'List the SCPI resources and then exit',
        dest = 'list',
    )
    parser.add_argument(
        '-r',
        '--baudrate',
        type = int,
        help = 'The baud rate to connect to the instruments. All instruments must have the same baud rate. Default: 9600',
        dest = 'baudrate',
        default = 9600,
    )
    parser.add_argument(
        '-i',
        '--measurement-interval',
        type = int,
        help = 'The interval in seconds between measurements. Default: 5',
        dest = 'measurement_interval',
        default = 5,
    )
    parser.add_argument(
        '-o',
        '--output-directory',
        type = Path,
        help = 'The directory where the log file is saved to. Default: ./',
        dest = 'output_directory',
        default = Path("./"),
    )
    parser.add_argument(
        '-c',
        '--config',
        type = Path,
        help = 'The YAML config file with the devices and device configurations to use',
        required = True,
        dest = 'config_file',
    )
    parser.add_argument(
        '--turn-on',
        action = 'store_true',
        help = 'Turn on the power supplies',
        dest = 'turn_on',
    )
    parser.add_argument(
        '--log',
        action = 'store_true',
        help = 'Log the power supplies\' measurements. The process will not exit on its own, use Ctrl+C to exit',
        dest = 'log',
    )
    parser.add_argument(
        '-f',
        '--file-name',
        type = Path,
        help = 'The file name to save the log into',
        dest = 'file_name',
        default = None,
    )
    parser.add_argument(
        '--turn-off',
        action = 'store_true',
        help = 'Turn off the power supplies',
        dest = 'turn_off',
    )
    parser.add_argument(
        '--no_reset_inst',
        action = 'store_false',
        help = 'Dont issue RST to intrument',
        dest = 'reset_inst',
    )

    args = parser.parse_args()

    if args.list:
        rm = pyvisa.ResourceManager()
        resource_list = rm.list_resources()

        print(resource_list)

        ignore_list = []
        with open(args.config_file, 'r') as file:
            config_info = yaml.safe_load(file)
            ignore_list = config_info["ignore_list"]

        for resource in resource_list:
            print(resource)
            tmp_flag = False
            for ignored in ignore_list:
                if ignored in resource:
                    tmp_flag = True
                    break
            if(tmp_flag): continue
            with rm.open_resource(resource) as instrument:
                try:
                    instrument.baud_rate = args.baudrate
                    instrument.timeout = 2000
                    # instrument.write_termination = write_termination
                    # instrument.read_termination = read_termination
                    idn: str = instrument.query('*IDN?')
                    print(idn)
                except:
                    continue
    else:
        device_meas = DeviceMeasurements(outdir = Path(args.output_directory), interval = args.measurement_interval, baudrate = args.baudrate, config_file = Path(args.config_file),reset_inst = args.reset_inst, file_name = args.file_name)

        if args.turn_on:
            device_meas.turn_on()

        if args.log:
            def signal_handler(sig, frame):
                print("Exiting gracefully")

                device_meas.stop_log()
                if args.turn_off:
                    device_meas.turn_off()
                device_meas.release_devices()

                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)

            device_meas.start_log()

            signal.pause()
        else:
            if args.turn_off:
                device_meas.turn_off()

        device_meas.release_devices()
