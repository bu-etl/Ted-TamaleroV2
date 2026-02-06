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

#############################################################################
# Modified for ETROC2 I2C testing in jupyter notebooks, Murtaza Safdari
#############################################################################

## Imports
import matplotlib.pyplot as plt
import logging
import numpy as np
import time
import datetime
from tqdm import tqdm
import os, sys
import multiprocessing
import importlib
import pandas
from pathlib import Path
import subprocess
import sqlite3
from mpl_toolkits.axes_grid1 import make_axes_locatable
from fnmatch import fnmatch
import signal

import i2c_gui
import i2c_gui.chips
from i2c_gui.usb_iss_helper import USB_ISS_Helper
from i2c_gui.fpga_eth_helper import FPGA_ETH_Helper
from i2c_gui.chips.etroc2_chip import register_decoding

sys.path.insert(1, f'/home/{os.getlogin()}/ETROC2/ETROC_DAQ')
import run_script
importlib.reload(run_script)


def chip_broadcast_decoded_register_write(
        chip: i2c_gui.chips.ETROC2_Chip,
        decodedRegisterName: str,
        data_to_write: str,
                                          ):
    row_indexer_handle,_,_ = chip.get_indexer("row")
    column_indexer_handle,_,_ = chip.get_indexer("column")

    bit_depth = register_decoding["ETROC2"]["Register Blocks"]["Pixel Config"][decodedRegisterName]["bits"]
    handle = chip.get_decoded_indexed_var("ETROC2", "Pixel Config", decodedRegisterName)

    if len(data_to_write)!=bit_depth:
        print("Binary data_to_write is of incorrect length for",decodedRegisterName, "with bit depth", bit_depth)
    data_hex_modified = hex(int(data_to_write, base=2))

    for row in range(16):
        for col in range(16):
            row_indexer_handle.set(row)
            column_indexer_handle.set(col)

            chip.read_decoded_value("ETROC2", "Pixel Config", decodedRegisterName)

            if(bit_depth>1): handle.set(data_hex_modified)
            elif(bit_depth==1): handle.set(data_to_write)
            else: print(decodedRegisterName, "!!!ERROR!!! Bit depth <1, how did we get here...")

            chip.write_decoded_value("ETROC2", "Pixel Config", decodedRegisterName)

def chip_pixel_decoded_register_write(
        chip: i2c_gui.chips.ETROC2_Chip,
        decodedRegisterName: str,
        data_to_write: str,
                                 ):
    bit_depth = register_decoding["ETROC2"]["Register Blocks"]["Pixel Config"][decodedRegisterName]["bits"]
    handle = chip.get_decoded_indexed_var("ETROC2", "Pixel Config", decodedRegisterName)
    chip.read_decoded_value("ETROC2", "Pixel Config", decodedRegisterName)
    if len(data_to_write)!=bit_depth: print("Binary data_to_write is of incorrect length for",decodedRegisterName, "with bit depth", bit_depth)
    data_hex_modified = hex(int(data_to_write, base=2))
    if(bit_depth>1): handle.set(data_hex_modified)
    elif(bit_depth==1): handle.set(data_to_write)
    else: print(decodedRegisterName, "!!!ERROR!!! Bit depth <1, how did we get here...")
    chip.write_decoded_value("ETROC2", "Pixel Config", decodedRegisterName)

def chip_pixel_decoded_register_read(
        chip: i2c_gui.chips.ETROC2_Chip,
        decodedRegisterName: str,
        key: str,
        need_int: bool = False,
                                ):
    handle = chip.get_decoded_indexed_var("ETROC2", f"Pixel {key}", decodedRegisterName)
    chip.read_decoded_value("ETROC2", f"Pixel {key}", decodedRegisterName)
    if(need_int): return int(handle.get(), base=16)
    else: return handle.get()

def chip_peripheral_decoded_register_write(
        chip: i2c_gui.chips.ETROC2_Chip,
        decodedRegisterName: str,
        data_to_write: str,
                                      ):
    bit_depth = register_decoding["ETROC2"]["Register Blocks"]["Peripheral Config"][decodedRegisterName]["bits"]
    handle = chip.get_decoded_display_var("ETROC2", "Peripheral Config", decodedRegisterName)
    chip.read_decoded_value("ETROC2", "Peripheral Config", decodedRegisterName)
    if len(data_to_write)!=bit_depth: print("Binary data_to_write is of incorrect length for",decodedRegisterName, "with bit depth", bit_depth)
    data_hex_modified = hex(int(data_to_write, base=2))
    if(bit_depth>1): handle.set(data_hex_modified)
    elif(bit_depth==1): handle.set(data_to_write)
    else: print(decodedRegisterName, "!!!ERROR!!! Bit depth <1, how did we get here...")
    chip.write_decoded_value("ETROC2", "Peripheral Config", decodedRegisterName)

def chip_peripheral_decoded_register_read(
        chip: i2c_gui.chips.ETROC2_Chip,
        decodedRegisterName: str,
        key: str,
        need_int: bool = False,
                                     ):
    handle = chip.get_decoded_display_var("ETROC2", f"Peripheral {key}", decodedRegisterName)
    chip.read_decoded_value("ETROC2", f"Peripheral {key}", decodedRegisterName)
    if(need_int): return int(handle.get(), base=16)
    else: return handle.get()

