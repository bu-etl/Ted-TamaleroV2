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

DAC_scan_root = '../ETROC-Data'
DAC_scan_file_pattern = "*FPGA_Data.dat"
def take_trigger_data_for_DAC_scan(
        chip: i2c_gui.chips.ETROC2_Chip,
        current_DAC: int,
        fpga_ip: str,
        fpga_time: int,
        QInj: int,
        threshold_name: str,
                                   ):
    # Set the DAC v, Qinj {Qinj}fCalue to the value being scanned
    chip_pixel_decoded_register_write(chip, "DAC", format(current_DAC, '010b'))

    today_str = datetime.date.today().isoformat() # If the day changes while taking data, like this we guarantee to pick up the correct data below
    parser = run_script.getOptionParser()
    (options, args) = parser.parse_args(args=f"--useIPC --hostname {fpga_ip} -o {threshold_name} -v --reset_till_trigger_linked -s 0x000C -p 0x000f -d 0x0800 -c 0x0001 --fpga_data_time_limit {int(fpga_time)} --fpga_data_QInj --check_trigger_link_at_end --nodaq --DAC_Val {int(current_DAC)}".split())
    IPC_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_{QInj}_{current_DAC}'))
    process.start()
    process.join()

    path_pattern = f"*{today_str}_Array_Test_Results/{threshold_name}"

    file_list = []
    for path, subdirs, files in os.walk(DAC_scan_root):
        if not fnmatch(path, path_pattern): continue
        for name in files:
            pass
            if fnmatch(name, DAC_scan_file_pattern):
                file_list.append(os.path.join(path, name))
                print(file_list[-1])

    found_DAC = False
    for file_index, file_name in enumerate(file_list):
        with open(file_name) as infile:
            for line in infile:
                text_list = line.split(',')
                FPGA_state = text_list[0]
                FPGA_data = int(text_list[3])
                triggerbit_data = int(text_list[5])
                DAC = int(text_list[6])
                if DAC != current_DAC:
                    continue
                if triggerbit_data is None:
                    continue
                return triggerbit_data
    return None

def binary_search_DAC_scan(
        QInj: int,
        baseline: int,
        baseline_offset: int,
        chip: i2c_gui.chips.ETROC2_Chip,
        pixel_row: int,
        pixel_col: int,
        extra_output_name: str, # use {run_name_extra}_{TID_str} for compatibility with old code
        fpga_ip: str,
        fpga_time: int,
        baseline_step: int = 1,
    ):
    from math import floor

    row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
    column_indexer_handle,_,_ = chip.get_indexer("column")

    # Set the pixel to act on
    column_indexer_handle.set(pixel_col)
    row_indexer_handle.set(pixel_row)
    print("Pixel:",pixel_col,pixel_row)

    # Enable charge injection
    chip_pixel_decoded_register_write(chip, "disDataReadout", "0")
    chip_pixel_decoded_register_write(chip, "QInjEn", "1")
    chip_pixel_decoded_register_write(chip, "disTrigPath", "0")
    # Bypass Cal Threshold
    chip_pixel_decoded_register_write(chip, "Bypass_THCal", "1")

    # Modifying charge injected
    chip_pixel_decoded_register_write(chip, "QSel", format(QInj, '05b'))
    threshold_name = f'E2_testing_VRef_SCurve_{extra_output_name}_Pixel_C{pixel_col}_R{pixel_row}_QInj_{QInj}_HVoff_pf_hits'

    parser = run_script.getOptionParser()
    (options, args) = parser.parse_args(args=f"--useIPC --hostname {fpga_ip} -o {threshold_name} -v -w --reset_till_trigger_linked -s 0x000C -p 0x000f -d 0x0800 -c 0x0001 --fpga_data_time_limit 3 --fpga_data_QInj --check_trigger_link_at_end --nodaq --clear_fifo".split())
    IPC_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_link'))
    process.start()
    process.join()

    min_scan = int(baseline - baseline_offset)
    max_scan = 1023
    scan_range = int(max_scan - min_scan)
    processed_DACs = {}

    has_knee = True
    knee_DAC = None
    while True:
        if len(processed_DACs) == 0:
            current_DAC = max_scan
        elif len(processed_DACs) == 1:
            current_DAC = min_scan
        elif len(processed_DACs) == 2:
            current_DAC = int(floor(min_scan + scan_range/2.))
        if current_DAC in processed_DACs:
            print(f"DAC {current_DAC} already processed, exiting")
            break
        if current_DAC > max_scan or current_DAC < min_scan:
            print(f"DAC {current_DAC} is outside the range, exiting")
            break
        print(QInj, current_DAC)

        processed_DACs[current_DAC] = take_trigger_data_for_DAC_scan(
            chip,
            current_DAC,
            fpga_ip,
            fpga_time,
            QInj,
            threshold_name
        )
        if processed_DACs[current_DAC] is None:
            processed_DACs.pop(current_DAC)
            continue

        if len(processed_DACs) == 3:
            if processed_DACs[1023] > 0:
                has_knee = False
                break

        if len(processed_DACs) < 3:
            continue

        from bisect import bisect_right, bisect_left
        DAC_list = list(processed_DACs.keys())
        DAC_list.sort()
        previous_DAC = current_DAC
        if processed_DACs[current_DAC] > 0:  # Go right
            next_DAC = DAC_list[bisect_right(DAC_list, current_DAC)]
            current_DAC = int(current_DAC + floor((next_DAC - current_DAC)/2.))
            pass
        else:  # Go left
            prev_DAC = DAC_list[bisect_left(DAC_list, current_DAC) - 1]
            current_DAC = int(current_DAC - floor((current_DAC - prev_DAC)/2.))
            pass

        if abs(current_DAC - previous_DAC) == 1: # Found the end
            knee_DAC = current_DAC
            break

    if has_knee:
        for step in range(11):
            offset = step - 5
            this_DAC = current_DAC + offset
            if this_DAC > 1023 or this_DAC < 0:
                continue
            if this_DAC not in processed_DACs:
                processed_DACs[this_DAC] = take_trigger_data_for_DAC_scan(
                    chip,
                    this_DAC,
                    fpga_ip,
                    fpga_time,
                    QInj,
                    threshold_name
                )

    if int(baseline) not in processed_DACs:
        processed_DACs[int(baseline)] = take_trigger_data_for_DAC_scan(
            chip,
            int(baseline),
            fpga_ip,
            fpga_time,
            QInj,
            threshold_name
        )

    for step in range(0, baseline_offset, baseline_step):
        this_DAC = int(baseline + step + 1)
        if this_DAC > 1023 or this_DAC < 0:
            continue
        if this_DAC not in processed_DACs:
            processed_DACs[this_DAC] = take_trigger_data_for_DAC_scan(
                chip,
                this_DAC,
                fpga_ip,
                fpga_time,
                QInj,
                threshold_name
            )

    for step in range(0, baseline_offset, baseline_step):
        this_DAC = int(baseline - step - 1)
        if this_DAC > 1023 or this_DAC < 0:
            continue
        if this_DAC not in processed_DACs:
            processed_DACs[this_DAC] = take_trigger_data_for_DAC_scan(
                chip,
                this_DAC,
                fpga_ip,
                fpga_time,
                QInj,
                threshold_name
            )

    # Disable charge injection
    chip_pixel_decoded_register_write(chip, "QInjEn", "0")
    chip_pixel_decoded_register_write(chip, "disDataReadout", "1")
    chip_pixel_decoded_register_write(chip, "disTrigPath", "1")

    return processed_DACs, knee_DAC

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
                print(f"PeriCfg{peripheralRegisterKey:2}", "FAILURE")

        this_df = pandas.DataFrame(data = data)

        with sqlite3.connect(this_log_file) as sqlconn:
            this_df.to_sql('registers', sqlconn, if_exists='append', index=False)


    if do_pixel:
        ### Test using selected pixel registers
        check_row = [0, 0, 0, 15]
        check_col = [0, 7, 15, 7]
        check_list = list(zip(check_row, check_col))

        pixelRegisterKeys = [i for i in range(32)]
        data = []
        this_log_file = i2c_log_dir / 'PixelConsistency.sqlite'
        if file_comment is not None:
            this_log_file = i2c_log_dir / f'PixelConsistency_{file_comment}.sqlite'
        row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
        column_indexer_handle,_,_ = chip.get_indexer("column")
        for row, col in check_list:
            print("Pixel", row, col)
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
                    print(row,col,f"PixCfg{pixelRegisterKey:2}","FAILURE", data_bin_PixCfgX, "To", data_bin_new_1_PixCfgX,  "To", data_bin_new_2_PixCfgX, "To", data_bin_recover_PixCfgX)

        this_df = pandas.DataFrame(data = data)

        with sqlite3.connect(this_log_file) as sqlconn:
            this_df.to_sql('registers', sqlconn, if_exists='append', index=False)

