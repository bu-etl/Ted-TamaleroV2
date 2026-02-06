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
import plotly.express as px
import logging
import i2c_gui
import i2c_gui.chips
from i2c_gui.usb_iss_helper import USB_ISS_Helper
from i2c_gui.fpga_eth_helper import FPGA_ETH_Helper
from mpl_toolkits.axes_grid1 import make_axes_locatable
import time
import matplotlib.pyplot as plt
from tqdm import tqdm
from i2c_gui.chips.etroc2_chip import register_decoding
import os, sys
import multiprocessing
import datetime
from pathlib import Path
import pandas as pd
sys.path.insert(1, f'/home/{os.getlogin()}/ETROC2/ETROC_DAQ')
import run_script
try:
  import parser_arguments
except:
    pass
import importlib
importlib.reload(run_script)
from scripts.log_action import log_action_v2

def run_ws(
        chip_name: str,
        port: str = '/dev/ttyACM0',
        fpga_ip: str = '192.168.2.3',
        chip_address = 0x60,
        ws_address = 0x40,
        read_mode = 'WS',
    ):
    log_action_v2(Path("./"), "Config", "WS", f"Configure waveform sampler of chip with WS I2C {ws_address} with ws_testing.py script")
    # Set defaults
    ### It is very important to correctly set the chip name, this value is stored with the data

    # 'The port name the USB-ISS module is connected to. Default: COM3'
    # I2C addresses for the pixel block and WS

    if read_mode == 'WS':
        do_ws_controller = True
        do_i2c_controller = False
        do_high_level = False
    elif read_mode == 'I2C':
        do_ws_controller = False
        do_i2c_controller = True
        do_high_level = False
    else:
        do_ws_controller = False
        do_i2c_controller = False
        do_high_level = True

    i2c_gui.__no_connect__ = False  # Set to fake connecting to an ETROC2 device
    i2c_gui.__no_connect_type__ = "echo"  # for actually testing readback
    #i2c_gui.__no_connect_type__ = "check"  # default behaviour

    # Start logger and connect
    ## Logger
    log_level=30
    logging.basicConfig(format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')
    logger = logging.getLogger("Script_Logger")
    Script_Helper = i2c_gui.ScriptHelper(logger)

    ## USB ISS connection
    conn = i2c_gui.Connection_Controller(Script_Helper)
    conn.connection_type = "USB-ISS"
    conn.handle: USB_ISS_Helper
    conn.handle.port = port
    conn.handle.clk = 100

    conn.connect()

    chip = i2c_gui.chips.ETROC2_Chip(parent=Script_Helper, i2c_controller=conn)
    chip.config_i2c_address(chip_address)
    chip.config_waveform_sampler_i2c_address(ws_address)  # Not needed if you do not access WS registers
    logger.setLevel(log_level)

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

    def ws_decoded_register_write(decodedRegisterName, data_to_write):
        bit_depth = register_decoding["Waveform Sampler"]["Register Blocks"]["Config"][decodedRegisterName]["bits"]
        handle = chip.get_decoded_display_var("Waveform Sampler", "Config", decodedRegisterName)
        chip.read_decoded_value("Waveform Sampler", "Config", decodedRegisterName)
        if len(data_to_write)!=bit_depth: print("Binary data_to_write is of incorrect length for",decodedRegisterName, "with bit depth", bit_depth)
        data_hex_modified = hex(int(data_to_write, base=2))
        if(bit_depth>1): handle.set(data_hex_modified)
        elif(bit_depth==1): handle.set(data_to_write)
        else: print(decodedRegisterName, "!!!ERROR!!! Bit depth <1, how did we get here...")
        chip.write_decoded_value("Waveform Sampler", "Config", decodedRegisterName)

    def ws_decoded_config_read(decodedRegisterName, need_int=False):
        handle = chip.get_decoded_display_var("Waveform Sampler", f"Config", decodedRegisterName)
        chip.read_decoded_value("Waveform Sampler", f"Config", decodedRegisterName)
        if(need_int): return int(handle.get(), base=16)
        else: return handle.get()

    def ws_decoded_status_read(decodedRegisterName, need_int=False):
        handle = chip.get_decoded_display_var("Waveform Sampler", f"Status", decodedRegisterName)
        chip.read_decoded_value("Waveform Sampler", f"Status", decodedRegisterName)
        if(need_int): return int(handle.get(), base=16)
        else: return handle.get()

    # Set the basic peripheral registers
    peripheral_decoded_register_write("EFuse_Prog", format(0x00017f0f, '032b'))     # chip ID
    peripheral_decoded_register_write("singlePort", '1')                            # Set data output to right port only
    peripheral_decoded_register_write("serRateLeft", '00')                          # Set Data Rates to 320 mbps
    peripheral_decoded_register_write("serRateRight", '00')                         # ^^
    peripheral_decoded_register_write("onChipL1AConf", '00')                        # Switches off the onboard L1A
    peripheral_decoded_register_write("PLL_ENABLEPLL", '1')                         # "Enable PLL mode, active high. Debugging use only."
    peripheral_decoded_register_write("chargeInjectionDelay", format(0x0a, '05b'))  # User tunable delay of Qinj pulse
    peripheral_decoded_register_write("triggerGranularity", format(0x01, '03b'))    # only for trigger bit

    # Perform Auto-calibration on WS pixel (Row0, Col14)
    # Reset the maps
    baseLine = 0
    noiseWidth = 0

    row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
    column_indexer_handle,_,_ = chip.get_indexer("column")
    row = 0
    col = 14
    column_indexer_handle.set(col)
    row_indexer_handle.set(row)
    # Disable TDC
    pixel_decoded_register_write("enable_TDC", "0")
    # Enable THCal clock and buffer, disable bypass
    pixel_decoded_register_write("CLKEn_THCal", "1")
    pixel_decoded_register_write("BufEn_THCal", "1")
    pixel_decoded_register_write("Bypass_THCal", "0")
    pixel_decoded_register_write("TH_offset", format(0x07, '06b'))
    # Reset the calibration block (active low)
    pixel_decoded_register_write("RSTn_THCal", "0")
    pixel_decoded_register_write("RSTn_THCal", "1")
    # Start and Stop the calibration, (25ns x 2**15 ~ 800 us, ACCumulator max is 2**15)
    pixel_decoded_register_write("ScanStart_THCal", "1")
    pixel_decoded_register_write("ScanStart_THCal", "0")
    # Check the calibration done correctly
    if(pixel_decoded_register_read("ScanDone", "Status")!="1"): print("!!!ERROR!!! Scan not done!!!")
    baseLine = pixel_decoded_register_read("BL", "Status", need_int=True)
    noiseWidth = pixel_decoded_register_read("NW", "Status", need_int=True)
    # Disable clock and buffer before charge injection
    pixel_decoded_register_write("CLKEn_THCal", "0")
    pixel_decoded_register_write("BufEn_THCal", "0")
    # Set Charge Inj Q to 15 fC
    pixel_decoded_register_write("QSel", format(0x0e, '05b'))

    ### Print BL and NW from automatic calibration
    print(f"BL: {baseLine}, NW: {noiseWidth}")

    ### Disable all pixel readouts before doing anything
    row_indexer_handle,_,_ = chip.get_indexer("row")
    column_indexer_handle,_,_ = chip.get_indexer("column")
    column_indexer_handle.set(0)
    row_indexer_handle.set(0)

    broadcast_handle,_,_ = chip.get_indexer("broadcast")
    broadcast_handle.set(True)
    pixel_decoded_register_write("disDataReadout", "1")
    broadcast_handle.set(True)
    pixel_decoded_register_write("QInjEn", "0")
    broadcast_handle.set(True)
    pixel_decoded_register_write("disTrigPath", "1")

    ### WS and pixel initialization
    # If you want, you can change the pixel row and column numbers
    row_indexer_handle,_,_ = chip.get_indexer("row")  # Returns 3 parameters: handle, min, max
    column_indexer_handle,_,_ = chip.get_indexer("column")
    row = 0
    col = 14
    print(f"Enabling Pixel ({row},{col})")
    column_indexer_handle.set(col)
    row_indexer_handle.set(row)
    pixel_decoded_register_write("Bypass_THCal", "0")
    pixel_decoded_register_write("TH_offset", format(0x0c, '06b'))  # Offset used to add to the auto BL for real triggering
    pixel_decoded_register_write("QSel", format(0x1e, '05b'))       # Ensure we inject 30 fC of charge
    pixel_decoded_register_write("QInjEn", "1")                     # ENable charge injection for the selected pixel
    pixel_decoded_register_write("RFSel", format(0x00, '02b'))      # Set Largest feedback resistance -> maximum gain
    pixel_decoded_register_write("enable_TDC", "1")                 # Enable TDC

    # PLL calibration
    peripheral_decoded_register_write("asyPLLReset", "0")
    peripheral_decoded_register_write("asyPLLReset", "1")
    peripheral_decoded_register_write("asyStartCalibration", "0")
    peripheral_decoded_register_write("asyStartCalibration", "1")

    # FC calibration
    peripheral_decoded_register_write("asyAlignFastcommand", "1")
    peripheral_decoded_register_write("asyAlignFastcommand", "0")


    regOut1F_handle = chip.get_display_var("Waveform Sampler", "Config", "regOut1F")
    regOut1F_handle.set("0x22")
    chip.write_register("Waveform Sampler", "Config", "regOut1F")
    regOut1F_handle.set("0x0b")
    chip.write_register("Waveform Sampler", "Config", "regOut1F")

    # ws_decoded_register_write("mem_rstn", "0")                      # 0: reset memory
    # ws_decoded_register_write("clk_gen_rstn", "0")                  # 0: reset clock generation
    # ws_decoded_register_write("sel1", "0")                          # 0: Bypass mode, 1: VGA mode
    ws_decoded_register_write("DDT", format(0, '016b'))             # Time Skew Calibration set to 0
    ws_decoded_register_write("CTRL", format(0x2, '02b'))           # CTRL default = 0x10 for regOut0D
    ws_decoded_register_write("comp_cali", format(0, '03b'))        # Comparator calibration should be off

    chip.read_all_address_space("Waveform Sampler") # Read all registers of WS
    rd_addr_handle = chip.get_decoded_display_var("Waveform Sampler", "Config", "rd_addr")
    dout_handle = chip.get_decoded_display_var("Waveform Sampler", "Status", "dout")

    ### Run DAQ to send ws fc
    time_per_pixel = 3
    dead_time_per_pixel = 3
    total_scan_time = time_per_pixel + dead_time_per_pixel
    outname = 'ws_test'

    today = datetime.date.today()
    todaystr = "../ETROC-Data/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)

    try:
        parser = parser_arguments.create_parser()
    except:
        parser = run_script.getOptionParser()
    (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {fpga_ip} -t {int(total_scan_time)} -o {outname} -v -w -s 0x000C -p 0x000f --compressed_translation  --clear_fifo".split())
    IPC_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'main_process'))
    process.start()

    IPC_queue.put('start onetime ws')
    while not IPC_queue.empty():
        pass

    print("Taking data, waiting 1.5 s")
    time.sleep(1.5)
    print("Done waiting, will stop the DAQ")
    IPC_queue.put('stop DAQ')
    while not IPC_queue.empty():
        pass

    IPC_queue.put('allow threads to exit')
    process.join()

    ### Read from WS memory
    ws_decoded_register_write("rd_en_I2C", "1")

    max_steps = 1024  # Size of the data buffer inside the WS
    lastUpdateTime = time.time_ns()
    base_data = []
    coeff = 0.05/5*8.5  # This number comes from the example script in the manual
    time_coeff = 1/2.56  # 2.56 GHz WS frequency

    from i2c_gui.chips.address_space_controller import Address_Space_Controller
    ws_address_space_controller: Address_Space_Controller = chip._address_space["Waveform Sampler"]

    from i2c_gui.i2c_connection_helper import I2C_Connection_Helper
    i2c_controller: I2C_Connection_Helper = chip._i2c_controller
    addr_regs = [0x00, 0x00]  # regOut1C and regOut1D

    for address in tqdm(range(max_steps)):
        if do_ws_controller:
            ws_address_space_controller._memory[0x1C] = ((address & 0b11) << 6)
            ws_address_space_controller._memory[0x1D] = ((address & 0b1111111100) >> 2)
            ws_address_space_controller.write_memory_block(0x1C, 2, write_check=False)
            ws_address_space_controller.read_memory_block(0x20, 2)  # Read regIn20 and regIn21
            data = dout_handle.get()

        if do_i2c_controller:
            addr_regs[0] = ((address & 0b11) << 6)          # 0x1C
            addr_regs[1] = ((address & 0b1111111100) >> 2)  # 0x1D
            i2c_controller.write_device_memory(ws_address, 0x1C, addr_regs, 8)
            tmp_data = i2c_controller.read_device_memory(ws_address, 0x20, 2, 8)
            data = hex((tmp_data[0] >> 2) + (tmp_data[1] << 6))

        if do_high_level:
            rd_addr_handle.set(hex(address))
            chip.write_decoded_value("Waveform Sampler", "Config", "rd_addr", write_check=False, no_message=True)
            chip.read_decoded_value("Waveform Sampler", "Status", "dout", no_message=True)
            data = dout_handle.get()

        #if time_idx == 1:
        #    data = hex_0fill(int(data, 0) + 8192, 14)

        binary_data = bin(int(data, 0))[2:].zfill(14)  # because dout is 14 bits long
        Dout_S1 = int('0b'+binary_data[1:7], 0)
        Dout_S2 = int(binary_data[ 7]) * 24 + \
                    int(binary_data[ 8]) * 16 + \
                    int(binary_data[ 9]) * 10 + \
                    int(binary_data[10]) *  6 + \
                    int(binary_data[11]) *  4 + \
                    int(binary_data[12]) *  2 + \
                    int(binary_data[13])

        base_data.append(
            {
                "Data Address": address,
                "Data": int(data, 0),
                "Raw Data": bin(int(data, 0))[2:].zfill(14),
                "pointer": int(binary_data[0]),
                "Dout_S1": Dout_S1,
                "Dout_S2": Dout_S2,
                "Dout": Dout_S1 - coeff * Dout_S2,
            }
        )

    df = pd.DataFrame(base_data)

    df_length = len(df)
    channels = 8

    df_per_ch : list[pd.DataFrame] = []
    for ch in range(channels):
        df_per_ch += [df.iloc[int(ch * df_length/channels):int((ch + 1) * df_length/channels)].copy()]
        df_per_ch[ch].reset_index(inplace = True, drop = True)

    pointer_idx = df_per_ch[-1]["pointer"].loc[df_per_ch[-1]["pointer"] != 0].index  # TODO: Maybe add a search of the pointer in any channel, not just the last one
    if len(pointer_idx) != 0:  # If pointer found, reorder the data
        pointer_idx = pointer_idx[0]
        new_idx = list(set(range(len(df_per_ch[-1]))).difference(range(pointer_idx+1))) + list(range(pointer_idx+1))
        for ch in range(channels):
            df_per_ch[ch] = df_per_ch[ch].iloc[new_idx].reset_index(drop = True)  # Fix indexes after reordering

    # interleave the channels
    for ch in range(channels):
        df_per_ch[ch]["Time Index"] = df_per_ch[ch].index * channels + (channels - 1 - ch)  # Flip the order of the channels in the interleave...
        df_per_ch[ch]["Channel"] = ch + 1

    # Actually put it all together in one dataframe and sort the data correctly
    df = pd.concat(df_per_ch)
    df["Time [ns]"] = df["Time Index"] * time_coeff
    df.set_index('Time Index', inplace=True)
    df.sort_index(inplace=True)

    # Disable reading data from WS:
    ws_decoded_register_write("rd_en_I2C", "0")

    output = f"rawdataWS_{chip_name}_" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + ".csv"
    outfile = base_dir / output
    df.to_csv(outfile)

    df['Aout'] = -(df['Dout']-(31.5-coeff*31.5)*1.2)/32

    fig, ax = plt.subplots(figsize=(20, 8))
    ax.plot(df['Time [ns]'], df['Dout'])
    ax.set_xlabel('Time [ns]', fontsize=15)
    plt.show()

    fig_aout = px.line(
        df,
        x="Time [ns]",
        y="Aout",
        labels = {
            "Time [ns]": "Time [ns]",
            "Aout": "",
        },
        title = "Waveform (Aout) from the board {}".format(chip_name),
        markers=True
    )

    fig_dout = px.line(
        df,
        x="Time [ns]",
        y="Dout",
        labels = {
            "Time [ns]": "Time [ns]",
            "Dout": "",
        },
        title = "Waveform (Dout) from the board {}".format(chip_name),
        markers=True
    )

    todaystr = "../ETROC-figures/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)

    fig_aout.write_html(
        base_dir / f'WS_Aout_{chip_name}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}.html',
        full_html = False,
        include_plotlyjs = 'cdn',
    )

    fig_dout.write_html(
        base_dir / f'WS_Dout_{chip_name}_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")}.html',
        full_html = False,
        include_plotlyjs = 'cdn',
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(
                    prog='Waveform Sampler Testing!',
                    description='Control them!',
                    #epilog='Text at the bottom of help'
                    )
    parser.add_argument(
        '-c',
        '--chipname',
        metavar = 'NAME',
        type = str,
        help = 'Board label',
        required = True,
        dest = 'chip_name',
    )
    parser.add_argument(
        '--ip_address',
        metavar = 'NAME',
        type = str,
        help = 'KC705 FPGA IP address',
        default="192.168.2.3",
        dest = 'ip_address',
    )
    parser.add_argument(
        '-m',
        '--read_mode',
        metavar='MODE',
        type = str,
        choices=["WS", "I2C", "High Level"],
        default='WS',
        help='The read mode algorithm to use for reading the WS. Options are: WS - to read with the WS controller; I2C - to read with the I2C controller; High Level - to use the high level functions. Default: WS',
    )
    args = parser.parse_args()

    run_ws(
        chip_name = args.chip_name,
        port = '/dev/ttyACM0',
        fpga_ip = args.ip_address,
        chip_address = 0x60,
        ws_address = 0x40,
        read_mode = args.read_mode,
    )

if __name__ == "__main__":
    main()
