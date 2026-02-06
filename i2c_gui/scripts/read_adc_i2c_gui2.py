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

import time
import logging
import signal
import sys
import datetime
import pandas
import sqlite3
from pathlib import Path
from threading import Timer
import i2c_gui2

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

class ADCMeasurements():
    _rt = None

    _adc_channels = {}
    _dac_channels = {}

    _calibration = {}

    def __init__(
            self,
            outdir: Path,
            interval: int,
            port: str,
            vref: int,
            i2c_address: int,
            internal_vref: bool,
                 ):
        self._interval = interval
        self._outdir = outdir
        self._port = port
        self._vref = vref
        self._i2c_address = i2c_address
        self._internal_vref = internal_vref
        if self._internal_vref:
            self._vref = 2.5

        if self._interval < 2:
            self._interval = 2

        self._logger = logging.getLogger("Script_Logger")

        ## USB ISS connection
        clock = 100
        self._conn = i2c_gui2.USB_ISS_Helper(self._port, clock, dummy_connect = False)
        self._chip = i2c_gui2.AD5593R_Chip(self._i2c_address, self._conn, self._logger)

        for i in range(9):  # Channel 8 is temperature
            self._adc_channels[i] = False
        for i in range(8):
            self._dac_channels[i] = False

        self._registers = [
            "ADC_SEQ",
            "GEN_CTRL_REG",
            "ADC_CONFIG",
            "DAC_CONFIG",
            "PULLDWN_CONFIG",
            "LDAC_MODE",
            "PD_REF_CTRL",
                    ]

        self._handle = {}
        for name in self._registers:
            self._chip.read_register("AD5593R", "Config_RD", name, no_message=True)
            self._handle[name] = self._chip["AD5593R", "Config_RD", name]
        
        # Enable internal VRef if we are using it (internal to the ADC)
        value = int(self._handle["PD_REF_CTRL"])
        if self._internal_vref:
            value = value | 0b0000_0010_0000_0000
        else:
            value = value & 0b1111_1101_1111_1111
        self._handle["PD_REF_CTRL"] = value
        self._chip.write_register("AD5593R", "Config_RD", "PD_REF_CTRL")

        self.set_dac_value(0)

        self._handle["LDAC_MODE"] = 0x0000  # alternative is 0x0001, but in this mode you need to write LDAC_MODE with 0x0002 to update the DAC output
        self._chip.write_register("AD5593R", "Config_RD", "LDAC_MODE")

        # Use ADC buffer if not using the SMA adaptor PCB
        # Disable ADC buffer when using the SMA adaptor PCB
        value = 0b000000_0_0_0_0_0_0_0000  #  Disable ADC buffer
        value = 0b000000_0_1_0_0_0_0_0000  #  Enable ADC buffer and keep it always powered
        #value = 0b000000_1_1_0_0_0_0_0000  #  Enable ADC buffer and only power during conversion
        self._handle["GEN_CTRL_REG"] = value
        self._chip.write_register("AD5593R", "Config_RD", "GEN_CTRL_REG")

        adc_reg = 0
        dac_reg = 0
        pulldown_reg = 0x00ff
        self._handle["DAC_CONFIG"] = dac_reg
        self._handle["ADC_CONFIG"] = adc_reg
        self._handle["PULLDWN_CONFIG"] = pulldown_reg
        self._chip.write_register("AD5593R", "Config_RD", "DAC_CONFIG")
        self._chip.write_register("AD5593R", "Config_RD", "ADC_CONFIG")
        self._chip.write_register("AD5593R", "Config_RD", "PULLDWN_CONFIG")

        self.set_calibration(8, 'C', self.adc_to_temp)

    def adc_to_temp(self, adc):
        return 25 + (adc - (0.5/self._vref)*4095)/(2.654 * (2.5/self._vref))

    def set_calibration(self, channel: int, unit: str, function):
        self._calibration[channel] = {
            'unit': unit,
            'function': function,
        }

    def add_adc_pin(self, pin: int):
        if pin not in self._adc_channels or pin == 8:
            raise RuntimeError(f"An invalid pin was selected: {pin}")
        
        self._adc_channels[pin] = True

    def remove_adc_pin(self, pin: int):
        if pin not in self._adc_channels or pin == 8:
            raise RuntimeError(f"An invalid pin was selected: {pin}")
        
        self._adc_channels[pin] = False

    def add_temperature(self):
        self._adc_channels[8] = True

    def remove_temperature(self):
        self._adc_channels[8] = False

    def add_dac_pin(self, pin: int):
        if pin not in self._dac_channels:
            raise RuntimeError(f"An invalid pin was selected: {pin}")
        
        self._dac_channels[pin] = True

    def remove_dac_pin(self, pin: int):
        if pin not in self._dac_channels:
            raise RuntimeError(f"An invalid pin was selected: {pin}")
        
        self._dac_channels[pin] = False

    def configure(self):
        adc_reg = 0
        dac_reg = 0
        pulldown_reg = 0x00ff
        self._num_measurements = 0

        for pin in range(8):
            if self._dac_channels[pin]:  #  Enable DAC pins
                dac_reg = (dac_reg | (1 << pin))
                pulldown_reg = (pulldown_reg & (0xffff - (1 << pin)))
            if self._adc_channels[pin]:  #  Enable ADC pins
                adc_reg = (adc_reg | (1 << pin))
                pulldown_reg = (pulldown_reg & (0xffff - (1 << pin)))
                self._num_measurements += 1

        self._handle["DAC_CONFIG"] = dac_reg
        self._handle["ADC_CONFIG"] = adc_reg
        self._handle["PULLDWN_CONFIG"] = pulldown_reg

        if self._adc_channels[8]:  #  Enable temperature in the ADC sequence if it is chosen
            adc_reg = adc_reg | 0x100
            self._num_measurements += 1
        self._adc_sequence = adc_reg

        self._chip.write_register("AD5593R", "Config_RD", "DAC_CONFIG")
        self._chip.write_register("AD5593R", "Config_RD", "ADC_CONFIG")
        self._chip.write_register("AD5593R", "Config_RD", "PULLDWN_CONFIG")

    def set_dac_value(self, value: int, pin: int | None = None):
        if pin is None:
            for pin_idx in self._dac_channels:
                self.set_dac_value(value, pin_idx)
            return

        if pin not in self._dac_channels:
            raise RuntimeError(f"An invalid pin was selected: {pin}")

        self._chip.read_register("AD5593R", "DAC_RD", f"DAC{pin}")
        self._chip["AD5593R", "DAC_RD", f"DAC{pin}"] = value & 0xfff
        self._chip.write_register("AD5593R", "DAC_RD", f"DAC{pin}", readback_check=False, no_message=True)

    def start_log(self):
        time.sleep(0.5)
        self._rt = RepeatedTimer(self._interval, self.log_measurement)
        self.log_action("ADC", "Logging", "Start")

    def stop_log(self):
        if self._rt is not None:
            self._rt.stop()
            self._rt = None
            self.log_action("ADC", "Logging", "Stop")

    def log_action(self, action_system: str, action_type: str, action_message: str):
        log_action_v2(self._outdir, action_system, action_type, action_message)

    def log_measurement(self):
        measurement = self.do_measurement()

        df = pandas.DataFrame(measurement)

        outfile = self._outdir / 'ADCHistory.sqlite'
        with sqlite3.connect(outfile) as sqlconn:
            df.to_sql('adc', sqlconn, if_exists='append', index=False)

    def do_measurement(self):
        measurement = {
            'timestamp': [],
            'ADC': [],
            'channel': [],
            'voltage': [],
            'vref': [],
            'calibrated': [],
            'calibrated_units': [],
        }

        results = self._chip.read_adc_results(self._adc_sequence, self._num_measurements)
        time = datetime.datetime.now().isoformat(sep=' ')

        for data in results:
            adc = data & 0xfff
            channel = data >> 12
            voltage = (adc/0xfff) * self._vref

            measurement["timestamp"] += [time]
            measurement["ADC"] += [adc]
            measurement["channel"] += [channel]
            measurement["voltage"] += [voltage]
            measurement["vref"] += [self._vref]

            if channel in self._calibration:
                if channel == 8:
                    measurement["calibrated"] += [self._calibration[channel]['function'](adc)]
                else:
                    measurement["calibrated"] += [self._calibration[channel]['function'](voltage)]
                measurement["calibrated_units"] += [self._calibration[channel]['unit']]
            else:
                measurement["calibrated"] += [None]
                measurement["calibrated_units"] += [None]

        return measurement

