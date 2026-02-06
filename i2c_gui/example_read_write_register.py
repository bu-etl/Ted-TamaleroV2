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

import logging
import i2c_gui
import i2c_gui.chips
from i2c_gui.usb_iss_helper import USB_ISS_Helper
from i2c_gui.fpga_eth_helper import FPGA_ETH_Helper

default_log_level = 40

def read_write_test(
    port: str = "COM3",
    chip_address: int = 0x72,
    ws_address: int = None,
    log_level = default_log_level,
    ):
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
    #conn.handle.hostname = "192.168.2.3"
    #conn.handle.port = "1024"

    conn.connect()

    try:
        chip = i2c_gui.chips.ETROC2_Chip(parent=Script_Helper, i2c_controller=conn)
        chip.config_i2c_address(chip_address)  # Not needed if you do not access ETROC registers (i.e. only access WS registers)
        chip.config_waveform_sampler_i2c_address(ws_address)  # Not needed if you do not access WS registers

        logger.setLevel(log_level)

        ### Read a peripheral config register
        # First get a handle to the variable (the handle is a python tkinter StringVar so you need to use specific methods to read/write the handle)
        handle_PeriCfg0 = chip.get_display_var("ETROC2", "Peripheral Config", "PeriCfg0")
        # Then read over I2C the value of that register (the value is automatically stored in the handle)
        chip.read_register("ETROC2", "Peripheral Config", "PeriCfg0")
        # Fetch the value from the handle and do something with it
        print(handle_PeriCfg0.get())

        ### Write the same peripheral config register
        # We already have the handle, so just set a value we want
        handle_PeriCfg0.set("0x12")  # In theory it should support either hex or decimal
        # Then send a write command over I2C
        chip.write_register("ETROC2", "Peripheral Config", "PeriCfg0")  # Unless explicitly disabled, there will be a read I2C command after the write to check the write was successful, but this readback operation only sends a message to the GUI, so you need to explicitly check if you want to be sure
        chip.read_register("ETROC2", "Peripheral Config", "PeriCfg0")
        print(handle_PeriCfg0.get())

        ### Global status registers can only be read, not written
        handle_PeriSta0 = chip.get_display_var("ETROC2", "Peripheral Status", "PeriSta0")
        chip.read_register("ETROC2", "Peripheral Status", "PeriSta0")
        print(handle_PeriSta0.get())

        ### Read a pixel config register
        # For the pixels, we need to fetch the indexers to the pixel since these control the other function calls
        row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
        column_indexer_handle,_,_ = chip.get_indexer("column")
        # Choose the pixel to operate on
        column_indexer_handle.set(2)
        row_indexer_handle.set(4)
        # Get the handle to the register
        handle_PixCfg0_2_4 = chip.get_indexed_var("ETROC2", "Pixel Config", "PixCfg0")
        #handle_PixCfg0_2_4 = chip.get_display_var("ETROC2", "Pixel Config:2:4", "PixCfg0") # Alternative to previous line but does not use the indexer handles since the values are explicitly defined
        # Read over I2C the register pointed to by the indexers (there is not a version that does not use the indexers)
        chip.read_register("ETROC2", "Pixel Config", "PixCfg0")
        # Fetch the value from the handle and do something with it
        print(handle_PixCfg0_2_4.get())

        ### Write same pixel register as above
        handle_PixCfg0_2_4.set(20)
        chip.write_register("ETROC2", "Pixel Config", "PixCfg0")
        chip.read_register("ETROC2", "Pixel Config", "PixCfg0")
        print(handle_PixCfg0_2_4.get())

        ### Read a pixel status register (remember that the indexers are used in the background to choose which pixel is being operated on)
        handle_PixSta1_2_4 = chip.get_indexed_var("ETROC2", "Pixel Status", "PixSta1")
        chip.read_register("ETROC2", "Pixel Status", "PixSta1")
        print(handle_PixSta1_2_4.get())

        ### Read WS Config register
        handle_WS_regOut01 = chip.get_display_var("Waveform Sampler", "Config", "regOut01")
        chip.read_register("Waveform Sampler", "Config", "regOut01")
        print(handle_WS_regOut01.get())

        ### Read WS Status register
        handle_WS_regIn20 = chip.get_display_var("Waveform Sampler", "Status", "regIn20")
        chip.read_register("Waveform Sampler", "Status", "regIn20")
        print(handle_WS_regIn20.get())

        ### You may also be interested in the following functions:
        ## Read and write the full chip, you can use handles in the middle to modify individual registers and then write everything at once
        #chip.read_all()
        #chip.write_all()
        ## Read and write a full address space:
        #chip.read_all_address_space("ETROC2")
        #chip.write_all_address_space("ETROC2")
        ## Read and write a full block within an address space (Status blocks can not be written to)
        #chip.read_all_block("ETROC2", "Pixel Config:3:4") # Block name for a spacific pixel
        #chip.read_all_block("ETROC2", "Pixel Config") # Block name for all pixels
        #chip.write_all_block("ETROC2", "Pixel Config") # Block name for all pixels

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
        logging.basicConfig(filename='logging.log', filemode='w', encoding='utf-8', level=logging.NOTSET)
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

    i2c_gui.__no_connect__ = True  # Set to fake connecting to an ETROC2 device
    i2c_gui.__no_connect_type__ = "echo"  # for actually testing readback
    #i2c_gui.__no_connect_type__ = "check"  # default behaviour

    read_write_test(log_level=log_level)