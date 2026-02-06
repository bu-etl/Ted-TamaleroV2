#############################################################################
# zlib License
#
# (C) 2023 Zach FLowers, Murtaza Safdari <musafdar@cern.ch>, Cristóvão Beirão da Cruz e Silva, Jongho Lee
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import os, sys
import datetime
from tqdm import tqdm
import pandas
import logging
import signal
import sqlite3
import i2c_gui
import i2c_gui.chips
from i2c_gui.usb_iss_helper import USB_ISS_Helper
from i2c_gui.chips.etroc2_chip import register_decoding
from pathlib import Path
import numpy as np

class Chip_Auto_Cal_Helper:
    def __init__(
        self,
        history_filename: str,
        chip_name: str,
        port: str = '/dev/ttyACM0',
        chip_address: int = 0x60,
        ws_address: int = None,
        data_dir: Path = Path('../ETROC-Data/'),
        ):
        # TODO: What if data_dir does not exist?
        # TODO: There is probably a smarter way to handle the hist file name
        # TODO: In fact, the best approch would be to put these steps outside
        # the class and the class only receives one path variable with the
        # full path to the history file
        self._data_dir = data_dir
        self._history_file_path = data_dir / (history_filename + ".sqlite")

        self.chip_name = chip_name
        self.port = port
        self.chip_address = chip_address
        self.ws_address = ws_address

        ## Logger
        self._log_level=logging.WARN
        logging.basicConfig(format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')
        self.logger = logging.getLogger("Auto_Cal_Logger")

        ## Script Helper so i2c_gui works well from a script
        self._script_helper = i2c_gui.ScriptHelper(self.logger)

        self._is_connected = False
        self.etroc_connected = False
        self.ws_connected = False
        self.conn: i2c_gui.Connection_Controller = None
        self.connect()

    def connect(self):
        if self._is_connected:
            self.disconnect()

        self.conn = i2c_gui.Connection_Controller(self._script_helper)
        self.conn.connection_type = "USB-ISS"
        self.conn.handle: USB_ISS_Helper
        self.conn.handle.port = self.port
        self.conn.handle.clk = 100
        self.conn.connect()
        self.logger.setLevel(self._log_level)

        self.chip = i2c_gui.chips.ETROC2_Chip(parent=self._script_helper, i2c_controller=self.conn)
        if self.chip_address is not None:
            self.chip.config_i2c_address(self.chip_address)  # Not needed if you do not access ETROC registers (i.e. only access WS registers)
            self.etroc_connected = True
        if self.ws_address is not None:
            self.chip.config_waveform_sampler_i2c_address(self.ws_address)  # Not needed if you do not access WS registers
            self.ws_connected = True

        self.get_handles()

    def disconnect(self):
        if self._is_connected:
            self.conn.disconnect()
            self._is_connected = False
            self.etroc_connected = False
            self.ws_connected = False

    def get_handles(self):
        if self.etroc_connected:
            self.row_indexer_handle,_,_ = self.chip.get_indexer("row")
            self.column_indexer_handle,_,_ = self.chip.get_indexer("column")
            self.enable_TDC_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Config", "enable_TDC")
            self.CLKEn_THCal_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Config", "CLKEn_THCal")
            self.BufEn_THCal_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Config", "BufEn_THCal")
            self.Bypass_THCal_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Config", "Bypass_THCal")
            self.TH_offset_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Config", "TH_offset")
            self.RSTn_THCal_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Config", "RSTn_THCal")
            self.ScanStart_THCal_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Config", "ScanStart_THCal")
            self.DAC_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Config", "DAC")
            self.ScanDone_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Status", "ScanDone")
            self.BL_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Status", "BL")
            self.NW_handle = self.chip.get_decoded_indexed_var("ETROC2", "Pixel Status", "NW")

    def run_auto_calibration(
        self,
        run_str: str,
        comment_str: str,
        disable_all_pixels: bool = False,
        scan_list = None # [(8, 2), (8, 8), (8, 14)]
        ):
        if not self._is_connected:
            self.connect()

        data = {
            'row': [],
            'col': [],
            'baseline': [],
            'noise_width': [],
            'timestamp': [],
        }

        note_for_df = ''
        if comment_str == '':
            note_for_df = run_str
        else:
            note_for_df = f'{run_str}_{comment_str}'

        if scan_list is None: 
            col_list, row_list = np.meshgrid(np.arange(16),np.arange(16))
            scan_list = list(zip(row_list.flatten(),col_list.flatten()))
        for this_row,this_col in scan_list:
                self.row_indexer_handle.set(this_row)
                self.column_indexer_handle.set(this_col)
                self.chip.read_all_block("ETROC2", "Pixel Config")

                # Disable TDC
                self.enable_TDC_handle.set("0")

                # Enable THCal clock and buffer, disable bypass
                self.CLKEn_THCal_handle.set("1")
                self.BufEn_THCal_handle.set("1")
                self.Bypass_THCal_handle.set("0")
                self.TH_offset_handle.set(hex(0x0a))

                # Send changes to chip
                self.chip.write_all_block("ETROC2", "Pixel Config")

                # Reset the calibration block (active low)
                self.RSTn_THCal_handle.set("0")
                self.chip.write_decoded_value("ETROC2", "Pixel Config", "RSTn_THCal")
                self.RSTn_THCal_handle.set("1")
                self.chip.write_decoded_value("ETROC2", "Pixel Config", "RSTn_THCal")

                # Start and Stop the calibration, (25ns x 2**15 ~ 800 us, ACCumulator max is 2**15)
                self.ScanStart_THCal_handle.set("1")
                self.chip.write_decoded_value("ETROC2", "Pixel Config", "ScanStart_THCal")
                self.ScanStart_THCal_handle.set("0")
                self.chip.write_decoded_value("ETROC2", "Pixel Config", "ScanStart_THCal")

                # Wait for the calibration to be done correctly
                retry_counter = 0
                self.chip.read_all_block("ETROC2", "Pixel Status")
                # print("Scan Done Register: ", ScanDone_handle.get())
                while self.ScanDone_handle.get() != "1":
                    time.sleep(0.01)
                    self.chip.read_all_block("ETROC2", "Pixel Status")
                    retry_counter += 1
                    if retry_counter == 5 and self.ScanDone_handle.get() != "1":
                        print(f"!!!ERROR!!! Scan not done for row {this_row}, col {this_col}!!!")
                        break

                if not disable_all_pixels:
                    self.enable_TDC_handle.set("1")
                # Disable THCal clock and buffer, enable bypass
                self.CLKEn_THCal_handle.set("0")
                self.BufEn_THCal_handle.set("0")
                self.Bypass_THCal_handle.set("1")
                self.DAC_handle.set(hex(0x3ff))

                # Send changes to chip
                self.chip.write_all_block("ETROC2", "Pixel Config")

                data['row'].append(this_row)
                data['col'].append(this_col)
                data['baseline'].append(int(self.BL_handle.get(), 0))
                data['noise_width'].append(int(self.NW_handle.get(), 0))
                data['timestamp'].append(datetime.datetime.now())

        BL_df = pandas.DataFrame(data=data)
        BL_df['chip_name'] = self.chip_name
        BL_df['note'] = note_for_df

        with sqlite3.connect(self._history_file_path) as sqlconn:
            BL_df.to_sql('baselines', sqlconn, if_exists='append', index=False)


def main():
    import argparse

    parser = argparse.ArgumentParser(
                    prog='Make baseline history',
                    description='Control them!',
                    #epilog='Text at the bottom of help'
                    )

    parser.add_argument(
        '-c',
        '--chipName',
        metavar = 'NAME',
        type = str,
        help = 'Name of the chip - no special chars',
        required = True,
        dest = 'chip_name',
    )
    parser.add_argument(
        '-t',
        '--commentStr',
        metavar = 'NAME',
        type = str,
        help = 'Comment string - no special chars',
        required = True,
        dest = 'comment_str',
    )
    parser.add_argument(
        '-d',
        '--disable_all_pixels',
        help = 'disable_all_pixels',
        action = 'store_true',
        dest = 'disable_all_pixels',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help = 'verbose output',
        action = 'store_true',
        dest = 'verbose',
    )
    parser.add_argument(
        '--scan_list',
        metavar = 'LIST',
        # type = list,
        type=lambda a: tuple(map(int, a.split(','))), nargs='+',
        help = 'define scan list, must include 0,0 at the start, ex: 0,0 8,2 8,8 8,14',
        default = None,
        dest = 'scan_list',
    )
    parser.add_argument(
        '--interval_time',
        metavar = 'TIME',
        type = int,
        help = 'interval between automatlic calibration in seconds',
        required = True,
        dest = 'interval_time',
    )
    parser.add_argument(
        '--global_time',
        metavar = 'TIME',
        type = str,
        help = 'global run time for automatic calibration, eg. 1h, 20m, 30s',
        required = True,
        dest = 'global_time',
    )

    args = parser.parse_args()

    def signal_handler(sig, frame):
        print("Exiting gracefully")
        sys.exit(0)

    total_time = -1
    if 'h' in args.global_time:
        total_time = int(args.global_time.split('h')[0]) * 60 * 60
    elif 'm' in args.global_time:
        total_time = int(args.global_time.split('m')[0]) * 60
    elif 's' in args.global_time:
        total_time = int(args.global_time.split('s')[0])
    else:
        print('Please specify the unit of time (h or m or s)')
        sys.exit(0)

    # TODO: This could even be moved to the top of the file, outside a function, after the includes
    i2c_gui.__no_connect__ = False  # Set to fake connecting to an ETROC2 device
    i2c_gui.__no_connect_type__ = "echo"  # for actually testing readback
    #i2c_gui.__no_connect_type__ = "check"  # default behaviour

    cal_helper = Chip_Auto_Cal_Helper(
        history_filename = "BaselineHistory_CC_Jan2024_CERN",
        chip_name = args.chip_name,
        port = "/dev/ttyACM2",
        chip_address = 0x61,
        ws_address = None,
        data_dir = Path('../ETROC-Data/')
    )

    count = 0
    start_time = time.time()

    while True:
        run_str = f"Run{count}"
        signal.signal(signal.SIGINT, signal_handler)

        cal_helper.run_auto_calibration(
            # chip_name = args.chip_name,
            comment_str = args.comment_str,
            run_str = run_str,
            disable_all_pixels = args.disable_all_pixels,
            scan_list = args.scan_list,
        )
        end_time = time.time()

        if (end_time - start_time > total_time):
            print('Exiting because of time limit')
            sys.exit(0)

        count += 1
        if args.verbose:
            print(f'Sleeping for {args.interval_time}s')
        time.sleep(args.interval_time)

if __name__ == "__main__":
    main()