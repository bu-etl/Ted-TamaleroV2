#############################################################################
# zlib License
#
# (C) 2023 Cristóvão Beirão da Cruz e Silva <cbeiraod@cern.ch>
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
from pathlib import Path
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
    _multimeters = {}
    _channels = {}

    _rt = None

    def __init__(
            self,
            outdir: Path,
            interval: int,
            baudrate: int = 9600,
                 ):
        self._rm = pyvisa.ResourceManager()
        self._interval = interval
        self._outdir = outdir
        self._baudrate = baudrate

        if self._interval < 3:
            self._interval = 3

    def add_instrument(self, name: str, manufacturer: str, model: str, serial: str, config: dict[str, str] = {}):
        self._multimeters[name] = {
            "type": "regular",
            "manufacturer": manufacturer,
            "model": model,
            "serial": serial,
            "config": config,
            "resource": None,
            "handle": None,
        }

    def find_devices(self):
        resources = self._rm.list_resources()

        for resource in resources:
            if 'ASRL/dev/ttyS' in resource.split('::')[0]:
                continue
            if 'ASRL/dev/ttyUSB' in resource.split('::')[0]:
                continue
            if 'ASRL/dev/ttyACM' in resource.split('::')[0]:
               continue
            with self._rm.open_resource(resource) as instrument:
                try:
                    instrument.timeout = 2000
                    idn: str = instrument.query('*IDN?')
                    print(idn)
                    # idn format: <company name>, <model number>, <serial number>, <firmware revision>
                    idn_info = idn.split(",")
                    idn_info = [inf.strip() for inf in idn_info]

                    for supply in self._multimeters:
                        if idn_info[0] == self._multimeters[supply]["manufacturer"] and idn_info[1] == self._multimeters[supply]["model"] and idn_info[2] == self._multimeters[supply]["serial"]:
                            self._multimeters[supply]["resource"] = resource
                            break
                except:
                    print(f"Could not connect to resource: {resource}")
                    print("  Perhaps the device is not VISA compatible")
                    continue

        for supply in self._multimeters:
            if self._multimeters[supply]["resource"] is None:
                raise RuntimeError(f"Unable to find the power supply for {supply}")

        # This loop separate from above because of the lock
        for supply in self._multimeters:
            supply_model = self._multimeters[supply]["model"]
            self._multimeters[supply]["handle"] = self._rm.open_resource(self._multimeters[supply]["resource"])

            self._multimeters[supply]["handle"].write("*rst; status:preset; *cls")

        #     for channel in self._channels[supply]:
        #         if supply_model == "PL303QMD-P":
        #             get_ch_state = f'OP{channel}?'  # For CERN Type of Power supply
        #         else:
        #             raise RuntimeError("Unknown power supply model for checking channel status")
        #         state: str = self._power_supplies[supply]["handle"].query(get_ch_state)
        #         #state = state.strip()
        #         if state == "0":
        #             self._channels[supply][channel]['on'] = False
        #         elif state == "1":
        #             self._channels[supply][channel]['on'] = True
        #         else:
        #             raise RuntimeError(f"An impossible state was found for {supply} channel {channel}: \"{state}\"")


    def start_log(self):
        time.sleep(0.5)
        self._rt = RepeatedTimer(self._interval, self.log_measurement)
        self.log_action("Power", "Logging", "Start")

    def stop_log(self):
        if self._rt is not None:
            self._rt.stop()
            self._rt = None
            self.log_action("Power", "Logging", "Stop")

    def release_devices(self):
        for supply in self._multimeters:
            supply_model = self._multimeters[supply]["model"]
            if supply_model == "MODEL 2000":
                self._multimeters[supply]["handle"].query("status:measurement?")
                self._multimeters[supply]["handle"].write("trace:clear; feed:control next")
            else:
                raise RuntimeError("Unknown Multimeter type for releasing the Multimeter")

    def log_action(self, action_system: str, action_type: str, action_message: str):
        log_action_v2(self._outdir, action_system, action_type, action_message)

    def log_measurement(self):
        measurement = self.do_measurement()

        df = pandas.DataFrame(measurement)

        outfile = self._outdir / 'vol_monitoring.sqlite'
        with sqlite3.connect(outfile) as sqlconn:
            df.to_sql('vol_monitoring', sqlconn, if_exists='append', index=False)

    def do_measurement(self):
        measurement = {
            'timestamp': [],
            'voltage': [],
            'Instrument': [],
        }

        for supply in self._multimeters:
            supply_model = self._multimeters[supply]["model"]
            if supply_model == "MODEL 2000":
                number_of_readings = 2
                interval_in_ms = 500
                # program the enable register 512: Set bit B9, sre: service request enable 1: Set MSB bit (Bit 0)
                self._multimeters[supply]["handle"].write("status:measurement:enable 512; *sre 1") 

                # This command specifies the sample count.
                # The sample count defines how many times operation loops around in the trigger model to perform a device action.
                self._multimeters[supply]["handle"].write("sample:count %d" % number_of_readings) 

                # Select bus trigger as event
                self._multimeters[supply]["handle"].write("trigger:source bus") 
                self._multimeters[supply]["handle"].write("trigger:delay %f" % (interval_in_ms / 1000.0))
                self._multimeters[supply]["handle"].write("trace:points %d" % number_of_readings)
                self._multimeters[supply]["handle"].write("trace:feed sense1; feed:control next")

                self._multimeters[supply]["handle"].write("initiate")
                self._multimeters[supply]["handle"].assert_trigger()

                voltages = self._multimeters[supply]["handle"].query_ascii_values("trace:data?")
                avg = sum(voltages) / len(voltages)
            else:
                raise RuntimeError("Unknown Multimeter type for releasing the Multimeter")
            time = pandas.Timestamp.now().isoformat(sep=' ', timespec='seconds')

            measurement["timestamp"] += [time]
            measurement["voltage"] += [avg]
            measurement["Instrument"] += [supply]

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

    args = parser.parse_args()

    if args.list:
        rm = pyvisa.ResourceManager()
        resource_list = rm.list_resources()

        print(resource_list)

        for resource in resource_list:
            if 'ASRL/dev/ttyS' in resource.split('::')[0]:
                continue
            if 'ASRL/dev/ttyUSB' in resource.split('::')[0]:
                continue
            if 'ASRL/dev/ttyACM' in resource.split('::')[0]:
               continue

            with rm.open_resource(resource) as instrument:
                try:
                    # TODO: Need a more intelligent way in order to not force all instruments to have the same requirements
                    instrument.timeout = 2000
                    idn: str = instrument.query('*IDN?')
                    print(idn)
                except:
                    continue
    else:
        device_meas = DeviceMeasurements(
                                        outdir = Path(args.output_directory),
                                        interval = args.measurement_interval,
                                         )

        # TODO: Parse instruments and channels from a config file so that the code does not change from setup to setup, there would be a config file for each setup
        device_meas.add_instrument("VTemp", "KEITHLEY INSTRUMENTS INC.", "MODEL 2000", "4059170") # ADDR 6
        device_meas.add_instrument("VRef", "KEITHLEY INSTRUMENTS INC.", "MODEL 2000", "1069750") # ADDR 16

        device_meas.find_devices()

        def signal_handler(sig, frame):
            print("Exiting gracefully")

            device_meas.stop_log()
            device_meas.release_devices()

            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        device_meas.start_log()

        signal.pause()

        device_meas.release_devices()
