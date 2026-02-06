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

# nb. This is very similar to the read write register example
# There is one detail you have to be very careful about
# Never fetch a decoded value handle change it and write to I2C without first reading that value
# When you write to I2C, all registers containing the decoded value are fully written to the device
# If you do not read first, then you will not know what the parts of the register that do not belong to the decoded value contain
# These parts may have default values, different from what is currently written to the device
# Or these parts may be some left over information from previous operations you may have performed on this register
# Take extreme care when operating on decoded values!!!!

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

        ### Read a peripheral config decoded value
        # First get a handle to the variable (the handle is a python tkinter StringVar so you need to use specific methods to read/write the handle)
        handle_PLL_ClkGen_disCLK = chip.get_decoded_display_var("ETROC2", "Peripheral Config", "PLL_ClkGen_disCLK")
        # Then read over I2C the value of that register (the value is automatically stored in the handle)
        chip.read_decoded_value("ETROC2", "Peripheral Config", "PLL_ClkGen_disCLK")
        #chip.read_register("ETROC2", "Peripheral Config", "PeriCfg0") # As an alternative, you an read "by hand" the register(s) where the decoded value is contained
        # Fetch the value from the handle and do something with it
        print(handle_PLL_ClkGen_disCLK.get())

        ### Write the same peripheral config decoded value
        # We already have the handle, so just set a value we want
        handle_PLL_ClkGen_disCLK.set("1")  # Be careful when setting, single bit decoded values only support 0 and 1
        # Then send a write command over I2C
        chip.write_decoded_value("ETROC2", "Peripheral Config", "PLL_ClkGen_disCLK")  # Unless explicitly disabled, there will be a read I2C command after the write to check the write was successful, but this readback operation only sends a message to the GUI, so you need to explicitly check if you want to be sure
        chip.read_decoded_value("ETROC2", "Peripheral Config", "PLL_ClkGen_disCLK")
        print(handle_PLL_ClkGen_disCLK.get())

        ## See register exaples to understand how to access pixel decoded values and WS decoded values, the logi is exactly the same

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