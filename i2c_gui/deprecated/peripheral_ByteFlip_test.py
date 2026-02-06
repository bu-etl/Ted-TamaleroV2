#!/usr/bin/env python
# coding: utf-8

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
# Modified for ETROC2 I2C testing in jupyter notebooks, Murtaza Safdari, Jongho Lee
#############################################################################

import logging
import i2c_gui
import i2c_gui.chips
from i2c_gui.usb_iss_helper import USB_ISS_Helper
from i2c_gui.fpga_eth_helper import FPGA_ETH_Helper
from i2c_gui.chips.etroc2_chip import register_model

def byte_flip_test(
    port = "COM3", # 'The port name the USB-ISS module is connected to. Default: COM3'
    chip_address: int = 0x60, # I2C addresses for the ETROC2 chip
    ws_address: int = None, # I2C addresses for the Waveform Sampler
    log_level: int = 0,
    ):

    # Start logger and connect
    logger = logging.getLogger("Script_Logger")
    Script_Helper = i2c_gui.ScriptHelper(logger)

    # Set defaults
    # 'If set, the full log will be saved to a file (i.e. the log level is ignored)'
    log_file = False

    ## USB ISS connection
    conn = i2c_gui.Connection_Controller(Script_Helper)
    conn.connection_type = "USB-ISS"
    conn.handle: USB_ISS_Helper
    conn.handle.port = port
    conn.handle.clk = 100

    ## For FPGA connection (not yet fully implemented)
    #conn.connection_type = "FPGA-Eth"
    #conn.handle: FPGA_ETH_Helper
    #conn.handle.hostname = "192.168.2.3"
    #conn.handle.port = "1024"

    conn.connect()

    # counter for failure peripheral register testing
    failure_counter = 0

    try:
        chip = i2c_gui.chips.ETROC2_Chip(parent=Script_Helper, i2c_controller=conn)
        chip.config_i2c_address(chip_address)  # Not needed if you do not access ETROC registers (i.e. only access WS registers)
        # chip.config_waveform_sampler_i2c_address(ws_address)  # Not needed if you do not access WS registers

        logger.setLevel(log_level)

        # Single byte flip peripheral
        peripheralRegisterKeys = register_model["ETROC2"]["Register Blocks"]["Peripheral Config"]["Registers"].keys()
        for peripheralRegisterKey in peripheralRegisterKeys:
            
            # Fetch the register
            handle_PeriCfgX = chip.get_display_var("ETROC2", "Peripheral Config", peripheralRegisterKey)
            chip.read_register("ETROC2", "Peripheral Config", peripheralRegisterKey)
            data_bin_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            
            # Make the flipped bits, "2"
            data_bin_modified_PeriCfgX = data_bin_PeriCfgX.replace('1', '2').replace('0', '1').replace('2', '0')
            
            # data_bin_modified_PeriCfgX = ''.join(data_bin_modified_PeriCfgX)
            data_hex_modified_PeriCfgX = hex(int(data_bin_modified_PeriCfgX, base=2))
            
            # Set the register with the value
            handle_PeriCfgX.set(data_hex_modified_PeriCfgX)
            chip.write_register("ETROC2", "Peripheral Config", peripheralRegisterKey)
            
            # Perform two reads to verify the persistence of the change
            chip.read_register("ETROC2", "Peripheral Config", peripheralRegisterKey)
            data_bin_new_1_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            chip.read_register("ETROC2", "Peripheral Config", peripheralRegisterKey)
            data_bin_new_2_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            
            # Undo the change to recover the original register value, and check for consistency
            handle_PeriCfgX.set(hex(int(data_bin_PeriCfgX, base=2)))
            chip.write_register("ETROC2", "Peripheral Config", peripheralRegisterKey)
            chip.read_register("ETROC2", "Peripheral Config", peripheralRegisterKey)
            data_bin_recover_PeriCfgX = format(int(handle_PeriCfgX.get(), base=16), '08b')
            
            # Handle what we learned from the tests
            # outputs = [peripheralRegisterKey, data_bin_PeriCfgX, "To", data_bin_new_1_PeriCfgX,  "To", data_bin_new_2_PeriCfgX, "To", data_bin_recover_PeriCfgX]
            # message = ' '.join(outputs)
            # logger.trace(message)
            
            if(data_bin_new_1_PeriCfgX!=data_bin_new_2_PeriCfgX or data_bin_new_2_PeriCfgX!=data_bin_modified_PeriCfgX or data_bin_recover_PeriCfgX!=data_bin_PeriCfgX): 
                # outputs = ["\033[1;33m", peripheralRegisterKey, "\033[1;31m FAILURE \033[0m \n"]
                # message = ' '.join(outputs)
                # logger.trace(message)
                failure_counter += 1
        
        if(failure_counter != 0):
            print("\033[1;31m Peripheral byte flip testing is failed \033[0m")
        else:
            print("\033[1;32m Peripheral byte flip testing is a success \033[0m")
            
    except Exception:
        import traceback
        traceback.print_exc()
    except:
        print("An Unknown Exception occurred")
    finally:
        conn.disconnect()  # Put this in finally block so that it always executes

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description='Run a full test of the ETROC2 registers')
    parser.add_argument(
        '-l',
        '--log-level',
        help = 'Set the logging level. Default: WARNING',
        choices = ["CRITICAL","ERROR","WARNING","INFO","DEBUG","TRACE","DETAILED_TRACE","NOTSET"],
        default = "WARNING",
        dest = 'log_level',
    )
    parser.add_argument(
        '--log-file',
        help = 'If set, the full log will be saved to a file (i.e. the log level is ignored)',
        action = 'store_true',
        dest = 'log_file',
        default=False,
    )
    parser.add_argument(
        '-p',
        '--port',
        metavar = 'device',
        help = 'The port name the USB-ISS module is connected to. Default: COM3',
        default = "COM3",
        dest = 'port',
        type = str,
    )

    args = parser.parse_args()

    if args.log_file:
        logging.basicConfig(filename='result_peripheral_byte_flip_test.log', filemode='w', encoding='utf-8', level=logging.NOTSET)
        
    else:
        log_level = 0
        if args.log_level == "CRITICAL":
            log_level=50
        elif args.log_level == "ERROR":
            log_level=40
        elif args.log_level == "WARNING":
            log_level=30
        elif args.log_level == "INFO":
            log_level=20
        elif args.log_level == "DEBUG":
            log_level=10
        elif args.log_level == "TRACE":
            log_level=8
        elif args.log_level == "DETAILED_TRACE":
            log_level=5
        elif args.log_level == "NOTSET":
            log_level=0
        logging.basicConfig(format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')

    i2c_gui.__no_connect__ = False  # Set to fake connecting to an ETROC2 device
    i2c_gui.__no_connect_type__ = "echo"  # for actually testing readback
    #i2c_gui.__no_connect_type__ = "check"  # default behaviour

    byte_flip_test(log_level=log_level)