global exit_loop
exit_loop = False

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
                    prog='Read ADC',
                    description='Control it!\nBy default, this script will take no action apart from finding and attempting to configure the ADC. Use the --turn-on --log --turn-off options to control what actions the script takes./n/nWARNING: This script will conflict with any notebook trying to run things with the USB-ISS',
                    #epilog='Text at the bottom of help'
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
        '-p',
        '--port',
        type = str,
        help = 'The USB-ISS port',
        dest = 'port',
        required = True,
    )
    parser.add_argument(
        '-a',
        '--i2c-address',
        type = int,
        help = 'The I2C address of the AD5593R device. Default: 0x10',
        dest = 'i2c_address',
        default = 0x10,
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
        '--internal-vref',
        action = 'store_true',
        help = 'Use the Internal vref of the AD5593R',
        dest = 'internal_vref',
    )
    parser.add_argument(
        '--log',
        action = 'store_true',
        help = 'Log the ADC measurements. The process will not exit on its own, use Ctrl+C to exit',
        dest = 'log',
    )

    args = parser.parse_args()

    device_meas = ADCMeasurements(
                                    outdir = Path(args.output_directory),
                                    interval = args.measurement_interval,
                                    port = args.port,
                                    vref = 1.024,
                                    i2c_address = args.i2c_address,
                                    internal_vref = args.internal_vref,
                                  )
    
    device_meas.add_temperature()
    #device_meas.add_adc_pin(8)
    #device_meas.add_dac_pin(8)

    device_meas.configure()

    if args.log:
        def signal_handler(sig, frame):
            global exit_loop
            print("Exiting gracefully")
            exit_loop = True

        signal.signal(signal.SIGINT, signal_handler)

        while not exit_loop:
            device_meas.log_measurement()
            time.sleep(args.measurement_interval)

        signal.pause()
    else:
        print(device_meas.do_measurement())
