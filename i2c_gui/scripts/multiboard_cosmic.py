#############################################################################
# zlib License
#
# (C) 2023 Zach Flowers, Murtaza Safdari <musafdar@cern.ch>, Jongho Lee
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

# Imports
import matplotlib.pyplot as plt
import i2c_gui
import i2c_gui.chips
from mpl_toolkits.axes_grid1 import make_axes_locatable
import os, sys
import multiprocessing
import datetime
from pathlib import Path
import subprocess
import sqlite3
from notebooks.notebook_helpers import *
sys.path.insert(1, f'/home/{os.getlogin()}/ETROC2/ETROC_DAQ')
import run_script
import importlib
importlib.reload(run_script)
import signal
import pandas as pd
import time

def push_history_to_git(
        input_df: pd.DataFrame,
        note: str,
        git_repo: str,
    ):
    # Store BL, NW dataframe for later use
    new_columns = {
        'note': f'{note}',
    }

    if not os.path.exists(f'/home/{os.getlogin()}/ETROC2/{git_repo}'):
        os.system(f'git clone git@github.com:CMS-ETROC/{git_repo}.git /home/{os.getlogin()}/ETROC2/{git_repo}')

    for col in new_columns:
        input_df[col] = new_columns[col]

    outdir = Path(f'../{git_repo}')
    outfile = outdir / 'BaselineHistory.sqlite'

    init_cmd = [
        'cd ' + str(outdir.resolve()),
        'git stash -u',
        'git pull',
    ]
    end_cmd = [
        'cd ' + str(outdir.resolve()),
        'git add BaselineHistory.sqlite',
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
        input_df.to_sql('baselines', sqlconn, if_exists='append', index=False)

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

def func_daq(
        chip_names,
        run_str,
        extra_str,
        directory: Path,
        fpga_ip = "192.168.2.3",
        delay: int = 485,
        run_time: int = 120,
        extra_margin_time: int = 100,
        polarity = 0x000f,
        led_flag = 0x0000,
        active_channel = 0x0011,
        active_delay = "0001",
        do_ssd: bool = False,
    ):

    print('DAQ Start:', datetime.datetime.now())
    ## Making directory to save main_process.out files
    currentPath = Path('.')
    main_pro_dir = currentPath / 'main_process_multiboard'
    main_pro_dir.mkdir(exist_ok=True)

    outdir_name = f'{run_str}_'+'_'.join(chip_names)+f'_{extra_str}'
    if not do_ssd:
        outdir = directory / outdir_name
        outdir.mkdir(exist_ok=False)

    trigger_bit_delay = int(f'{active_delay}11'+format(delay, '010b'), base=2)
    parser = run_script.getOptionParser()
    if do_ssd:
        (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {fpga_ip} -t {run_time+extra_margin_time} -o {outdir_name} -v -w -s {led_flag} -p {polarity} -d {trigger_bit_delay} -a {active_channel} --compressed_translation -l 100000 --compressed_binary --ssd".split())
    else:
         (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {fpga_ip} -t {run_time+extra_margin_time} -o {outdir_name} -v -w -s {led_flag} -p {polarity} -d {trigger_bit_delay} -a {active_channel} --compressed_translation -l 100000 --compressed_binary".split())
    IPC_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'main_process_cosmic'))
    process.start()

    IPC_queue.put('memoFC Start Triggerbit')

    while not IPC_queue.empty():
        pass
    time.sleep(run_time)
    IPC_queue.put('stop DAQ')
    IPC_queue.put('memoFC Triggerbit')
    while not IPC_queue.empty():
        pass
    IPC_queue.put('allow threads to exit')
    process.join()
    print('DAQ End:', datetime.datetime.now())

    del IPC_queue, process, parser

def run_daq(
        chip_names: list,
        chip_addresses: list,
        chip_offsets: list,
        run_str: str,
        extra_str: str,
        i2c_port: str = "/dev/ttyACM0",
        fpga_ip: str = "192.168.2.3",
        run_time: int = 120,
        activeChannel: str = "0x0011",
        activeTrigger: str = "0001",
        led_flag: int = 0,
        polarity: str = "0x000f",
        do_fullAutoCal: bool = False,
        do_saveHistory: bool = False,
        do_skipConfig: bool = False,
        do_skipCalibration: bool = False,
        do_skipOffset: bool = False,
        do_skipAlign: bool = False,
        do_skipOnOff: bool = False,
        do_skipTDC: bool = False,
        do_ssd: bool = False,
        do_cosmic: bool= False,
    ):
    # It is very important to correctly set the chip name, this value is stored with the data
    chip_fignames = f'{run_str}_'+'_'.join(chip_names)+f'_{extra_str}'

    # 'The port name the USB-ISS module is connected to. Default: COM3'
    port = i2c_port
    # ws_addresses = [None, None, None]

    # i2c_gui.__no_connect__ = False  # Set to fake connecting to an ETROC2 device
    # i2c_gui.__no_connect_type__ = "echo"  # for actually testing readback
    # #i2c_gui.__no_connect_type__ = "check"  # default behaviour

    data_rootdir = Path('../ETROC-Data')
    data_outdir = data_rootdir / (datetime.date.today().isoformat() + '_Array_Test_Results')
    data_outdir.mkdir(exist_ok=True)

    fig_outdir = Path('../ETROC-figures')
    fig_outdir = fig_outdir / (datetime.date.today().isoformat() + '_Array_Test_Results')
    fig_outdir.mkdir(exist_ok=True)
    fig_path = str(fig_outdir)

    # Make i2c_connection class object
    # i2c_conn = self, port, chip_addresses, chip_names, chip_fc_delays
    i2c_conn = i2c_connection(port,chip_addresses,chip_names,[("1","1"), ("1","1"), ("1","1")])

    # Config chips
    ### Key is (Disable Pixels, Auto Cal, Chip Peripherals, Basic Peri Reg Check, Pixel Check)
    # 0 - 0 - (disable & auto_cal all pixels) - (auto_TH_CAL) - (disable default all pixels) - (set basic peripherals) - (peripheral reg check) -  (pixel ID check)
    if not do_skipConfig:
        i2c_conn.config_chips('00001111')

    ## Define pixel of interests:
    if do_fullAutoCal:
        col_list, row_list = np.meshgrid(np.arange(16), np.arange(16))
        scan_list = list(zip(row_list.flatten(), col_list.flatten()))
    else:
        # Define pixels of interest
        row_list = [14, 14, 14, 14]
        col_list = [6, 7, 8, 9]
        scan_list = list(zip(row_list, col_list))
        print(scan_list)

    if not do_skipCalibration:
        if do_fullAutoCal:
            i2c_conn.config_chips('00100000')
            ## Visualize the learned Baselines (BL) and Noise Widths (NW)
            ## Note that the NW represents the full width on either side of the BL
            frames = []
            for chip_address, chip_name in zip(chip_addresses,chip_names):
                BL_map_THCal,NW_map_THCal, BL_df = i2c_conn.get_auto_cal_maps(chip_address)
                frames.append(BL_df)
                fig = plt.figure(dpi=200, figsize=(10,10))
                gs = fig.add_gridspec(1,2)

                ax0 = fig.add_subplot(gs[0,0])
                ax0.set_title(f"{chip_name}: BL (DAC LSB)")
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
                ax1.set_title(f"{chip_name}: NW (DAC LSB)")
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
                        ax0.text(x,y,f"{BL_map_THCal.T[x,y]:.0f}", c="white", size=5, rotation=45, fontweight="bold", ha="center", va="center")
                        ax1.text(x,y,f"{NW_map_THCal.T[x,y]:.0f}", c="white", size=5, rotation=45, fontweight="bold", ha="center", va="center")
                plt.savefig(fig_path+"/BL_NW_"+chip_fignames+"_"+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")+".png")

            full_BL_df = pd.concat(frames)
            if do_saveHistory:
                push_history_to_git(full_BL_df, f'{run_str}_{extra_str}', 'ETROC-History-Testbeam')

            col_list, row_list = np.meshgrid(np.arange(16), np.arange(16))
            scan_list = list(zip(row_list.flatten(), col_list.flatten()))

        else:
            # Define pixels of interest
            row_list = [15, 15, 15, 15]
            col_list = [6, 7, 8, 9]
            scan_list = list(zip(row_list, col_list))
            print(scan_list)

            tmp_data = []
            for chip_address, chip_name in zip(chip_addresses, chip_names):
                for row, col in scan_list:
                    i2c_conn.auto_cal_pixel(chip_name=chip_name, row=row, col=col, verbose=False, chip_address=chip_address, chip=None, data=tmp_data, row_indexer_handle=None, column_indexer_handle=None)
            BL_df = pandas.DataFrame(data = tmp_data)
            if do_saveHistory:
                push_history_to_git(BL_df, f'{run_str}_{extra_str}', 'ETROC-History-Testbeam')

    ### Enable pixels of Interest
    if not do_skipOnOff:
        i2c_conn.enable_select_pixels_in_chips(scan_list)

    for chip_index, chip_address in enumerate(chip_addresses):
        chip = i2c_conn.get_chip_i2c_connection(chip_address)
        row_indexer_handle,_,_ = chip.get_indexer("row")
        column_indexer_handle,_,_ = chip.get_indexer("column")
        for row, col in scan_list:
            print(f"Operating on chip {hex(chip_address)} Pixel ({row},{col})")
            column_indexer_handle.set(col)
            row_indexer_handle.set(row)
            i2c_conn.pixel_decoded_register_write("QInjEn", "0", chip)
            if not do_skipOffset:
                i2c_conn.pixel_decoded_register_write("TH_offset", format(chip_offsets[chip_index], '06b'), chip)
            if do_cosmic:
                if(chip_index == 0 or chip_index == 2):
                    i2c_conn.pixel_decoded_register_write("lowerTOTTrig", format(0x064, '09b'), chip) ## only for cosmic run
        del chip, row_indexer_handle, column_indexer_handle

    if not do_skipAlign:
        # Calibrate PLL
        for chip_address in chip_addresses[:]:
            i2c_conn.calibratePLL(chip_address, chip=None)

        # Calibrate FC
        for chip_address in chip_addresses[:]:
            i2c_conn.asyResetGlobalReadout(chip_address, chip=None)
            i2c_conn.asyAlignFastcommand(chip_address, chip=None)

    plzDelDir = data_outdir / 'PlzDelete_Board013_NoLinkCheck'
    if not plzDelDir.is_dir():
        print('\nOne time DAQ run for checking LED lights')
        # Run One Time DAQ to Set FPGA Firmware
        parser = run_script.getOptionParser()
        (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {fpga_ip} -t 20 -o PlzDelete_Board013_NoLinkCheck -v -w -s 0x0000 -p 0x000f -d 0xb800 -a 0x00bb --clear_fifo".split())
        IPC_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'main_process_Start_LEDs_Board013_NoLinkCheck'))
        process.start()

        IPC_queue.put('memoFC Start Triggerbit QInj L1A BCR')
        while not IPC_queue.empty():
            pass
        time.sleep(10)
        IPC_queue.put('stop DAQ')
        IPC_queue.put('memoFC Triggerbit')
        while not IPC_queue.empty():
            pass
        IPC_queue.put('allow threads to exit')
        process.join()
        del IPC_queue, process, parser

    if not do_skipTDC:
        func_daq(
            chip_names = chip_names,
            run_str = run_str,
            extra_str = extra_str,
            directory = data_outdir,
            fpga_ip = fpga_ip,
            delay = 485,
            run_time = run_time,
            extra_margin_time = 15,
            polarity = polarity,
            led_flag = led_flag,
            active_channel = activeChannel,
            active_delay = activeTrigger,
            do_ssd = do_ssd,
        )

    if not do_skipOnOff:
        for chip_address in chip_addresses[:]:
            chip = i2c_conn.get_chip_i2c_connection(chip_address)
            row_indexer_handle,_,_ = chip.get_indexer("row")
            column_indexer_handle,_,_ = chip.get_indexer("column")
            for row,col in scan_list:
                i2c_conn.disable_pixel(row=row, col=col, verbose=True, chip_address=chip_address, chip=chip, row_indexer_handle=row_indexer_handle, column_indexer_handle=column_indexer_handle)
            del chip, row_indexer_handle, column_indexer_handle

    # Disconnect I2C Device
    del i2c_conn


def main():
    import argparse

    parser = argparse.ArgumentParser(
                    prog='Cosmic run!',
                    description='Control them!',
                    #epilog='Text at the bottom of help'
                    )

    parser.add_argument(
        '-s',
        '--extraStr',
        metavar = 'NAME',
        type = str,
        help = 'Extra string - no special chars',
        required = True,
        dest = 'extra_str',
    )
    parser.add_argument(
        '-t',
        '--runTime',
        metavar = 'TIME',
        type = int,
        help = 'DAQ running time in second',
        required = True,
        dest = 'daq_run_time',
    )
    parser.add_argument(
        '--globalRunTime',
        metavar = 'TIME',
        type = int,
        help = 'Global time limit for the total running time',
        dest = 'globalRunTime',
        default = -1,
    )
    parser.add_argument(
        '--globalCount',
        metavar = 'NUM',
        type = int,
        help = 'Global count limit',
        dest = 'globalCount',
        default = -1,
    )
    parser.add_argument(
        '--activeCh',
        metavar = 'HEX',
        help = 'Decide which channel will be actived (0x0011: ch1, 0x0022: ch2, 0x0044: ch3, 0x0088: ch4)',
        required = True,
        dest = 'activeCh',
    )
    parser.add_argument(
        '--activeTrig',
        metavar = 'BINARY',
        help = 'Decide which channel will be used for trigger (0001: ch1, 0010: ch2, 0100: ch3, 1000: ch4)',
        type = str,
        required = True,
        dest = 'activeTrig',
    )
    parser.add_argument(
        '--polarity',
        metavar = 'HEX',
        help = 'Polarity',
        required = True,
        dest = 'polarity',
    )
    parser.add_argument(
        '--cosmic',
        help = 'TOT trigger window set for cosmic run',
        action = 'store_true',
        dest = 'cosmic',
    )
    parser.add_argument(
        '--fullAutoCal',
        help = 'Run autocalibration for all 256 pixels',
        action = 'store_true',
        dest = 'fullAutoCal',
    )
    parser.add_argument(
        '--saveHistory',
        help = 'Save BL and NW as a history and push to git repo',
        action = 'store_true',
        dest = 'saveHistory',
    )
    parser.add_argument(
        '--skipConfig',
        help = 'Skip configure ETROC2',
        action = 'store_true',
        dest = 'skipConfig',
    )
    parser.add_argument(
        '--skipCalibration',
        help = 'Skip automatic calibration',
        action = 'store_true',
        dest = 'skipCalibration',
    )
    parser.add_argument(
        '--skipOffset',
        help = 'Skip offset configuration',
        action = 'store_true',
        dest = 'skipOffset',
    )
    parser.add_argument(
        '--skipAlign',
        help = 'Skip PLL and FC alignment',
        action = 'store_true',
        dest = 'skipAlign',
    )
    parser.add_argument(
        '--skipOnOff',
        help = 'Skip Enabling and disabling pixels',
        action = 'store_true',
        dest = 'skipOnOff',
    )
    parser.add_argument(
        '--skipTDC',
        help = 'Skip TDC DAQ run',
        action = 'store_true',
        dest = 'skipTDC',
    )
    parser.add_argument(
        '--saveSSD',
        help = 'Save data in SSD',
        action = 'store_true',
        dest = 'saveSSD',
    )
    parser.add_argument(
        '-b0',
        '--board0_name',
        metavar = 'NAME',
        help = "Name of the ETROC board installed in channel 0 (FMCRX1)",
        dest = 'board0_name',
        required = True,
        type = str,
    )
    parser.add_argument(
        '-b1',
        '--board1_name',
        metavar = 'NAME',
        help = "Name of the ETROC board installed in channel 1 (FMCRX2)",
        dest = 'board1_name',
        default = None,
        type = str,
    )
    parser.add_argument(
        '-b2',
        '--board2_name',
        metavar = 'NAME',
        help = "Name of the ETROC board installed in channel 2 (FMCRX3)",
        dest = 'board2_name',
        default = None,
        type = str,
    )
    parser.add_argument(
        '-b3',
        '--board3_name',
        metavar = 'NAME',
        help = "Name of the ETROC board installed in channel 3 (FMCRX4)",
        dest = 'board3_name',
        default = None,
        type = str,
    )
    parser.add_argument(
        '--board0_i2c',
        metavar = 'I2C_ADDRESS',
        help = "I2C address of the ETROC board installed in channel 0 (FMCRX1)",
        dest = 'board0_i2c',
        required = True,
        type = int,
    )
    parser.add_argument(
        '--board1_i2c',
        metavar = 'I2C_ADDRESS',
        help = "I2C address of the ETROC board installed in channel 1 (FMCRX2)",
        dest = 'board1_i2c',
        default = None,
        type = int,
    )
    parser.add_argument(
        '--board2_i2c',
        metavar = 'I2C_ADDRESS',
        help = "I2C address of the ETROC board installed in channel 2 (FMCRX3)",
        dest = 'board2_i2c',
        default = None,
        type = int,
    )
    parser.add_argument(
        '--board3_i2c',
        metavar = 'I2C_ADDRESS',
        help = "I2C address of the ETROC board installed in channel 3 (FMCRX4)",
        dest = 'board3_i2c',
        default = None,
        type = int,
    )
    parser.add_argument(
        '--board0_offset',
        help = 'Offset to determine the thresholds = BL + offset for channel 0 (FMCRX1)',
        metavar = 'NUM',
        type = int,
        default = 10,
        required = True,
        dest = 'board0_offset',
    )
    parser.add_argument(
        '--board1_offset',
        help = 'Offset to determine the thresholds = BL + offset for channel 1 (FMCRX2)',
        metavar = 'NUM',
        type = int,
        default = None,
        dest = 'board1_offset',
    )
    parser.add_argument(
        '--board2_offset',
        help = 'Offset to determine the thresholds = BL + offset for channel 2 (FMCRX3)',
        metavar = 'NUM',
        type = int,
        default = None,
        dest = 'board2_offset',
    )
    parser.add_argument(
        '--board3_offset',
        help = 'Offset to determine the thresholds = BL + offset for channel 3 (FMCRX4)',
        metavar = 'NUM',
        type = int,
        default = None,
        dest = 'board3_offset',
    )

    args = parser.parse_args()
    start_time = time.time()

    full_chip_names = [args.board0_name, args.board1_name, args.board2_name, args.board3_name]
    full_chip_addresses = [args.board0_i2c, args.board1_i2c, args.board2_i2c, args.board3_i2c]
    full_chip_offsets = [args.board0_offset, args.board1_offset, args.board2_offset, args.board3_offset]

    chip_names = list(filter(lambda item: item is not None, full_chip_names))
    chip_addresses = list(filter(lambda item: item is not None, full_chip_addresses))
    chip_offsets = list(filter(lambda item: item is not None, full_chip_offsets))

    count = 0
    num_active_boards = len(chip_names)
    binary_active_boards = format(int(args.activeCh[-1], base=16),'04b')
    position_active_boards = np.argwhere(np.array(list(binary_active_boards)).astype(int)[::-1]>0).flatten()

    if (args.globalRunTime == -1) and (args.globalCount == -1):
        print("Global run limit does not set, Please check the option")
        sys.exit(0)

    while True:
        run_str = f"Run{count}"
        led_page_count = count % num_active_boards
        led_page = int("000000000000"+format(position_active_boards[led_page_count], '02b')+"00", base=2)

        def signal_handler(sig, frame):
            print("Exiting gracefully")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        run_daq(
            chip_names = chip_names,
            chip_addresses = chip_addresses,
            chip_offsets = chip_offsets,
            run_str = run_str,
            extra_str = args.extra_str,
            i2c_port = "/dev/ttyACM0",
            fpga_ip = "192.168.2.3",
            run_time = args.daq_run_time,
            activeChannel = args.activeCh,
            activeTrigger = args.activeTrig,
            led_flag = led_page,
            polarity = args.polarity,
            do_fullAutoCal =  args.fullAutoCal,
            do_saveHistory = args.saveHistory,
            do_skipConfig = args.skipConfig,
            do_skipCalibration = args.skipCalibration,
            do_skipOffset = args.skipOffset,
            do_skipAlign = args.skipAlign,
            do_skipOnOff = args.skipOnOff,
            do_skipTDC = args.skipTDC,
            do_ssd = args.saveSSD,
            do_cosmic = args.cosmic,
        )

        end_time = time.time()

        count += 1

        if (end_time - start_time > args.globalRunTime) and (args.globalRunTime != -1):
            print('Exiting because of time limit')
            break

        if (count >= args.globalCount) and (args.globalCount != -1):
            print('Exiting because of count limit')
            break

if __name__ == "__main__":
    main()