def run_daq(
        timePerPixel: int,
        deadTime: int,
        dirname: str,
        fpga_ip: str,
            ):
    time_per_pixel = timePerPixel
    dead_time_per_pixel = deadTime
    total_scan_time = time_per_pixel + dead_time_per_pixel
    outname = dirname

    today = datetime.date.today()
    todaystr = "../ETROC-Data/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)

    parser = run_script.getOptionParser()
    (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {fpga_ip} -t {int(total_scan_time)} -o {outname} -v -w -s 0x000C -p 0x000f --compressed_translation -d 0x0800 --clear_fifo".split())
    IPC_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'main_process'))
    process.start()

    #IPC_queue.put('start L1A trigger bit')
    IPC_queue.put('start singleShot')
    while not IPC_queue.empty():
        pass

    time.sleep(time_per_pixel)
    #IPC_queue.put('stop L1A trigger bit')
    IPC_queue.put('stop L1A')

    time.sleep(1)
    IPC_queue.put('stop DAQ')
    while not IPC_queue.empty():
        pass

    IPC_queue.put('allow threads to exit')

    process.join()

def check_I2C(
    chip: i2c_gui.chips.ETROC2_Chip,
    chip_name: str,
    i2c_log_dir: Path,
    file_comment: str = None,
    do_peripheral: bool = True,
    do_pixel: bool = True,
    ):
    if do_peripheral:
        ## Check basic I2C functionatity and consistency
        ### Quick test using peripheral registers
        peripheral_success = True
        peripheralRegisterKeys = [i for i in range(32)]
        data = []
        this_log_file = i2c_log_dir / 'PeripheralConsistency.sqlite'
        if file_comment is not None:
            this_log_file = i2c_log_dir / f'PeripheralConsistency_{file_comment}.sqlite'
        for peripheralRegisterKey in peripheralRegisterKeys:
            # Fetch the register
            handle_PeriCfgX = chip.get_display_var("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            chip.read_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            data_bin_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            # Make the flipped bits
            # data_bin_modified_PeriCfgX = list(data_bin_PeriCfgX)
            data_bin_modified_PeriCfgX = data_bin_PeriCfgX.replace('1', '2').replace('0', '1').replace('2', '0')
            # data_bin_modified_PeriCfgX = ''.join(data_bin_modified_PeriCfgX)
            data_hex_modified_PeriCfgX = hex(int(data_bin_modified_PeriCfgX, base=2))
            # Set the register with the value
            handle_PeriCfgX.set(data_hex_modified_PeriCfgX)
            chip.write_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            # Perform two reads to verify the persistence of the change
            # chip.read_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")  # By default, write already does a read at the end
            data_bin_new_1_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            chip.read_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            data_bin_new_2_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            # Undo the change to recover the original register value, and check for consistency
            handle_PeriCfgX.set(hex(int(data_bin_PeriCfgX, base=2)))
            chip.write_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            # chip.read_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            data_bin_recover_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            # Handle what we learned from the tests
            timestamp = datetime.datetime.now().isoformat()
            data += [{
                'register': f"PeriCfg{peripheralRegisterKey}",
                'original_value': data_bin_PeriCfgX,
                'attempted_set_value': data_bin_modified_PeriCfgX,
                'new_value': data_bin_new_1_PeriCfgX,
                'repeated_read_new_value': data_bin_new_2_PeriCfgX,
                'reset_value': data_bin_recover_PeriCfgX,
                'timestamp': timestamp,
                'chip_name': chip_name,
            }]
            # print(f"PeriCfg{peripheralRegisterKey:2}", data_bin_PeriCfgX, "To", data_bin_new_1_PeriCfgX,  "To", data_bin_new_2_PeriCfgX, "To", data_bin_recover_PeriCfgX)
            if(data_bin_new_1_PeriCfgX!=data_bin_new_2_PeriCfgX or data_bin_new_2_PeriCfgX!=data_bin_modified_PeriCfgX or data_bin_recover_PeriCfgX!=data_bin_PeriCfgX):
                peripheral_success = False
            #    print(f"PeriCfg{peripheralRegisterKey:2}", "FAILURE")

        this_df = pandas.DataFrame(data = data)

        with sqlite3.connect(this_log_file) as sqlconn:
            this_df.to_sql('registers', sqlconn, if_exists='append', index=False)

        if peripheral_success:
            print(f"Detailed I2C Check {file_comment} - Peripheral: Success")
        else:
            print(f"Detailed I2C Check {file_comment} - Peripheral: Failure")


    if do_pixel:
        ### Test using selected pixel registers
        check_row = [0, 0, 0, 15]
        check_col = [0, 7, 15, 7]
        check_list = list(zip(check_row, check_col))

        pixel_success = True
        pixelRegisterKeys = [i for i in range(32)]
        data = []
        this_log_file = i2c_log_dir / 'PixelConsistency.sqlite'
        if file_comment is not None:
            this_log_file = i2c_log_dir / f'PixelConsistency_{file_comment}.sqlite'
        row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
        column_indexer_handle,_,_ = chip.get_indexer("column")
        for row, col in check_list:
            column_indexer_handle.set(col)
            row_indexer_handle.set(row)
            for pixelRegisterKey in pixelRegisterKeys:
                # Fetch the register
                handle_PixCfgX = chip.get_indexed_var("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                chip.read_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                data_bin_PixCfgX = format(int(handle_PixCfgX.get(), base=16), '08b')
                # Make the flipped byte
                data_bin_modified_PixCfgX = data_bin_PixCfgX.replace('1', '2').replace('0', '1').replace('2', '0')
                data_hex_modified_PixCfgX = hex(int(data_bin_modified_PixCfgX, base=2))
                # Set the register with the value
                handle_PixCfgX.set(data_hex_modified_PixCfgX)
                chip.write_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                # Perform two reads to verify the persistence of the change
                # chip.read_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                data_bin_new_1_PixCfgX = format(int(handle_PixCfgX.get(), base=16), '08b')
                chip.read_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                data_bin_new_2_PixCfgX = format(int(handle_PixCfgX.get(), base=16), '08b')
                # Undo the change to recover the original register value, and check for consistency
                handle_PixCfgX.set(hex(int(data_bin_PixCfgX, base=2)))
                chip.write_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                # chip.read_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                data_bin_recover_PixCfgX = format(int(handle_PixCfgX.get(), base=16), '08b')
                # Handle what we learned from the tests
                timestamp = datetime.datetime.now().isoformat()
                data += [{
                    'row': row,
                    'col': col,
                    'register': f"PixCfg{pixelRegisterKey}",
                    'original_value': data_bin_PixCfgX,
                    'attempted_set_value': data_bin_modified_PixCfgX,
                    'new_value': data_bin_new_1_PixCfgX,
                    'repeated_read_new_value': data_bin_new_2_PixCfgX,
                    'reset_value': data_bin_recover_PixCfgX,
                    'timestamp': timestamp,
                    'chip_name': chip_name,
                }]
                if(data_bin_new_1_PixCfgX!=data_bin_new_2_PixCfgX or data_bin_new_2_PixCfgX!=data_bin_modified_PixCfgX or data_bin_recover_PixCfgX!=data_bin_PixCfgX):
                    pixel_success = False
                #    print(row,col,f"PixCfg{pixelRegisterKey:2}","FAILURE", data_bin_PixCfgX, "To", data_bin_new_1_PixCfgX,  "To", data_bin_new_2_PixCfgX, "To", data_bin_recover_PixCfgX)

        this_df = pandas.DataFrame(data = data)

        with sqlite3.connect(this_log_file) as sqlconn:
            this_df.to_sql('registers', sqlconn, if_exists='append', index=False)

        if pixel_success:
            print(f"Detailed I2C Check {file_comment} - Pixel: Success")
        else:
            print(f"Detailed I2C Check {file_comment} - Pixel: Failure")

def run_ProbeStation(
        wafer_name: str,
        chip_name: str,
        comment_str: str,
        fpga_ip = "192.168.2.3",
        port = "/dev/ttyACM2",
        chip_address = 0x60,
        ws_address = None,
        run_name_extra = None,
        do_pixel_address: bool = False,
        do_i2c: bool = False,
        do_baseline: bool = False,
        do_qinj: bool = False,
        do_pllcalib: bool = False,
        do_offline: bool = False,
        do_detailed: bool = False,
        row: int = 0,
        col: int = 0,
            ):
    chip_figname = f"LowBiasCurrent_{comment_str}_{wafer_name}_{chip_name}"
    chip_figtitle= f"LowBiasCurrent {comment_str} - {wafer_name}: {chip_name}"
    if run_name_extra is not None:
        chip_figname = f"LowBiasCurrent_{comment_str}_{wafer_name}_{chip_name}_{run_name_extra}"
        chip_figtitle = f"LowBiasCurrent {comment_str} - {wafer_name}: {chip_name} {run_name_extra}"

    fig_outdir = Path('../ETROC-figures')
    fig_outdir = fig_outdir / (datetime.date.today().isoformat() + '_Array_Test_Results')
    fig_outdir.mkdir(exist_ok=True)
    fig_path = str(fig_outdir)

    data_dir = Path('../ETROC-Data/') / (datetime.date.today().isoformat() + '_Array_Test_Results')
    i2c_log_dir = data_dir / f'{comment_str}_{wafer_name}_{chip_name}_R{row}_C{col}_I2C'
    if run_name_extra is not None:
        i2c_log_dir = data_dir / f'{comment_str}_{wafer_name}_{chip_name}_{run_name_extra}_R{row}_C{col}_I2C'
    i2c_log_dir.mkdir(exist_ok = False)

    history_dir = Path('../ETROC-History-WaferProbe')
    history_dir.mkdir(exist_ok = True)

    ## Set defaults
    # 'If set, the full log will be saved to a file (i.e. the log level is ignored)'
    log_file = data_dir / f'{comment_str}_{wafer_name}_{chip_name}_R{row}_C{col}_I2C.log'
    if run_name_extra is not None:
        log_file = data_dir / f'{comment_str}_{wafer_name}_{chip_name}_{run_name_extra}_R{row}_C{col}_I2C.log'
    # 'Set the logging level. Default: WARNING',
    #  ["CRITICAL","ERROR","WARNING","INFO","DEBUG","TRACE","DETAILED_TRACE","NOTSET"]
    log_level_text = "WARNING"


    if log_file:
        #logging.basicConfig(filename=log_file, filemode='w', encoding='utf-8', level=logging.NOTSET, format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')
        logging.basicConfig(filename=log_file, filemode='w', encoding='utf-8', level=logging.DEBUG, format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')
        log_level = 0
    else:
        log_level = 0
        if log_level_text == "CRITICAL":
            log_level=50
        elif log_level_text == "ERROR":
            log_level=40
        elif log_level_text == "WARNING":
            log_level=30
        elif log_level_text == "INFO":
            log_level=20
        elif log_level_text == "DEBUG":
            log_level=10
        elif log_level_text == "TRACE":
            log_level=8
        elif log_level_text == "DETAILED_TRACE":
            log_level=5
        elif log_level_text == "NOTSET":
            log_level=0
        logging.basicConfig(format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')

    i2c_gui.__no_connect__ = False  # Set to fake connecting to an ETROC2 device
    i2c_gui.__no_connect_type__ = "echo"  # for actually testing readback
    #i2c_gui.__no_connect_type__ = "check"  # default behaviour

    ## Start logger and connect
    logger = logging.getLogger("Script_Logger")

    Script_Helper = i2c_gui.ScriptHelper(logger)

    ## USB ISS connection
    conn = i2c_gui.Connection_Controller(Script_Helper)
    conn.connection_type = "USB-ISS"
    conn.handle: USB_ISS_Helper
    conn.handle.port = port
    conn.handle.clk = 100

    ## For FPGA connection (not yet fully implemented)
    #conn.connection_type = "FPGA-Eth"
    #conn.handle: FPGA_ETH_Helper
    #conn.handle.hostname = fpga_ip
    #conn.handle.port = "1024"

    conn.connect()

    chip = i2c_gui.chips.ETROC2_Chip(parent=Script_Helper, i2c_controller=conn)
    chip.config_i2c_address(chip_address)  # Not needed if you do not access ETROC registers (i.e. only access WS registers)
    # chip.config_waveform_sampler_i2c_address(ws_address)  # Not needed if you do not access WS registers

    ## Disable all pixels
    #chip_broadcast_decoded_register_write(chip, "DAC", format(1023, '010b'))
    chip_broadcast_decoded_register_write(chip, "disDataReadout", "1")
    #chip_broadcast_decoded_register_write(chip, "QInjEn", "0")
    #chip_broadcast_decoded_register_write(chip, "disTrigPath", "1")

    row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
    column_indexer_handle,_,_ = chip.get_indexer("column")
    column_indexer_handle.set(col)
    row_indexer_handle.set(row)

    logger.setLevel(log_level)

    if do_detailed:
        check_I2C(
            chip = chip,
            chip_name = f'{wafer_name}_{chip_name}',
            i2c_log_dir = i2c_log_dir,
            file_comment = "Start",
        )

    ## Pixel ID Check
    if do_pixel_address:
        Failure_map = np.zeros((16,16))
        data = []
        pixel_success = True
        status_string = ""
        for this_row in range(16):
            for this_col in range(16):
                column_indexer_handle.set(this_col)
                row_indexer_handle.set(this_row)
                fetched_row = chip_pixel_decoded_register_read(chip, "PixelID-Row", "Status", need_int=True)
                fetched_col = chip_pixel_decoded_register_read(chip, "PixelID-Col", "Status", need_int=True)
                data += [{
                    'col': this_col,
                    'row': this_row,
                    'fetched_col': fetched_col,
                    'fetched_row': fetched_row,
                    'timestamp': datetime.datetime.now(),
                    'chip_name': chip_name,
                }]
                if(this_row!=fetched_row or this_col!=fetched_col):
                    pixel_success = False
                    Failure_map[15-this_row,15-this_col] = 1
                    if status_string == "":
                        status_string = f"({this_row},{this_col})"
                    else:
                        status_string += f", ({this_row},{this_col})"
        column_indexer_handle.set(col)
        row_indexer_handle.set(row)

        if pixel_success:
            print("Pixel Address Check: Success")
        else:
            print("Pixel Address Check: Failure")
            print(f"  Failed pixels: {status_string}")

        Failure_df = pandas.DataFrame(data = data)

        # Store for later use
        failOut = data_dir / f'{wafer_name}_{chip_name}_{comment_str}_FailedPixelsAt_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}.csv'
        Failure_df.to_csv(failOut, index=False)

        if do_detailed:
            check_I2C(
                chip = chip,
                chip_name = f'{wafer_name}_{chip_name}',
                i2c_log_dir = i2c_log_dir,
                file_comment = "AfterPixelAddress",
            )

    ## Simple I2C Check
    if do_i2c and not do_detailed:
        selected_peripheralRegisterKeys = [0]
        data = []
        this_log_file = i2c_log_dir / 'Simplei2cCheckPeripheralConsistency.sqlite'
        peripheral_success = True
        for peripheralRegisterKey in selected_peripheralRegisterKeys:
            # Fetch the register
            handle_PeriCfgX = chip.get_display_var("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            chip.read_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            data_bin_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            # Make the flipped bits
            # data_bin_modified_PeriCfgX = list(data_bin_PeriCfgX)
            data_bin_modified_PeriCfgX = data_bin_PeriCfgX.replace('1', '2').replace('0', '1').replace('2', '0')
            # data_bin_modified_PeriCfgX = ''.join(data_bin_modified_PeriCfgX)
            data_hex_modified_PeriCfgX = hex(int(data_bin_modified_PeriCfgX, base=2))
            # Set the register with the value
            handle_PeriCfgX.set(data_hex_modified_PeriCfgX)
            chip.write_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            # Perform two reads to verify the persistence of the change
            # chip.read_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")  # By default, write already does a read at the end
            data_bin_new_1_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            chip.read_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            data_bin_new_2_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            # Undo the change to recover the original register value, and check for consistency
            handle_PeriCfgX.set(hex(int(data_bin_PeriCfgX, base=2)))
            chip.write_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            # chip.read_register("ETROC2", "Peripheral Config", f"PeriCfg{peripheralRegisterKey}")
            data_bin_recover_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            timestamp = datetime.datetime.now().isoformat()
            data += [{
                'register': f"PeriCfg{peripheralRegisterKey}",
                'original_value': data_bin_PeriCfgX,
                'attempted_set_value': data_bin_modified_PeriCfgX,
                'new_value': data_bin_new_1_PeriCfgX,
                'repeated_read_new_value': data_bin_new_2_PeriCfgX,
                'reset_value': data_bin_recover_PeriCfgX,
                'timestamp': timestamp,
                'chip_name': f'{wafer_name}_{chip_name}',
            }]

            if(data_bin_new_1_PeriCfgX!=data_bin_new_2_PeriCfgX or data_bin_new_2_PeriCfgX!=data_bin_modified_PeriCfgX or data_bin_recover_PeriCfgX!=data_bin_PeriCfgX):
                peripheral_success = False
            else:
                peripheral_success = True

        this_df = pandas.DataFrame(data = data)

        with sqlite3.connect(this_log_file) as sqlconn:
            this_df.to_sql('registers', sqlconn, if_exists='append', index=False)

        if peripheral_success:
            print(f"Simple I2C Check - Peripheral: Success")
        else:
            print(f"Simple I2C Check - Peripheral: Failure")

        selected_pixelRegisterKeys = [0]
        data = []
        this_log_file = i2c_log_dir / 'Simplei2cPixelConsistency.sqlite'
        pixel_success = None

        for pixelRegisterKey in selected_pixelRegisterKeys:
                # Fetch the register
                handle_PixCfgX = chip.get_indexed_var("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                chip.read_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                data_bin_PixCfgX = format(int(handle_PixCfgX.get(), base=16), '08b')
                # Make the flipped byte
                data_bin_modified_PixCfgX = data_bin_PixCfgX.replace('1', '2').replace('0', '1').replace('2', '0')
                data_hex_modified_PixCfgX = hex(int(data_bin_modified_PixCfgX, base=2))
                # Set the register with the value
                handle_PixCfgX.set(data_hex_modified_PixCfgX)
                chip.write_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                # Perform two reads to verify the persistence of the change
                # chip.read_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                data_bin_new_1_PixCfgX = format(int(handle_PixCfgX.get(), base=16), '08b')
                chip.read_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                data_bin_new_2_PixCfgX = format(int(handle_PixCfgX.get(), base=16), '08b')
                # Undo the change to recover the original register value, and check for consistency
                handle_PixCfgX.set(hex(int(data_bin_PixCfgX, base=2)))
                chip.write_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                # chip.read_register("ETROC2", "Pixel Config", f"PixCfg{pixelRegisterKey}")
                data_bin_recover_PixCfgX = format(int(handle_PixCfgX.get(), base=16), '08b')
                data += [{
                    'row': row,
                    'col': col,
                    'register': f"PixCfg{pixelRegisterKey}",
                    'original_value': data_bin_PixCfgX,
                    'attempted_set_value': data_bin_modified_PixCfgX,
                    'new_value': data_bin_new_1_PixCfgX,
                    'repeated_read_new_value': data_bin_new_2_PixCfgX,
                    'reset_value': data_bin_recover_PixCfgX,
                    'timestamp': timestamp,
                    'chip_name': f'{wafer_name}_{chip_name}',
                }]

                if(data_bin_new_1_PixCfgX!=data_bin_new_2_PixCfgX or data_bin_new_2_PixCfgX!=data_bin_modified_PixCfgX or data_bin_recover_PixCfgX!=data_bin_PixCfgX):
                    pixel_success = False
                else:
                    pixel_success = True

        this_df = pandas.DataFrame(data = data)

        with sqlite3.connect(this_log_file) as sqlconn:
            this_df.to_sql('registers', sqlconn, if_exists='append', index=False)

        if pixel_success:
            print(f"Simple I2C Check - Pixel: Success")
        else:
            print(f"Simple I2C Check - Pixel: Failure")

    ## Automated baseline scan
    if do_baseline:
        # Enable THCal clock and buffer, disable bypass
        chip_pixel_decoded_register_write(chip, "CLKEn_THCal", "1")
        chip_pixel_decoded_register_write(chip, "BufEn_THCal", "1")
        chip_pixel_decoded_register_write(chip, "Bypass_THCal", "0")
        chip_pixel_decoded_register_write(chip, "TH_offset", format(0x0c, '06b'))
        time.sleep(0.1)

        # Reset the calibration block (active low)
        chip_pixel_decoded_register_write(chip, "RSTn_THCal", "0")
        time.sleep(0.1)
        chip_pixel_decoded_register_write(chip, "RSTn_THCal", "1")
        time.sleep(0.1)

        # Start and Stop the calibration, (25ns x 2**15 ~ 800 us, ACCumulator max is 2**15)
        chip_pixel_decoded_register_write(chip, "ScanStart_THCal", "1")
        time.sleep(1)
        chip_pixel_decoded_register_write(chip, "ScanStart_THCal", "0")
        time.sleep(1)

        # Check the calibration done correctly
        if(chip_pixel_decoded_register_read(chip, "ScanDone", "Status")!="1"): print("The automated threshold calibration may not have completed")

        baseline = chip_pixel_decoded_register_read(chip, "BL", "Status", need_int=True)
        noise_width = chip_pixel_decoded_register_read(chip, "NW", "Status", need_int=True)
        data = [{
            'col': col,
            'row': row,
            'baseline': baseline,
            'noise_width': noise_width,
            'timestamp': datetime.datetime.now(),
            'chip_name': f'{wafer_name}_{chip_name}',
        }]

        # Disable clock and buffer after charge injection
        chip_pixel_decoded_register_write(chip, "CLKEn_THCal", "0")
        chip_pixel_decoded_register_write(chip, "BufEn_THCal", "0")
        chip_pixel_decoded_register_write(chip, "Bypass_THCal", "1")

        print(f"Automated Baseline Scan: BL={baseline}, NW={noise_width}")

        BL_df = pandas.DataFrame(data = data)

        # Store for later use
        baselineOut = data_dir / f'{wafer_name}_{chip_name}_{comment_str}_BaselineAt_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}.csv'
        BL_df.to_csv(baselineOut, index=False)

        if do_detailed:
            check_I2C(
                chip = chip,
                chip_name = f'{wafer_name}_{chip_name}',
                i2c_log_dir = i2c_log_dir,
                file_comment = "AfterBaseline",
            )

    ### Store results in database
    if do_baseline or do_pixel_address:
        note = f'{wafer_name}_{chip_name}_{comment_str}'
        if run_name_extra is not None:
            note = f'{wafer_name}_{chip_name}_{comment_str}-{run_name_extra}'
        new_columns = {
            'note': f'{note}',
        }

        if do_baseline:
            for col in new_columns:
                BL_df[col] = new_columns[col]

        baselinefile = history_dir / 'BaselineHistory.sqlite'
        failOut = history_dir / 'FailedPixelHistory.sqlite'

        init_cmd = [
            'cd ' + str(history_dir.resolve()),
            'git stash -u',
            'git pull',
        ]

        end_cmd = [
            'cd ' + str(history_dir.resolve()),
        ]
        if do_baseline:
            end_cmd += [
                'git add BaselineHistory.sqlite',
            ]
        if do_pixel_address:
            end_cmd += [
                'git add FailedPixelHistory.sqlite',
            ]
        end_cmd += [
            'git commit -m "Added new history entry"',
            'git push',
            'git stash pop',
            'git stash clear',
        ]

        init_cmd = [x + '\n' for x in init_cmd]
        end_cmd  = [x + '\n' for x in end_cmd]

        p = subprocess.Popen(
            '/bin/bash',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            )

        for cmd in init_cmd:
            p.stdin.write(cmd + "\n")
        p.stdin.close()
        p.wait()

        # print(p.stdout.read())

        if do_baseline:
            with sqlite3.connect(baselinefile) as sqlconn:
                BL_df.to_sql('baselines', sqlconn, if_exists='append', index=False)

        if do_pixel_address:
            with sqlite3.connect(failOut) as sqlconn:
                Failure_df.to_sql('pixels', sqlconn, if_exists='append', index=False)

        p = subprocess.Popen(
            '/bin/bash',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            )

        for cmd in end_cmd:
            p.stdin.write(cmd + "\n")
        p.stdin.close()
        p.wait()

        #print(p.stdout.read())

    ## QInj data taking check
    if do_qinj and do_baseline:
        ## Set Peripheral Registers
        chip_peripheral_decoded_register_write(chip, "EFuse_Prog", format(0x00017f0f, '032b'))
        chip_peripheral_decoded_register_write(chip, "singlePort", '1')
        chip_peripheral_decoded_register_write(chip, "serRateLeft", '00')
        chip_peripheral_decoded_register_write(chip, "serRateRight", '00')
        chip_peripheral_decoded_register_write(chip, "onChipL1AConf", '00')
        chip_peripheral_decoded_register_write(chip, "PLL_ENABLEPLL", '1')
        chip_peripheral_decoded_register_write(chip, "chargeInjectionDelay", format(0x0a, '05b'))
        chip_peripheral_decoded_register_write(chip, "triggerGranularity", format(0x00, '03b')) # only for trigger bit

        ## Force Re-align of the FC
        chip_peripheral_decoded_register_write(chip, "asyAlignFastcommand", "1")
        chip_peripheral_decoded_register_write(chip, "asyAlignFastcommand", "0")

        # Release the maximum and minimum range for trigger and data
        chip_pixel_decoded_register_write(chip, "upperTOATrig", format(0x3ff, '010b'))
        chip_pixel_decoded_register_write(chip, "lowerTOATrig", format(0x000, '010b'))
        chip_pixel_decoded_register_write(chip, "upperTOTTrig", format(0x1ff, '09b'))
        chip_pixel_decoded_register_write(chip, "lowerTOTTrig", format(0x000, '09b'))
        chip_pixel_decoded_register_write(chip, "upperCalTrig", format(0x3ff, '010b'))
        chip_pixel_decoded_register_write(chip, "lowerCalTrig", format(0x000, '010b'))
        chip_pixel_decoded_register_write(chip, "upperTOA", format(0x3ff, '010b'))
        chip_pixel_decoded_register_write(chip, "lowerTOA", format(0x000, '010b'))
        chip_pixel_decoded_register_write(chip, "upperTOT", format(0x1ff, '09b'))
        chip_pixel_decoded_register_write(chip, "lowerTOT", format(0x000, '09b'))
        chip_pixel_decoded_register_write(chip, "upperCal", format(0x3ff, '010b'))
        chip_pixel_decoded_register_write(chip, "lowerCal", format(0x000, '010b'))

        if do_pllcalib:
            chip_peripheral_decoded_register_write(chip, "asyPLLReset", "0")
            time.sleep(0.2)
            chip_peripheral_decoded_register_write(chip, "asyPLLReset", "1")
            chip_peripheral_decoded_register_write(chip, "asyStartCalibration", "0")
            time.sleep(0.2)
            chip_peripheral_decoded_register_write(chip, "asyStartCalibration", "1")

        #### One time run to set fpga firmware
        #firmware_time = 5
        #parser = run_script.getOptionParser()
        #(options, args) = parser.parse_args(args=f"-f --useIPC --hostname {fpga_ip} -t {firmware_time + 3} -o CanBeRemoved -v -w --compressed_translation -s 0x000C -p 0x000f -d 0x0800 --clear_fifo".split())
        #IPC_queue = multiprocessing.Queue()
        #process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_Start_LEDs'))
        #process.start()

        ##IPC_queue.put('start L1A trigger bit')
        #IPC_queue.put('start singleShot')
        #while not IPC_queue.empty():
        #    pass
        #time.sleep(firmware_time)
        #IPC_queue.put('stop DAQ')
        ##IPC_queue.put('stop L1A trigger bit')
        #IPC_queue.put('stop L1A')
        #while not IPC_queue.empty():
        #    pass
        #IPC_queue.put('allow threads to exit')
        #process.join()


        #SelectedQInj = [10, 15, 20, 25]
        SelectedQInj = [15]
        savedirname = ""

        for QInj in SelectedQInj:
            print(f"QInj data taking for QInj={QInj} check output data to check for success")

            chip_pixel_decoded_register_write(chip, "Bypass_THCal", "0")               # Bypass threshold calibration -> manual DAC setting
            chip_pixel_decoded_register_write(chip, "QSel", format(QInj, '05b'))       # Ensure we inject selected charge
            chip_pixel_decoded_register_write(chip, "TH_offset", format(0x0c, '06b'))  # Offset used to add to the auto BL for real triggering
            chip_pixel_decoded_register_write(chip, "disDataReadout", "0")             # ENable readout
            chip_pixel_decoded_register_write(chip, "QInjEn", "1")                     # ENable charge injection for the selected pixel
            chip_pixel_decoded_register_write(chip, "L1Adelay", format(0x01f5, '09b')) # Change L1A delay - circular buffer in ETROC2 pixel
            chip_pixel_decoded_register_write(chip, "disTrigPath", "0")                # Enable trigger path
            time.sleep(0.1)

            run_name = f'ProbeStation_testing_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}_Q{QInj}_{wafer_name}_{chip_name.replace("_","")}_'+comment_str+f'_R{row}_C{col}'
            if run_name_extra is not None:
                run_name = f'ProbeStation_testing_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}_Q{QInj}_{run_name_extra}_{wafer_name}_{chip_name.replace("_","")}_'+comment_str+f'_R{row}_C{col}'
            savedirname = run_name
            run_daq(8, 5, run_name, fpga_ip)

            chip_pixel_decoded_register_write(chip, "Bypass_THCal", "1")   # Bypass threshold calibration -> manual DAC setting
            chip_pixel_decoded_register_write(chip, "disDataReadout", "1")
            chip_pixel_decoded_register_write(chip, "QInjEn", "0")
            chip_pixel_decoded_register_write(chip, "disTrigPath", "1")
            time.sleep(0.1)

            if do_detailed:
                check_I2C(
                    chip = chip,
                    chip_name = f'{wafer_name}_{chip_name}',
                    i2c_log_dir = i2c_log_dir,
                    file_comment = f"AfterQInj{QInj}DAQ",
                )
        
        if do_offline:
            os.system(f"python standalone_translate_WaferProbe_etroc2_data.py -d ../ETROC-Data/{datetime.datetime.now().strftime('%Y-%m-%d')}_Array_Test_Results/{savedirname}")


    # Disconnect chip
    conn.disconnect()

def main():
    import argparse

    parser = argparse.ArgumentParser(
                    prog='TID measurements',
                    description='Control them!',
                    #epilog='Text at the bottom of help'
                    )

    parser.add_argument(
        '-w',
        '--waferName',
        metavar = 'NAME',
        type = str,
        help = 'Name of the wafer - no special chars',
        required = True,
        dest = 'wafer_name',
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
        '-l',
        '--infiniteLoop',
        help = 'Do infinite loop',
        action = 'store_true',
        dest = 'infinite_loop',
    )
    parser.add_argument(
        '-a',
        '--doPixelAddress',
        help = 'Do the I2C Pixel Address test',
        action = 'store_true',
        dest = 'do_pixel_address',
    )
    parser.add_argument(
        '-i',
        '--doI2C',
        help = 'Do the I2C test',
        action = 'store_true',
        dest = 'do_i2c',
    )
    parser.add_argument(
        '-b',
        '--doBaseline',
        help = 'Do the baseline measurement, required in order to take data with QInj',
        action = 'store_true',
        dest = 'do_baseline',
    )
    parser.add_argument(
        '-q',
        '--doQInj',
        help = 'Do the data taking with QInj, it is necessary to do the baseline in order to do QInj',
        action = 'store_true',
        dest = 'do_qinj',
    )
    parser.add_argument(
        '-p',
        '--doPLLcalib',
        help = 'Do the PLL calibration, it is required if you do not see the Qinj data',
        action = 'store_true',
        dest = 'do_pllcalib',
    )
    parser.add_argument(
        '-f',
        '--doOffline',
        help = 'Do offline translation',
        action = 'store_true',
        dest = 'do_offline',
    )
    parser.add_argument(
        '--minV',
        metavar = 'VOLTAGE',
        type = float,
        help = 'Minimum voltage for V scan, V scan only done if both max and min are set. Default: 1.2',
        default = 1.2,
        dest = 'minV',
    )
    parser.add_argument(
        '--maxV',
        metavar = 'VOLTAGE',
        type = float,
        help = 'Maximum voltage for V scan, V scan only done if both max and min are set. Default: 1.2',
        default = 1.2,
        dest = 'maxV',
    )
    parser.add_argument(
        '--stepV',
        metavar = 'VOLTAGE',
        type = float,
        help = 'Step for the V scan, V scan only done if both max and min are set',
        default = 0.05,
        dest = 'stepV',
    )
    parser.add_argument(
        '--scanTypeV',
        metavar = 'TYPE',
        type = str,
        help = 'Type of voltage scan to perform, must be one of Analog, Digital or Both. Default: Digital. The code assumes V1 is the Analog power supply and V2 is the Digital power supply.',
        choices = ['Analog', 'Both', 'Digital'],
        default = 'Digital',
        dest = 'scanTypeV',
    )
    parser.add_argument(
        '-r',
        '--reverseVScan',
        help = 'Do the V scan from higher voltage values to lower voltage values, instead of the default low to high.',
        action = 'store_true',
        dest = 'reverseVScan',
    )
    parser.add_argument(
        '--row',
        metavar = 'ROW',
        type = int,
        help = 'Row index of the pixel to be scanned. Default: 0',
        default = 0,
        dest = 'row',
    )
    parser.add_argument(
        '--col',
        metavar = 'COL',
        type = int,
        help = 'Col index of the pixel to be scanned. Default: 0',
        default = 0,
        dest = 'col',
    )
    parser.add_argument(
        '-d',
        '--doDetailed',
        help = 'If set, detailed I2C checks will be performed after every test to verify that reading/writing I2C still works',
        action = 'store_true',
        dest = 'do_detailed',
    )
    parser.add_argument(
        '-n',
        '--doNoise',
        help = 'If set, noise scan will be performed, only if baseline measurement is also done',
        action = 'store_true',
        dest = 'do_noise',
    )

    args = parser.parse_args()

    if args.row > 15 or args.row < 0:
        raise RuntimeError("The pixel row must be within the range 0 to 15")
    if args.col > 15 or args.col < 0:
        raise RuntimeError("The pixel column must be within the range 0 to 15")

    # from read_current import DeviceMeasurements
    # delay_time = 5
    # powerDevices = DeviceMeasurements(outdir=Path('.'), interval=delay_time)
    # powerDevices.find_devices()

    def signal_handler(sig, frame):
        print("Exiting gracefully")

        # powerDevices.turn_off()

        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    count = 0
    while True:
        run_str = f"Run{count}"

        run_ProbeStation(
            wafer_name = args.wafer_name,
            chip_name = args.chip_name,
            comment_str = args.comment_str,
            run_name_extra = f"{run_str}",
            do_pixel_address = args.do_pixel_address,
            do_i2c = args.do_i2c,
            do_baseline = args.do_baseline,
            do_qinj = args.do_qinj,
            do_pllcalib = args.do_pllcalib,
            do_offline = args.do_offline,
            row = args.row,
            col = args.col,
            do_detailed = args.do_detailed,
        )

        if not args.infinite_loop:
            break

        # do_analog = False
        # do_digital = False
        # voltage_str = "None"
        # if args.scanTypeV == 'Digital':
        #     do_digital = True
        #     voltage_str = "VD"
        # elif args.scanTypeV == 'Analog':
        #     do_analog = True
        #     voltage_str = "VA"
        # elif args.scanTypeV == 'Both':
        #     do_analog = True
        #     do_digital = True
        #     voltage_str = "V"
        # else:
        #     raise RuntimeError("Unknown scanTypeV selected")

        # voltage_steps = int((args.maxV - args.minV)/args.stepV)
        # if voltage_steps <= 0:
        #     voltage_steps = 1
        # voltage_list = list(np.linspace(args.minV, args.maxV, voltage_steps))
        # if args.reverseVScan:
        #     voltage_list.reverse()

        # powerDevices.turn_on()

        # time.sleep(1)

        # try:
        #     for voltage in voltage_list:
        #         if len(voltage_list) > 1:
        #             print(f"Setting voltage to {voltage} V")

        #         if do_analog:
        #             powerDevices.set_power_V1(voltage)
        #         if do_digital:
        #             powerDevices.set_power_V2(voltage)
        #         if do_analog or do_digital:
        #             time.sleep(1)

        #         run_ProbeStation(
        #             wafer_name = args.wafer_name,
        #             chip_name = args.chip_name,
        #             comment_str = args.comment_str,
        #             run_name_extra = f"{voltage_str}{voltage}_{run_str}",
        #             do_pixel_address = args.do_pixel_address,
        #             do_i2c = args.do_i2c,
        #             do_baseline = args.do_baseline,
        #             do_qinj = args.do_qinj,
        #             row = args.row,
        #             col = args.col,
        #             do_detailed = args.do_detailed,
        #         )
        # except:
        #     print("There was an exception!!!!!!!!!!!!!!!!!!!!!!!!")
        # finally:
        #     powerDevices.turn_off()
        #     time.sleep(1)

        # count += 1
        # if not args.infinite_loop:
        #     break

if __name__ == "__main__":
    main()