def run_TID(
        chip_name,
        TID_str,
        fpga_ip = "192.168.2.3",
        port = "/dev/ttyACM1",
        chip_address = 0x60,
        ws_address = None,
        do_detailed = True,
        run_name_extra = None,
        do_knee_finding: bool = False,
        do_full_scan: bool = False,
        do_row_scan: bool = False,
        only_baseline: bool = False,
            ):
    ## Specify board name
    # !!!!!!!!!!!!
    # It is very important to correctly set the chip name, this value is stored with the data
    chip_figname = f"LowBiasCurrent_{TID_str}_{chip_name}"
    if run_name_extra is not None:
        chip_figname = f"LowBiasCurrent_{TID_str}_{chip_name}_{run_name_extra}"
    chip_figtitle= "LowBiasCurrent "+TID_str+chip_name

    fig_outdir = Path('../ETROC-figures')
    fig_outdir = fig_outdir / (datetime.date.today().isoformat() + '_Array_Test_Results')
    fig_outdir.mkdir(exist_ok=True)
    fig_path = str(fig_outdir)

    data_dir = Path('../ETROC-Data/') / (datetime.date.today().isoformat() + '_Array_Test_Results')
    i2c_log_dir = data_dir / f'{TID_str}_{chip_name}_I2C'
    if run_name_extra is not None:
        i2c_log_dir = data_dir / f'{TID_str}_{chip_name}_{run_name_extra}_I2C'
    i2c_log_dir.mkdir(exist_ok = False)

    ## Set defaults
    # 'If set, the full log will be saved to a file (i.e. the log level is ignored)'
    log_file = data_dir / f'{TID_str}_{chip_name}_I2C.log'
    if run_name_extra is not None:
        log_file = data_dir / f'{TID_str}_{chip_name}_{run_name_extra}_I2C.log'
    # 'Set the logging level. Default: WARNING',
    #  ["CRITICAL","ERROR","WARNING","INFO","DEBUG","TRACE","DETAILED_TRACE","NOTSET"]
    log_level_text = "WARNING"
    # 'The port name the USB-ISS module is connected to. Default: COM3'


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

    logger.setLevel(log_level)

    ## Useful Functions
    def pixel_decoded_register_write(decodedRegisterName, data_to_write):
        bit_depth = register_decoding["ETROC2"]["Register Blocks"]["Pixel Config"][decodedRegisterName]["bits"]
        handle = chip.get_decoded_indexed_var("ETROC2", "Pixel Config", decodedRegisterName)
        chip.read_decoded_value("ETROC2", "Pixel Config", decodedRegisterName)
        if len(data_to_write)!=bit_depth: print("Binary data_to_write is of incorrect length for",decodedRegisterName, "with bit depth", bit_depth)
        data_hex_modified = hex(int(data_to_write, base=2))
        if(bit_depth>1): handle.set(data_hex_modified)
        elif(bit_depth==1): handle.set(data_to_write)
        else: print(decodedRegisterName, "!!!ERROR!!! Bit depth <1, how did we get here...")
        chip.write_decoded_value("ETROC2", "Pixel Config", decodedRegisterName)

    def pixel_decoded_register_read(decodedRegisterName, key, need_int=False):
        handle = chip.get_decoded_indexed_var("ETROC2", f"Pixel {key}", decodedRegisterName)
        chip.read_decoded_value("ETROC2", f"Pixel {key}", decodedRegisterName)
        if(need_int): return int(handle.get(), base=16)
        else: return handle.get()

    def peripheral_decoded_register_write(decodedRegisterName, data_to_write):
        bit_depth = register_decoding["ETROC2"]["Register Blocks"]["Peripheral Config"][decodedRegisterName]["bits"]
        handle = chip.get_decoded_display_var("ETROC2", "Peripheral Config", decodedRegisterName)
        chip.read_decoded_value("ETROC2", "Peripheral Config", decodedRegisterName)
        if len(data_to_write)!=bit_depth: print("Binary data_to_write is of incorrect length for",decodedRegisterName, "with bit depth", bit_depth)
        data_hex_modified = hex(int(data_to_write, base=2))
        if(bit_depth>1): handle.set(data_hex_modified)
        elif(bit_depth==1): handle.set(data_to_write)
        else: print(decodedRegisterName, "!!!ERROR!!! Bit depth <1, how did we get here...")
        chip.write_decoded_value("ETROC2", "Peripheral Config", decodedRegisterName)

    def peripheral_decoded_register_read(decodedRegisterName, key, need_int=False):
        handle = chip.get_decoded_display_var("ETROC2", f"Peripheral {key}", decodedRegisterName)
        chip.read_decoded_value("ETROC2", f"Peripheral {key}", decodedRegisterName)
        if(need_int): return int(handle.get(), base=16)
        else: return handle.get()

    ## Pixel ID Check
    Failure_map = np.zeros((16,16))
    data = []
    row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
    column_indexer_handle,_,_ = chip.get_indexer("column")
    for row in range(16):
        for col in range(16):
            column_indexer_handle.set(col)
            row_indexer_handle.set(row)
            fetched_row = pixel_decoded_register_read("PixelID-Row", "Status", need_int=True)
            fetched_col = pixel_decoded_register_read("PixelID-Col", "Status", need_int=True)
            data += [{
                'col': col,
                'row': row,
                'fetched_col': fetched_col,
                'fetched_row': fetched_row,
                'timestamp': datetime.datetime.now(),
                'chip_name': chip_name,
            }]
            if(row!=fetched_row or col!=fetched_col):
                print("Fail!", row, col, fetched_row, fetched_col)
                Failure_map[15-row,15-col] = 1

    Failure_df = pandas.DataFrame(data = data)

    # fig = plt.figure(dpi=75, figsize=(8,8))
    # gs = fig.add_gridspec(1,1)

    # ax0 = fig.add_subplot(gs[0,0])
    # ax0.set_title("Pixel ID Failure Map")
    # img0 = ax0.imshow(Failure_map, interpolation='none')
    # ax0.set_aspect("equal")
    # ax0.get_yaxis().set_visible(False)
    # ax0.get_xaxis().set_visible(False)
    # divider = make_axes_locatable(ax0)
    # cax = divider.append_axes('right', size="5%", pad=0.05)
    # fig.colorbar(img0, cax=cax, orientation="vertical")
    # plt.show()

    if do_detailed:
        check_I2C(
            chip = chip,
            chip_name = chip_name,
            i2c_log_dir = i2c_log_dir,
            file_comment = "Start",
        )

    ## Set Peripheral Registers
    peripheral_decoded_register_write("EFuse_Prog", format(0x00017f0f, '032b'))
    peripheral_decoded_register_write("singlePort", '1')
    peripheral_decoded_register_write("serRateLeft", '00')
    peripheral_decoded_register_write("serRateRight", '00')
    peripheral_decoded_register_write("onChipL1AConf", '00')
    peripheral_decoded_register_write("PLL_ENABLEPLL", '1')
    peripheral_decoded_register_write("chargeInjectionDelay", format(0x0a, '05b'))
    peripheral_decoded_register_write("triggerGranularity", format(0x01, '03b')) # only for trigger bit

    if do_detailed:
        ## Extra checking of peripherals (useful for debugging)
        decodedRegisterNames = list(register_decoding["ETROC2"]["Register Blocks"]["Peripheral Config"].keys())
        for decodedRegisterName in decodedRegisterNames:
            handle = chip.get_decoded_display_var("ETROC2", "Peripheral Config", decodedRegisterName)
            chip.read_decoded_value("ETROC2", "Peripheral Config", decodedRegisterName)
            data_str = handle.get()
            data_int = int(data_str, base=16)
            data_bin = format(data_int, f'0{register_decoding["ETROC2"]["Register Blocks"]["Peripheral Config"][decodedRegisterName]["bits"]}b')
            data_hex = hex(int(data_bin, base=2))
            print(f"{decodedRegisterName:25}", f"{data_str:10}", f"{data_hex:10}", f"{data_int:10}", f"{data_bin:32}", register_decoding["ETROC2"]["Register Blocks"]["Peripheral Config"][decodedRegisterName]["bits"])

        decodedRegisterNames = list(register_decoding["ETROC2"]["Register Blocks"]["Peripheral Status"].keys())
        for decodedRegisterName in decodedRegisterNames:
            handle = chip.get_decoded_display_var("ETROC2", "Peripheral Status", decodedRegisterName)
            chip.read_decoded_value("ETROC2", "Peripheral Status", decodedRegisterName)
            data_str = handle.get()
            data_int = int(data_str, base=16)
            data_bin = format(data_int, f'0{register_decoding["ETROC2"]["Register Blocks"]["Peripheral Status"][decodedRegisterName]["bits"]}b')
            data_hex = hex(int(data_bin, base=2))
            print(f"{decodedRegisterName:25}", f"{data_str:10}", f"{data_hex:10}", f"{data_int:10}", f"{data_bin:32}", register_decoding["ETROC2"]["Register Blocks"]["Peripheral Status"][decodedRegisterName]["bits"])

    ## Force Re-align of the FC
    # Run this when you see inconsistent BCID in your data, even though you expect to see the same numbers for each cycle

    print(peripheral_decoded_register_read("asyAlignFastcommand", "Config"))
    peripheral_decoded_register_write("asyAlignFastcommand", "1")
    peripheral_decoded_register_write("asyAlignFastcommand", "0")

    ## Automatic threshold calibration
    BL_map_THCal = np.zeros((16,16))
    NW_map_THCal = np.zeros((16,16))

    row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
    column_indexer_handle,_,_ = chip.get_indexer("column")
    data = []
    # Loop for threshold calibration
    for row in tqdm(range(16), desc=" row", position=0):
        for col in tqdm(range(16), desc=" col", position=1, leave=False):
            column_indexer_handle.set(col)
            row_indexer_handle.set(row)
            # Maybe required to make this work
            # pixel_decoded_register_write("enable_TDC", "0")
            # pixel_decoded_register_write("testMode_TDC", "0")
            # Enable THCal clock and buffer, disable bypass
            pixel_decoded_register_write("CLKEn_THCal", "1")
            pixel_decoded_register_write("BufEn_THCal", "1")
            pixel_decoded_register_write("Bypass_THCal", "0")
            pixel_decoded_register_write("TH_offset", format(0x0c, '06b'))
            # Reset the calibration block (active low)
            pixel_decoded_register_write("RSTn_THCal", "0")
            pixel_decoded_register_write("RSTn_THCal", "1")
            # Start and Stop the calibration, (25ns x 2**15 ~ 800 us, ACCumulator max is 2**15)
            pixel_decoded_register_write("ScanStart_THCal", "1")
            pixel_decoded_register_write("ScanStart_THCal", "0")
            # Check the calibration done correctly
            if(pixel_decoded_register_read("ScanDone", "Status")!="1"): print("!!!ERROR!!! Scan not done!!!")
            BL_map_THCal[row, col] = pixel_decoded_register_read("BL", "Status", need_int=True)
            NW_map_THCal[row, col] = pixel_decoded_register_read("NW", "Status", need_int=True)
            data += [{
                'col': col,
                'row': row,
                'baseline': BL_map_THCal[row, col],
                'noise_width': NW_map_THCal[row, col],
                'timestamp': datetime.datetime.now(),
                'chip_name': chip_name,
            }]
            # Disable clock and buffer before charge injection
            pixel_decoded_register_write("CLKEn_THCal", "0")
            pixel_decoded_register_write("BufEn_THCal", "0")

            pixel_decoded_register_write("Bypass_THCal", "1")
            pixel_decoded_register_write("DAC", format(1023, '010b'))
            # Set Charge Inj Q to 15 fC
            pixel_decoded_register_write("QSel", format(0x0e, '05b'))

            time.sleep(0.1)

    BL_df = pandas.DataFrame(data = data)

    fig = plt.figure(dpi=200, figsize=(10,10))
    gs = fig.add_gridspec(1,2)

    ax0 = fig.add_subplot(gs[0,0])
    # ax0.set_title("BL (DAC LSB), "+chip_figtitle, size=8)
    img0 = ax0.imshow(BL_map_THCal, interpolation='none')
    ax0.set_aspect("equal")
    ax0.invert_xaxis()
    ax0.invert_yaxis()
    plt.xticks(range(16), range(16), rotation="vertical")
    plt.yticks(range(16), range(16))
    divider = make_axes_locatable(ax0)
    cax = divider.append_axes('right', size="5%", pad=0.05)
    fig.colorbar(img0, cax=cax, orientation="vertical")

    ax1 = fig.add_subplot(gs[0,1])
    # ax1.set_title("NW (DAC LSB), "+chip_figtitle, size=8)
    img1 = ax1.imshow(NW_map_THCal, interpolation='none')
    ax1.set_aspect("equal")
    ax1.invert_xaxis()
    ax1.invert_yaxis()
    plt.xticks(range(16), range(16), rotation="vertical")
    plt.yticks(range(16), range(16))
    divider = make_axes_locatable(ax1)
    cax = divider.append_axes('right', size="5%", pad=0.05)
    fig.colorbar(img1, cax=cax, orientation="vertical")

    for x in range(16):
        for y in range(16):
            # if(BL_map_THCal.T[x,y]==0): continue
            ax0.text(x,y,f"{BL_map_THCal.T[x,y]:.0f}", c="white", size=5, rotation=45, fontweight="bold", ha="center", va="center")
            ax1.text(x,y,f"{NW_map_THCal.T[x,y]:.0f}", c="white", size=5, rotation=45, fontweight="bold", ha="center", va="center")
    plt.savefig(fig_path+"/BL_NW_"+chip_figname+"_"+datetime.datetime.now().isoformat()+".png")

    ### Store BL, NW dataframe for later use
    outdir = Path('../ETROC-Data')
    outdir = outdir / (datetime.date.today().isoformat() + '_Array_Test_Results')
    outdir.mkdir(exist_ok=True)
    outfile = outdir / (chip_name+TID_str+"_BaselineAt_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + ".csv")
    BL_df.to_csv(outfile, index=False)
    failOut = outdir / (chip_name+TID_str+"_FailedPixelsAt_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + ".csv")
    Failure_df.to_csv(failOut, index=False)

    ### Store BL, NW dataframe in database
    note = TID_str + '_' + chip_name
    if run_name_extra is not None:
        note = run_name_extra + '_' + TID_str + '_' + chip_name
    new_columns = {
        'note': f'{note}',
    }

    for col in new_columns:
        BL_df[col] = new_columns[col]

    outdir = Path('../ETROC-History')
    outfile = outdir / 'BaselineHistory.sqlite'
    failOut = outdir / 'FailedPixelHistory.sqlite'

    init_cmd = [
        'cd ' + str(outdir.resolve()),
        'git stash -u',
        'git pull',
    ]
    end_cmd = [
        'cd ' + str(outdir.resolve()),
        'git add BaselineHistory.sqlite',
        'git add FailedPixelHistory.sqlite',
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

    print(p.stdout.read())

    with sqlite3.connect(outfile) as sqlconn:
        BL_df.to_sql('baselines', sqlconn, if_exists='append', index=False)

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

    p.stdin.close()

    print(p.stdout.read())


    ## Disable all pixels
    row_indexer_handle,_,_ = chip.get_indexer("row")
    column_indexer_handle,_,_ = chip.get_indexer("column")
    column_indexer_handle.set(0)
    row_indexer_handle.set(0)

    chip_broadcast_decoded_register_write(chip, "disDataReadout", "1")
    chip_broadcast_decoded_register_write(chip, "QInjEn", "0")
    chip_broadcast_decoded_register_write(chip, "disTrigPath", "1")

    if only_baseline:
        return

    # Release the maximum and minimum range for trigger and data
    chip_broadcast_decoded_register_write(chip, "upperTOATrig", format(0x3ff, '010b'))
    chip_broadcast_decoded_register_write(chip, "lowerTOATrig", format(0x000, '010b'))
    chip_broadcast_decoded_register_write(chip, "upperTOTTrig", format(0x1ff, '09b'))
    chip_broadcast_decoded_register_write(chip, "lowerTOTTrig", format(0x000, '09b'))
    chip_broadcast_decoded_register_write(chip, "upperCalTrig", format(0x3ff, '010b'))
    chip_broadcast_decoded_register_write(chip, "lowerCalTrig", format(0x000, '010b'))
    chip_broadcast_decoded_register_write(chip, "upperTOA", format(0x3ff, '010b'))
    chip_broadcast_decoded_register_write(chip, "lowerTOA", format(0x000, '010b'))
    chip_broadcast_decoded_register_write(chip, "upperTOT", format(0x1ff, '09b'))
    chip_broadcast_decoded_register_write(chip, "lowerTOT", format(0x000, '09b'))
    chip_broadcast_decoded_register_write(chip, "upperCal", format(0x3ff, '010b'))
    chip_broadcast_decoded_register_write(chip, "lowerCal", format(0x000, '010b'))


    # Run DAQ scanning by row to study multiple pixels TOT and TOA
    ### Define DAQ function
    def run_daq(timePerPixel, deadTime, dirname):

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

        IPC_queue.put('start L1A trigger bit')
        while not IPC_queue.empty():
            pass

        time.sleep(time_per_pixel)
        IPC_queue.put('stop L1A trigger bit')

        time.sleep(1)
        IPC_queue.put('stop DAQ')
        while not IPC_queue.empty():
            pass

        IPC_queue.put('allow threads to exit')

        process.join()

    ### One time run to set fpga firmware
    parser = run_script.getOptionParser()
    (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {fpga_ip} -t 10 -o CanBeRemoved -v -w --compressed_translation -s 0x000C -p 0x000f -d 0x0800 --clear_fifo".split())
    IPC_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_Start_LEDs'))
    process.start()

    IPC_queue.put('start L1A trigger bit')
    while not IPC_queue.empty():
        pass
    time.sleep(5)
    IPC_queue.put('stop DAQ')
    IPC_queue.put('stop L1A trigger bit')
    while not IPC_queue.empty():
        pass
    IPC_queue.put('allow threads to exit')
    process.join()

    if do_row_scan:
        QInjEns = [10, 15, 20]
        # Make sure all pixels are in a well known initial state
        chip_broadcast_decoded_register_write(chip, "disDataReadout", "1")
        chip_broadcast_decoded_register_write(chip, "QInjEn", "0")
        chip_broadcast_decoded_register_write(chip, "disTrigPath", "1")

        ### Actual DAQ run
        for QInj in QInjEns:
            print(f'Taking data for QInj: {QInj}')
            for i in range(16):
                # Disable pixels for clean start
                row_indexer_handle,_,_ = chip.get_indexer("row")
                column_indexer_handle,_,_ = chip.get_indexer("column")
                column_indexer_handle.set(0)
                row_indexer_handle.set(0)

                scan_list = list(zip(np.full(16, i), np.arange(16)))
                print(scan_list)

                for row, col in scan_list:
                    column_indexer_handle.set(col)
                    row_indexer_handle.set(row)

                    print(f"Enabling Pixel ({row},{col})")

                    pixel_decoded_register_write("Bypass_THCal", "0")               # Bypass threshold calibration -> manual DAC setting
                    pixel_decoded_register_write("QSel", format(QInj, '05b'))       # Ensure we inject 0 fC of charge
                    pixel_decoded_register_write("TH_offset", format(0x0c, '06b'))  # Offset used to add to the auto BL for real triggering
                    pixel_decoded_register_write("disDataReadout", "0")             # ENable readout
                    pixel_decoded_register_write("QInjEn", "1")                     # ENable charge injection for the selected pixel
                    pixel_decoded_register_write("L1Adelay", format(0x01f5, '09b')) # Change L1A delay - circular buffer in ETROC2 pixel
                    pixel_decoded_register_write("disTrigPath", "0")                # Enable trigger path

                run_name = f'TID_testing_candidate_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}_Q{QInj}_{chip_name.replace("_","")}_'+TID_str+f'_R{str(i)}_CX'
                if run_name_extra is not None:
                    run_name = f'TID_testing_candidate_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}_Q{QInj}_{run_name_extra}_{chip_name.replace("_","")}_'+TID_str+f'_R{str(i)}_CX'
                run_daq(10, 6, run_name)

                for row, col in scan_list:
                    column_indexer_handle.set(col)
                    row_indexer_handle.set(row)

                    print(f"Disabling Pixel ({row},{col})")

                    pixel_decoded_register_write("Bypass_THCal", "1")               # Bypass threshold calibration -> manual DAC setting
                    pixel_decoded_register_write("disDataReadout", "1")
                    pixel_decoded_register_write("QInjEn", "0")
                    pixel_decoded_register_write("disTrigPath", "1")

        chip_broadcast_decoded_register_write(chip, "disDataReadout", "1")
        chip_broadcast_decoded_register_write(chip, "QInjEn", "0")
        chip_broadcast_decoded_register_write(chip, "disTrigPath", "1")

        if do_detailed:
            check_I2C(
                chip = chip,
                chip_name = chip_name,
                i2c_log_dir = i2c_log_dir,
                file_comment = "AfterRowDAQ",
            )

    # Qinj S Curve Scan
    ## Define Pixel for ACC and DAC scan
    DAC_row_list = [15, 0, 0, 0]
    DAC_col_list = [7, 15, 7, 0]
    DAC_row_list = [0,  0, 3,  3, 15, 15]
    DAC_col_list = [2, 10, 2, 10,  2, 10]
    DAC_scan_list = list(zip(DAC_col_list, DAC_row_list))
    print(DAC_scan_list)

    ## Simple Scan To Measure The Noise
    thresholds = np.arange(-10,10,1) # relative to BL
    # thresholds = np.arange(0,1,1) # BL only
    scan_name = "E2_testing_VRef_SCurve_Noise_"+TID_str
    if run_name_extra is not None:
        scan_name = f"E2_testing_VRef_SCurve_Noise_{run_name_extra}_{TID_str}"
    fpga_time = 3
    QInj = 0

    row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
    column_indexer_handle,_,_ = chip.get_indexer("column")

    today = datetime.date.today()
    todaystr = "../ETROC-Data/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)

    data = []

    # Add dummy data taking for the FPGA to have time to align
    DAC_row_list_with_dummy = [-1] + DAC_row_list
    DAC_col_list_with_dummy = [-1] + DAC_col_list

    # Loop for enable/disable charge injection per pixel (single!!!)
    for index, row, col in zip(tqdm(range(len(DAC_row_list_with_dummy)), desc=f'Pixel Loop', leave=True), DAC_row_list_with_dummy, DAC_col_list_with_dummy):
        print("Pixel:",col,row)
        if col == -1 and row == -1:
            row = DAC_row_list_with_dummy[1]
            col = DAC_col_list_with_dummy[1]

        column_indexer_handle.set(col)
        row_indexer_handle.set(row)
        # Ensure charge injection is disabled
        pixel_decoded_register_write("disDataReadout", "0")
        pixel_decoded_register_write("QInjEn", "0")
        pixel_decoded_register_write("disTrigPath", "0")

        # Bypass Cal Threshold
        pixel_decoded_register_write("Bypass_THCal", "1")

        # start FPGA state
        threshold_name = scan_name+f'_Pixel_C{col}_R{row}_Noise_HVoff_pf_hits'
        (options, args) = parser.parse_args(args=f"--useIPC --hostname {fpga_ip} -o {threshold_name} -v -w --reset_till_trigger_linked -s 0x000C -p 0x000f -d 0x0800 -c 0x0001 --fpga_data_time_limit 3 --fpga_data --check_trigger_link_at_end --nodaq --clear_fifo".split())
        IPC_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_link'))
        process.start()
        process.join()

        for DAC in tqdm(thresholds[:], desc=f'DAC Loop for Pixel {col},{row}', leave=False):
            DAC = int(DAC+BL_map_THCal[row][col])
            print("DAC", DAC)

            # Set the DAC v, Qinj {Qinj}fCalue to the value being scanned
            pixel_decoded_register_write("DAC", format(DAC, '010b'))

            (options, args) = parser.parse_args(args=f"--useIPC --hostname {fpga_ip} -o {threshold_name} -v --reset_till_trigger_linked -s 0x000C -p 0x000f -d 0x0800 -c 0x0001 --fpga_data_time_limit {int(fpga_time)} --fpga_data --check_trigger_link_at_end --nodaq --DAC_Val {int(DAC)}".split())
            IPC_queue = multiprocessing.Queue()
            process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_Noise_{QInj}_{DAC}'))
            process.start()
            process.join()

        # Disable charge injection
        pixel_decoded_register_write("QInjEn", "0")
        pixel_decoded_register_write("disDataReadout", "1")
        pixel_decoded_register_write("disTrigPath", "1")
        pixel_decoded_register_write("DAC", format(1023, '010b'))

        if index == 0:
            time.sleep(5)

    if do_detailed:
        check_I2C(
            chip = chip,
            chip_name = chip_name,
            i2c_log_dir = i2c_log_dir,
            file_comment = "AfterSinglePixelNoiseScan",
        )

    sCurve_df = pandas.DataFrame(data=data)

    outdir = Path('../ETROC-Data')
    outdir = outdir / (datetime.date.today().isoformat() + '_Array_Test_Results')
    outdir.mkdir(exist_ok=True)
    outfile = outdir / (scan_name + "_at_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + ".csv")
    sCurve_df.to_csv(outfile, index=False)

    ### Choose Pixel To Plot Noise To Check Output
    row = 0
    col = 0
    DAC_plot_row_list = [row]
    DAC_plot_col_list = [col]

    root = '../ETROC-Data'
    file_pattern = "*FPGA_Data.dat"
    BL = int(BL_map_THCal[row][col])
    hitmap_full_Scurve = {row:{col:{thr+BL:0 for thr in thresholds} for col in range(16)} for row in range(16)}
    sum_data_hitmap_full_Scurve = {row:{col:{thr+BL:0 for thr in thresholds} for col in range(16)} for row in range(16)}
    sum2_data_hitmap_full_Scurve = {row:{col:{thr+BL:0 for thr in thresholds} for col in range(16)} for row in range(16)}
    for index, row, col in zip((range(len(DAC_plot_row_list))), DAC_plot_row_list, DAC_plot_col_list):
        path_pattern = f"*{today.isoformat()}_Array_Test_Results/E2_testing_VRef_SCurve_Noise_{TID_str}_Pixel_C{col}_R{row}_Noise_HVoff_pf_hits"
        if run_name_extra is not None:
            path_pattern = f"*{today.isoformat()}_Array_Test_Results/E2_testing_VRef_SCurve_Noise_{run_name_extra}_{TID_str}_Pixel_C{col}_R{row}_Noise_HVoff_pf_hits"
        file_list = []
        for path, subdirs, files in os.walk(root):
            if not fnmatch(path, path_pattern): continue
            for name in files:
                pass
                if fnmatch(name, file_pattern):
                    file_list.append(os.path.join(path, name))
                    print(file_list[-1])
        total_files = len(file_list)
        for file_index, file_name in enumerate(file_list):
            print(f"{file_index+1}/{total_files}")
            with open(file_name) as infile:
                for line in infile:
                    text_list = line.split(',')
                    FPGA_state = text_list[0]
                    FPGA_data = int(text_list[3])
                    triggerbit_data = int(text_list[5])
                    DAC = int(text_list[6])
                    if DAC == -1: continue
                    print(DAC)
                    sum_data_hitmap_full_Scurve[row][col][DAC] += triggerbit_data
                    hitmap_full_Scurve[row][col][DAC] += 1
                    print(sum_data_hitmap_full_Scurve[row][col][DAC])
                    print(hitmap_full_Scurve[row][col][DAC])

    data_mean = {row:{col:{thr+BL:0 for thr in thresholds} for col in range(16)} for row in range(16)}
    for index, row, col in zip((range(len(DAC_plot_row_list))), DAC_plot_row_list, DAC_plot_col_list):
        for DAC in (thresholds):
            DAC = int(DAC)+BL
            print(DAC)
            print(sum_data_hitmap_full_Scurve[row][col][DAC])
            print(hitmap_full_Scurve[row][col][DAC])
            if(hitmap_full_Scurve[row][col][DAC]==0):
                data_mean[row][col][DAC] = 0
                continue
            data_mean[row][col][DAC] = sum_data_hitmap_full_Scurve[row][col][DAC]/hitmap_full_Scurve[row][col][DAC]

    fig = plt.figure(dpi=200, figsize=(8,4.5))
    gs = fig.add_gridspec(1,1)
    u_cl = np.sort(np.unique(DAC_plot_col_list))
    u_rl = np.sort(np.unique(DAC_plot_row_list))
    for ri,row in enumerate(u_rl):
        for ci,col in enumerate(u_cl):
            ax0 = fig.add_subplot(gs[len(u_rl)-ri-1,len(u_cl)-ci-1])
            ax0.axvline(BL_map_THCal[row][col], color='k', label="THCal BL", lw=0.7)
            ax0.axvline(BL_map_THCal[row][col]+NW_map_THCal[row][col], color='k', ls='--', label="THCal NW", lw=0.7)
            ax0.axvline(BL_map_THCal[row][col]-NW_map_THCal[row][col], color='k', ls='--', lw=0.7)
            ax0.plot([thr+BL for thr in thresholds], data_mean[row][col].values(), '.-', color='#1f78b4', label=f"0 fC",lw=0.5,markersize=2)
            ax0.set_xlabel("DAC Value [decimal]")
            ax0.set_ylabel("Data Counts [decimal]")
            # ax0.text(0.7, 0.8, f"Pixel {row},{col}", transform=ax0.transAxes)
            plt.legend(loc="center right")
            plt.yscale("log")
        plt.title(f"{chip_figtitle}, Pixel ({row},{col}) Full S-Curve")
        plt.tight_layout()
    plt.savefig(fig_path+"/Full_S-Curve_"+chip_figname+"_"+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")+".png")

    if do_knee_finding:
        ## DAC scan using counter
        ### Define DACs for scanning near BL
        # relative to BL
        min_threshold = -10
        BL_scan_max = 10
        BL_scan_step = 2

        BL_thresholds = {
            1: np.arange(min_threshold,  min_threshold + BL_scan_max, BL_scan_step),
            5: np.arange(min_threshold,  min_threshold + BL_scan_max, BL_scan_step),
            6: np.arange(min_threshold,  min_threshold + BL_scan_max, BL_scan_step),
            8: np.arange(min_threshold,  min_threshold + BL_scan_max, BL_scan_step),
            10: np.arange(min_threshold, min_threshold + BL_scan_max, BL_scan_step),
            12: np.arange(min_threshold, min_threshold + BL_scan_max, BL_scan_step),
            15: np.arange(min_threshold, min_threshold + BL_scan_max, BL_scan_step),
            17: np.arange(min_threshold, min_threshold + BL_scan_max, BL_scan_step),
            20: np.arange(min_threshold, min_threshold + BL_scan_max, BL_scan_step),
            22: np.arange(min_threshold, min_threshold + BL_scan_max, BL_scan_step),
            25: np.arange(min_threshold, min_threshold + BL_scan_max, BL_scan_step),
            27: np.arange(min_threshold, min_threshold + BL_scan_max, BL_scan_step),
            30: np.arange(min_threshold, min_threshold + BL_scan_max, BL_scan_step),
        }

        ### Define DACs for scanning Pedestal
        # relative to BL
        min_threshold = BL_scan_max
        pedestal_scan_step = 2

        pedestal_thresholds = {
            1: np.arange(min_threshold,  min_threshold + 10, pedestal_scan_step),
            5: np.arange(min_threshold,  min_threshold + 10, pedestal_scan_step),
            6: np.arange(min_threshold,  min_threshold + 10, pedestal_scan_step),
            8: np.arange(min_threshold,  min_threshold + 40, pedestal_scan_step),
            10: np.arange(min_threshold, min_threshold + 70, pedestal_scan_step),
            12: np.arange(min_threshold, min_threshold + 90, pedestal_scan_step),
            15: np.arange(min_threshold, min_threshold + 120, pedestal_scan_step),
            17: np.arange(min_threshold, min_threshold + 130, pedestal_scan_step),
            20: np.arange(min_threshold, min_threshold + 140, pedestal_scan_step),
            22: np.arange(min_threshold, min_threshold + 170, pedestal_scan_step),
            25: np.arange(min_threshold, min_threshold + 200, pedestal_scan_step),
            27: np.arange(min_threshold, min_threshold + 250, pedestal_scan_step),
            30: np.arange(min_threshold, min_threshold + 280, pedestal_scan_step),
        }

        ### Combine Thresholds
        thresholds = {}
        for QInj in BL_thresholds:
            thresholds[QInj] = list(BL_thresholds[QInj])
            for DAC in pedestal_thresholds[QInj]:
                thresholds[QInj].append(DAC)

        ### Define Charges
        # Full Charges
        # QInjEns = [5, 6, 8, 10, 12, 15, 17, 20, 22, 25, 27, 30]
        # Recommend for TID
        QInjEns = [8, 10, 15, 22, 27]
        # Single
        # QInjEns = [8]
        num_thr = 0
        for QInj in QInjEns:
            num_thr += len(thresholds[QInj])
        num_pix = len(DAC_scan_list)
        print(f"Will scan {num_thr} thresholds and {num_pix} pixels")
        print(f"Expected scan time is {num_thr*num_pix*5./60.} minutes")

        ### Run QInj+DAC Scan
        scan_name = "E2_testing_VRef_SCurve_"+TID_str
        if run_name_extra is not None:
            scan_name = f"E2_testing_VRef_SCurve_{run_name_extra}_{TID_str}"
        fpga_time = 3

        row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
        column_indexer_handle,_,_ = chip.get_indexer("column")

        today = datetime.date.today()
        todaystr = "../ETROC-Data/" + today.isoformat() + "_Array_Test_Results/"
        base_dir = Path(todaystr)
        base_dir.mkdir(exist_ok=True)

        data = {}
        knee_DAC = {}

        # Loop for enable/disable charge injection per pixel (single!!!)
        for index, row, col in zip(tqdm(range(len(DAC_row_list)), desc=f'Pixel Loop', leave=True), DAC_row_list, DAC_col_list):
            if (row,col) not in data:
                data[(row, col)] = {}
                knee_DAC[(row, col)] = {}
            for QInj in tqdm(QInjEns, desc=f'Charge Loop for Pixel {col},{row}', leave=False):
                extra_name = f'{TID_str}'
                if run_name_extra is not None:
                    extra_name = f"{run_name_extra}_{TID_str}"

                triggers_n_knee = binary_search_DAC_scan(
                    QInj,
                    BL_map_THCal[row][col],
                    10,
                    chip,
                    row,
                    col,
                    extra_name,
                    fpga_ip,
                    fpga_time,
                    baseline_step=1,
                )

                data[(row, col)][QInj] = triggers_n_knee[0]
                knee_DAC[(row, col)][QInj] = triggers_n_knee[1]


        if do_detailed:
            check_I2C(
                chip = chip,
                chip_name = chip_name,
                i2c_log_dir = i2c_log_dir,
                file_comment = "AfterQInjDACScan",
            )


        if do_full_scan:
            overscan_DAC = 5
            underscan_DAC = 30
            step_DAC = 1
            row_indexer_handle,_,_ = chip.get_indexer("row")
            column_indexer_handle,_,_ = chip.get_indexer("column")
            column_indexer_handle.set(0)
            row_indexer_handle.set(0)

            # Disable all pixels for clean start
            chip_broadcast_decoded_register_write(chip, "disDataReadout", "1")
            chip_broadcast_decoded_register_write(chip, "QInjEn", "0")
            chip_broadcast_decoded_register_write(chip, "disTrigPath", "1")

            for index, row, col in zip(tqdm(range(len(DAC_row_list)), desc=f'Pixel Loop', leave=True), DAC_row_list, DAC_col_list):
                pixel_baseline = BL_map_THCal[row][col]

                column_indexer_handle.set(col)
                row_indexer_handle.set(row)
                pixel_decoded_register_write("Bypass_THCal", "1")               # Bypass threshold calibration -> manual DAC setting
                pixel_decoded_register_write("L1Adelay", format(0x01f5, '09b')) # Change L1A delay - circular buffer in ETROC2 pixel

                pixel_decoded_register_write("disDataReadout", "0")             # ENable readout
                pixel_decoded_register_write("disTrigPath", "0")                # Enable trigger path

                for QInj in tqdm(QInjEns, desc=f'Charge Loop for Pixel {col},{row}', leave=False):
                    if knee_DAC[(row, col)][QInj] is not None:
                        pixel_max_dac = knee_DAC[(row, col)][QInj] + overscan_DAC
                    else:
                        print(f"There was a problem in the knee finding and no knee was found for pixel {row} {col} for QInj {QInj}, using max range instead.")
                        pixel_max_dac = 1023

                    pixel_min_dac = int(pixel_baseline) - underscan_DAC

                    pixel_decoded_register_write("QSel", format(QInj, '05b'))       # Ensure we inject selected charge

                    for DAC in range(int(pixel_min_dac), int(pixel_max_dac + 1), step_DAC):
                        print(f"Enabling Pixel ({row},{col}) with charge {QInj} fC and DAC {DAC}")

                        pixel_decoded_register_write("DAC", format(DAC, '010b'))

                        run_name = f'TID_FullScan_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}_DAC{DAC}_Q{QInj}_{chip_name.replace("_","")}_'+TID_str+f'_R{row}_C{col}'
                        if run_name_extra is not None:
                            run_name = f'TID_FullScan_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}_DAC{DAC}_Q{QInj}_{run_name_extra}_{chip_name.replace("_","")}_'+TID_str+f'_R{row}_C{col}'

                        pixel_decoded_register_write("QInjEn", "1")                     # ENable charge injection for the selected pixel
                        run_daq(10, 4, run_name)
                        pixel_decoded_register_write("QInjEn", "0")

                # Disable pixel after taking data to make sure everything is off
                pixel_decoded_register_write("disDataReadout", "1")
                pixel_decoded_register_write("disTrigPath", "1")
                pixel_decoded_register_write("DAC", format(1023, '010b'))

                pixel_decoded_register_write("Bypass_THCal", "0")               # Bypass threshold calibration -> manual DAC setting

            if do_detailed:
                check_I2C(
                    chip = chip,
                    chip_name = chip_name,
                    i2c_log_dir = i2c_log_dir,
                    file_comment = "AfterFullScan",
                )

        ### Choose Pixel To Plot Full Scan Output

        # DAC_row_list = [15, 0, 0, 0]
        # DAC_col_list = [7, 15, 7, 0]
        row = 0
        col = 0

        # data[(row, col)][QInj][DAC] = triggers

        colors = ['#e41a1c','#377eb8','#4daf4a','#984ea3','#ff7f00']

        fig, ax0 = plt.subplots(dpi=200, figsize=(8,4.5))
        ax0.axvline(BL_map_THCal[row][col], color='k', label="THCal BL", lw=0.7)
        ax0.axvline(BL_map_THCal[row][col]+NW_map_THCal[row][col], color='k', ls='--', label="THCal NW", lw=0.7)
        ax0.axvline(BL_map_THCal[row][col]-NW_map_THCal[row][col], color='k', ls='--', lw=0.7)

        for i, qinj in enumerate(QInjEns[0:]):
            x = list(data[(row,col)][qinj].keys())
            y = [data[(row,col)][qinj][dac] for dac in x]
            ax0.plot(x, y, '.-', color=colors[i], label=f"{qinj} fC",lw=0.5,markersize=2)

        ax0.set_xlabel("DAC Value [decimal]")
        ax0.set_ylabel("Trigger Counts [decimal]")
        plt.legend(loc="upper right")
        plt.yscale("log")
        plt.title(f"{chip_figtitle}, Pixel ({row},{col}) Full S-Curve")
        plt.tight_layout()
        plt.savefig(fig_path+"/Full_S-Curve_"+chip_figname+"_"+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")+".png")

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
        '--TIDStr',
        metavar = 'NAME',
        type = str,
        help = 'TID string - no special chars',
        required = True,
        dest = 'TID_str',
    )
    parser.add_argument(
        '-l',
        '--infiniteLoop',
        help = 'Do infinite loop',
        action = 'store_true',
        dest = 'infinite_loop',
    )
    parser.add_argument(
        '-d',
        '--doDetailed',
        help = 'Do detailed',
        action = 'store_true',
        dest = 'do_detailed',
    )
    parser.add_argument(
        '-k',
        '--doKneeFinding',
        help = 'Do knee finding',
        action = 'store_true',
        dest = 'do_knee_finding',
    )
    parser.add_argument(
        '-f',
        '--doFullScan',
        help = 'Do full scan, taking regular data, of QInj and DAC threshold using the knee position found with the knee finding. i.e. this scan is only done if knee finding is enabled',
        action = 'store_true',
        dest = 'do_full_scan',
    )
    parser.add_argument(
        '-r',
        '--doRowScan',
        help = 'Do row scan, taking regular data for a full row at a time',
        action = 'store_true',
        dest = 'do_row_scan',
    )
    parser.add_argument(
        '-b',
        '--onlyBaseline',
        help = 'Only do the baseline measurement, skip all other measurements',
        action = 'store_true',
        dest = 'only_baseline',
    )
    parser.add_argument(
        '--minV',
        metavar = 'VOLTAGE',
        type = float,
        help = 'Minimum voltage for V scan, V scan only done if both max and min are set',
        default = None,
        dest = 'minV',
    )
    parser.add_argument(
        '--maxV',
        metavar = 'VOLTAGE',
        type = float,
        help = 'Maximum voltage for V scan, V scan only done if both max and min are set',
        default = None,
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
        '--reverseVScan',
        help = 'Do the V scan from higher voltage values to lower voltage values, instead of the default low to high.',
        action = 'store_true',
        dest = 'reverseVScan',
    )

    args = parser.parse_args()

    count = 0
    while True:
        run_str = f"Run{count}"

        if args.maxV is not None and args.minV is not None:
            from read_current import DeviceMeasurements
            delay_time = 5
            powerDevices = DeviceMeasurements(outdir=Path('.'), interval=delay_time)
            powerDevices.find_devices()
            powerDevices.turn_on()

            def signal_handler(sig, frame):
                print("Exiting gracefully")

                powerDevices.turn_off()

                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)

            do_analog = False
            do_digital = False
            voltage_str = "None"
            if args.scanTypeV == 'Digital':
                do_digital = True
                voltage_str = "VD"
            elif args.scanTypeV == 'Analog':
                do_analog = True
                voltage_str = "VA"
            elif args.scanTypeV == 'Both':
                do_analog = True
                do_digital = True
                voltage_str = "V"
            else:
                raise RuntimeError("Unknown scanTypeV selected")

            voltage_list = list(np.linspace(args.minV, args.maxV, (args.maxV - args.minV)/args.stepV))
            if args.reverseVScan:
                voltage_list.reverse()

            for voltage in voltage_list:
                if do_analog:
                    powerDevices.set_power_V1(voltage)
                if do_digital:
                    powerDevices.set_power_V2(voltage)
                run_TID(
                    chip_name = args.chip_name,
                    TID_str = args.TID_str,
                    do_detailed = args.do_detailed,
                    run_name_extra = f"{voltage_str}{voltage}_{run_str}",
                    do_knee_finding = args.do_knee_finding,
                    do_full_scan = args.do_full_scan,
                    only_baseline = args.only_baseline,
                    do_row_scan = args.do_row_scan,
                )
            powerDevices.turn_off()
        else:
            run_TID(
                chip_name = args.chip_name,
                TID_str = args.TID_str,
                do_detailed = args.do_detailed,
                run_name_extra = run_str,
                do_knee_finding = args.do_knee_finding,
                do_full_scan = args.do_full_scan,
                only_baseline = args.only_baseline,
                do_row_scan = args.do_row_scan,
            )

        count += 1
        if not args.infinite_loop:
            break

if __name__ == "__main__":
    main()
