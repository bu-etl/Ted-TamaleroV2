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
sys.path.insert(1, f'/home/{os.getlogin()}/ETROC/ETROC_DAQ')
import run_script
import importlib
importlib.reload(run_script)
import signal
import pandas as pd
import time 
from fnmatch import fnmatch
import scipy.stats as stats
import hist

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

    outdir = git_repo
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

def func_fpga_data(
        chip_names,
        fpga_ip = "192.168.2.3",
        time_limit: int = 3,
        th_offset: int = 0x0f,
    ):

    parser = run_script.getOptionParser()

    ## One time to create output file
    rootdir = Path('../ETROC-Data')
    todaydir = rootdir / (datetime.date.today().isoformat() + '_Array_Test_Results')
    outdir_name = '_'.join(chip_names)+'_FPGA_data'
    outdir = todaydir / outdir_name

    if not outdir.is_dir():
        (options, args) = parser.parse_args(args=f"--useIPC --hostname {fpga_ip} -o {outdir_name} -v -w --reset_till_trigger_linked --counter_duration 0x0001 --fpga_data_time_limit {time_limit} --fpga_data --nodaq --DAC_Val {th_offset} -s 0x0000 -d 0x1800 -a 0x0011".split())
        IPC_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'main_process_fpga_data'))
        process.start()
        process.join()

    (options, args) = parser.parse_args(args=f"--useIPC --hostname {fpga_ip} -o {outdir_name} -v --reset_till_trigger_linked --counter_duration 0x0001 --fpga_data_time_limit {time_limit} --fpga_data --nodaq --DAC_Val {th_offset}".split())
    IPC_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'main_process_fpga_data'))
    process.start()
    process.join()

    del IPC_queue, process, parser

def pixel_turnon_points(i2c_conn, hostname, chip_address, chip_figname, s_flag, d_flag, a_flag, p_flag, scan_list, verbose=False, attempt='', today='', calibrate=False):
    scan_name = chip_figname+"_VRef_SCurve_BinarySearch_TurnOn"
    fpga_time = 3

    if(today==''): today = datetime.date.today()
    todaystr = "../ETROC-Data/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)

    BL_map_THCal,NW_map_THCal,_ = i2c_conn.get_auto_cal_maps(chip_address)
    for row, col in tqdm(scan_list, leave=False):
        turnon_point = -1
        if(calibrate):
            i2c_conn.auto_cal_pixel(chip_name=chip_figname, row=row, col=col, verbose=False, chip_address=chip_address, chip=None, data=None, row_indexer_handle=None, column_indexer_handle=None)
            i2c_conn.disable_pixel(row, col, verbose=False, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
        i2c_conn.enable_pixel_data_qinj(row=row, col=col, verbose=verbose, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
        pixel_connected_chip = i2c_conn.get_pixel_chip(chip_address, row, col)
        threshold_name = scan_name+f'_Pixel_C{col}_R{row}'+attempt
        parser = run_script.getOptionParser()
        (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {hostname} -o {threshold_name} -v -w --reset_till_trigger_linked -s {s_flag} -d {d_flag} -a {a_flag} -p {p_flag} --counter_duration 0x0001 --fpga_data_time_limit {int(fpga_time)} --fpga_data_QInj --check_trigger_link_at_end --nodaq".split())
        IPC_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_link'))
        process.start()
        process.join()

        a = 0
        b = BL_map_THCal[row][col] + (3*NW_map_THCal[row][col])
        while b-a>1:
            DAC = int(np.floor((a+b)/2))
            # Set the DAC to the value being scanned
            i2c_conn.pixel_decoded_register_write("DAC", format(DAC, '010b'), pixel_connected_chip)
            (options, args) = parser.parse_args(args=f"--useIPC --hostname {hostname} -o {threshold_name} -v --reset_till_trigger_linked --counter_duration 0x0001 --fpga_data_time_limit {int(fpga_time)} --fpga_data_QInj --check_trigger_link_at_end --nodaq --DAC_Val {int(DAC)}".split())
            IPC_queue = multiprocessing.Queue()
            process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_{DAC}'))
            process.start()
            process.join()
            
            continue_flag = False
            root = '../ETROC-Data'
            file_pattern = "*FPGA_Data.dat"
            path_pattern = f"*{today.isoformat()}_Array_Test_Results/{threshold_name}"
            file_list = []
            for path, subdirs, files in os.walk(root):
                if not fnmatch(path, path_pattern): continue
                for name in files:
                    pass
                    if fnmatch(name, file_pattern):
                        file_list.append(os.path.join(path, name))
            for file_index, file_name in enumerate(file_list):
                with open(file_name) as infile:
                    lines = infile.readlines()
                    last_line = lines[-1]
                    first_line = lines[0]
                    text_list = last_line.split(',')
                    FPGA_state = text_list[0]
                    line_DAC = int(text_list[-1])
                    if(FPGA_state==0 or line_DAC!=DAC): 
                        continue_flag=True
                        continue
                    TDC_tb = int(text_list[-2])
                    turnon_point = line_DAC
                    # Condition handling for Binary Search
                    if(TDC_tb>0):
                        b = DAC
                    else:
                        a = DAC                    
            if(continue_flag): continue  
        i2c_conn.disable_pixel(row=row, col=col, verbose=verbose, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
        if(verbose): print(f"Turn-On point for Pixel ({row},{col}) for chip {hex(chip_address)} is found to be DAC:{turnon_point}")
        del IPC_queue, process, parser, pixel_connected_chip

def trigger_bit_noisescan(i2c_conn, hostname, chip_address, chip_figtitle, chip_figname, s_flag, d_flag, a_flag, p_flag, scan_list, verbose=False, pedestal_scan_step = 1, attempt='', today='', busyCB=False, tp_tag='', neighbors=False):
    root = '../ETROC-Data'
    file_pattern = "*FPGA_Data.dat"
    thresholds = np.arange(-5,20,pedestal_scan_step) # relative to BL
    scan_name = chip_figname+"_VRef_SCurve_NoiseOnly"
    fpga_time = 3
    if(today==''): today = datetime.date.today()
    todaystr = root+"/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)
    # BL_map_THCal,NW_map_THCal,_ = i2c_conn.get_auto_cal_maps(chip_address)
    for row,col in scan_list:
        turnon_point = -1
        path_pattern = f"*{today.isoformat()}_Array_Test_Results/{chip_figname}_VRef_SCurve_BinarySearch_TurnOn_Pixel_C{col}_R{row}"+tp_tag
        file_list = []
        for path, subdirs, files in os.walk(root):
            if not fnmatch(path, path_pattern): continue
            for name in files:
                pass
                if fnmatch(name, file_pattern):
                    file_list.append(os.path.join(path, name))
        for file_index, file_name in enumerate(file_list):
            with open(file_name) as infile:
                lines = infile.readlines()
                last_line = lines[-1]
                text_list = last_line.split(',')
                line_DAC = int(text_list[-1])
                turnon_point = line_DAC
        if(busyCB):
            i2c_conn.enable_pixel_data(row=row, col=col, verbose=verbose, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
        else:
            i2c_conn.enable_pixel_triggerbit(row=row, col=col, verbose=verbose, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
        if(neighbors):
            for first_idx in range(-1,2):
                row_nb = row+first_idx
                if(row_nb>15 or row_nb<0): continue
                for second_idx in range(-1,2):
                    col_nb = col+second_idx
                    if(col_nb>15 or col_nb<0): continue
                    if(col_nb==col and row_nb == row): continue
                    i2c_conn.enable_pixel_data(row=row_nb, col=col_nb, verbose=verbose, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
        pixel_connected_chip = i2c_conn.get_pixel_chip(chip_address, row, col)
        threshold_name = scan_name+f'_Pixel_C{col}_R{row}'+attempt
        parser = run_script.getOptionParser()
        (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {hostname} -o {threshold_name} -v -w --reset_till_trigger_linked --counter_duration 0x0001 --fpga_data_time_limit {int(fpga_time)} --fpga_data --check_trigger_link_at_end --nodaq -s {s_flag} -d {d_flag} -a {a_flag} -p {p_flag}".split())
        IPC_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_noiseOnly'))
        process.start()
        process.join()
        
        for DAC in tqdm(thresholds, desc=f'DAC Loop for Chip {hex(chip_address)} Pixel ({row},{col})', leave=False):
        # for DAC in thresholds:
            threshold = int(DAC+turnon_point)
            if threshold < 1:
                threshold = 1
            # triggerbit_full_Scurve[row][col][threshold] = 0
            i2c_conn.pixel_decoded_register_write("DAC", format(threshold, '010b'), pixel_connected_chip)
            (options, args) = parser.parse_args(args=f"--useIPC --hostname {hostname} -o {threshold_name} -v --reset_till_trigger_linked --counter_duration 0x0001 --fpga_data_time_limit {int(fpga_time)} --fpga_data --check_trigger_link_at_end --nodaq --DAC_Val {int(threshold)}".split())
            IPC_queue = multiprocessing.Queue()
            process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_NoiseOnly_{threshold}'))
            process.start()
            process.join()
            
        i2c_conn.disable_pixel(row=row, col=col, verbose=verbose, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
        if(neighbors):
            for first_idx in range(-1,2):
                row_nb = row+first_idx
                if(row_nb>15 or row_nb<0): continue
                for second_idx in range(-1,2):
                    col_nb = col+second_idx
                    if(col_nb>15 or col_nb<0): continue
                    if(col_nb==col and row_nb == row): continue
                    i2c_conn.disable_pixel(row=row_nb, col=col_nb, verbose=verbose, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
        del IPC_queue, process, parser, pixel_connected_chip

def trigger_bit_noisescan_plot(i2c_conn, chip_address, chip_figtitle, chip_figname, scan_list, attempt='', today='', autoBL=False, gaus=True, tag=''):
    root = '../ETROC-Data'
    file_pattern = "*FPGA_Data.dat"
    scan_name = chip_figname+"_VRef_SCurve_NoiseOnly"
    if(autoBL): BL_map_THCal,NW_map_THCal,_ = i2c_conn.get_auto_cal_maps(chip_address)
    triggerbit_full_Scurve = {row:{col:{} for col in range(16)} for row in range(16)}

    if(today==''): today = datetime.date.today()
    todaystr = root+"/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)

    fig_outdir = Path('../ETROC-figures')
    fig_outdir = fig_outdir / (today.isoformat() + '_Array_Test_Results')
    fig_outdir.mkdir(exist_ok=True)
    fig_path = str(fig_outdir)
    
    for row,col in scan_list:
        path_pattern = f"*{today.isoformat()}_Array_Test_Results/{scan_name}_Pixel_C{col}_R{row}"+attempt
        file_list = []
        for path, subdirs, files in os.walk(root):
            if not fnmatch(path, path_pattern): continue
            for name in files:
                pass
                if fnmatch(name, file_pattern):
                    file_list.append(os.path.join(path, name))
        for file_index, file_name in enumerate(file_list):
            with open(file_name) as infile:
                for line in infile:
                    text_list = line.split(',')
                    FPGA_triggerbit = int(text_list[5])
                    DAC = int(text_list[-1])
                    if DAC == -1: continue
                    triggerbit_full_Scurve[row][col][DAC] = FPGA_triggerbit
    row_list, col_list = zip(*scan_list)
    u_cl = np.sort(np.unique(col_list))
    u_rl = np.sort(np.unique(row_list))

    fig = plt.figure(dpi=200, figsize=(len(np.unique(u_cl))*5,len(np.unique(u_rl))*5))
    gs = fig.add_gridspec(len(np.unique(u_rl)),len(np.unique(u_cl)))
    for ri,row in enumerate(u_rl):
        for ci,col in enumerate(u_cl):
            Y = np.array(list(triggerbit_full_Scurve[row][col].values()))
            X = np.array(list(triggerbit_full_Scurve[row][col].keys()))
            ax0 = fig.add_subplot(gs[len(u_rl)-ri-1,len(u_cl)-ci-1])
            ax0.plot(X, Y, '.-', color='b',lw=0.5,markersize=2)
            ax0.set_xlabel("DAC Value [decimal]")
            ax0.set_ylabel("Trigger Bit Counts [decimal]")
            max_y_point = np.amax(Y)
            max_x_point = X[np.argmax(Y)]
            fwhm_key_array  = X[Y>.0000037*max_y_point]
            fwhm_val_array  = Y[Y>.0000037*max_y_point]
            left_index  = np.argmin(np.where(Y>.0000037*max_y_point,X,np.inf))-1
            right_index = np.argmax(np.where(Y>.0000037*max_y_point,X,-np.inf))+1
            ax0.set_xlim(left=max_x_point-20, right=max_x_point+20)
            if(gaus):
                ax0.plot([max_x_point, max_x_point], [0, max_y_point], 'w-', label=f"Max at {max_x_point}", lw=0.7)
                ax0.plot([X[left_index], X[right_index]], [Y[left_index], Y[right_index]], color='w', ls='--', label=f"99.9996% width = {(X[right_index]-X[left_index])/2.}", lw=0.7)
            if(autoBL):
                ax0.axvline(BL_map_THCal[row][col], color='k', label=f"AutoBL = {BL_map_THCal[row][col]}", lw=0.7)
                ax0.axvline(BL_map_THCal[row][col]+NW_map_THCal[row][col], color='k', ls='--', label=f"AutoNW = $\pm${NW_map_THCal[row][col]}", lw=0.7)
                ax0.axvline(BL_map_THCal[row][col]-NW_map_THCal[row][col], color='k', ls='--', lw=0.7)
            if(gaus or autoBL): plt.legend(loc="upper right", fontsize=6)
            plt.yscale("log")
            plt.title(f"{chip_figtitle}, Pixel ({row},{col}) Noise Peak"+tag,size=10)
            plt.tight_layout()
    plt.savefig(fig_path+"/"+chip_figname+"_NoisePeak_Log"+attempt+"_"+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")+".png")
    plt.close()

    fig = plt.figure(dpi=200, figsize=(len(np.unique(u_cl))*5,len(np.unique(u_rl))*5))
    gs = fig.add_gridspec(len(np.unique(u_rl)),len(np.unique(u_cl)))
    for ri,row in enumerate(u_rl):
        for ci,col in enumerate(u_cl):
            Y = np.array(list(triggerbit_full_Scurve[row][col].values()))
            X = np.array(list(triggerbit_full_Scurve[row][col].keys()))
            ax0 = fig.add_subplot(gs[len(u_rl)-ri-1,len(u_cl)-ci-1])
            ax0.plot(X, Y, '.-', color='b',lw=0.5,markersize=2)
            ax0.set_xlabel("DAC Value [decimal]")
            ax0.set_ylabel("Trigger Bit Counts [decimal]")
            max_y_point = np.amax(Y)
            max_x_point = X[np.argmax(Y)]
            fwhm_key_array  = X[Y>.0000037*max_y_point]
            fwhm_val_array  = Y[Y>.0000037*max_y_point]
            left_index  = np.argmin(np.where(Y>.0000037*max_y_point,X,np.inf))-1
            right_index = np.argmax(np.where(Y>.0000037*max_y_point,X,-np.inf))+1
            ax0.set_xlim(left=max_x_point-20, right=max_x_point+20)
            if(gaus):
                ax0.plot([max_x_point, max_x_point], [0, max_y_point], 'w-', label=f"Max at {max_x_point}", lw=0.7)
                ax0.plot([X[left_index], X[right_index]], [Y[left_index], Y[right_index]], color='w', ls='--', label=f"99.9996% width = {(X[right_index]-X[left_index])/2.}", lw=0.7)
            if(autoBL):
                ax0.axvline(BL_map_THCal[row][col], color='k', label=f"AutoBL = {BL_map_THCal[row][col]}", lw=0.7)
                ax0.axvline(BL_map_THCal[row][col]+NW_map_THCal[row][col], color='k', ls='--', label=f"AutoNW = $\pm${NW_map_THCal[row][col]}", lw=0.7)
                ax0.axvline(BL_map_THCal[row][col]-NW_map_THCal[row][col], color='k', ls='--', lw=0.7)
            if(gaus or autoBL): plt.legend(loc="upper right", fontsize=6)
            plt.yscale("linear")
            plt.title(f"{chip_figtitle}, Pixel ({row},{col}) Noise Peak"+tag,size=10)
            plt.tight_layout()
    plt.savefig(fig_path+"/"+chip_figname+"_NoisePeak_Linear"+attempt+"_"+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")+".png")
    plt.close()
    del triggerbit_full_Scurve

def trigger_bit_noisescan_plot_autoCalVaried(i2c_conn, chip_address, chip_figtitle, chip_figname, scan_list):
    root = '../ETROC-Data'
    file_pattern = "*FPGA_Data.dat"
    scan_name = chip_figname+"_VRef_SCurve_NoiseOnly"
    # BL_map_THCal,NW_map_THCal,_ = i2c_conn.get_auto_cal_maps(chip_address)
    triggerbit_full_Scurve = {row:{col:{} for col in range(16)} for row in range(16)}

    today = datetime.date.today()
    todaystr = root+"/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)
    
    fig_outdir = Path('../ETROC-figures')
    fig_outdir = fig_outdir / (today.isoformat() + '_Array_Test_Results')
    fig_outdir.mkdir(exist_ok=True)
    fig_path = str(fig_outdir)

    for row,col in scan_list:
        path_pattern = f"*{today.isoformat()}_Array_Test_Results/{scan_name}_Pixel_C{col}_R{row}"
        file_list = []
        for path, subdirs, files in os.walk(root):
            if not fnmatch(path, path_pattern): continue
            for name in files:
                pass
                if fnmatch(name, file_pattern):
                    file_list.append(os.path.join(path, name))
        for file_index, file_name in enumerate(file_list):
            with open(file_name) as infile:
                for line in infile:
                    text_list = line.split(',')
                    FPGA_triggerbit = int(text_list[5])
                    DAC = int(text_list[-1])
                    if DAC == -1: continue
                    triggerbit_full_Scurve[row][col][DAC] = FPGA_triggerbit
    row_list, col_list = zip(*scan_list)
    u_cl = np.sort(np.unique(col_list))
    u_rl = np.sort(np.unique(row_list))
    fig = plt.figure(dpi=200, figsize=(len(np.unique(u_cl))*5,len(np.unique(u_rl))*5))
    gs = fig.add_gridspec(len(np.unique(u_rl)),len(np.unique(u_cl)))
    for ri,row in enumerate(u_rl):
        for ci,col in enumerate(u_cl):
            ax0 = fig.add_subplot(gs[len(u_rl)-ri-1,len(u_cl)-ci-1])
            # i2c_conn.open_TDC_pixel(chip_address, row, col, verbose=True, chip=None, row_indexer_handle=None, column_indexer_handle=None, alreadySetPixel=False)
            # i2c_conn.enable_pixel(row, col, verbose=True, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
            i2c_conn.disable_pixel(row, col, verbose=True, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
            for attempt in range(10):
                i2c_conn.auto_cal_pixel(chip_figname, row, col, verbose=True, chip_address=chip_address, chip=None, data=None, row_indexer_handle=None, column_indexer_handle=None)
                BL_map_THCal,NW_map_THCal,_ = i2c_conn.get_auto_cal_maps(chip_address)
                ax0.axvline(BL_map_THCal[row][col], color='k', label=f"AutoBL = {BL_map_THCal[row][col]}", lw=0.7)
                # ax0.axvline(BL_map_THCal[row][col]+NW_map_THCal[row][col], color='r', ls='-', label=f"AutoNW = $\pm${NW_map_THCal[row][col]}", lw=0.7)
                # ax0.axvline(BL_map_THCal[row][col]-NW_map_THCal[row][col], color='r', ls='-', lw=0.7)
            # i2c_conn.close_TDC_pixel(chip_address, row, col, verbose=True, chip=None, row_indexer_handle=None, column_indexer_handle=None, alreadySetPixel=False)
            i2c_conn.disable_pixel(row, col, verbose=True, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
            ax0.plot(triggerbit_full_Scurve[row][col].keys(), triggerbit_full_Scurve[row][col].values(), '.-', color='b',lw=0.5,markersize=2)
            ax0.set_xlabel("DAC Value [decimal]")
            ax0.set_ylabel("Trigger Bit Counts [decimal]")
            max_x_point = np.array(list(triggerbit_full_Scurve[row][col].keys()))[np.argmax(np.array(list(triggerbit_full_Scurve[row][col].values())))]
            ax0.set_xlim(left=max_x_point-20, right=max_x_point+20)
            plt.legend(loc="upper right")
            plt.yscale("linear")
            plt.title(f"{chip_figtitle}, Pixel ({row},{col}) Noise Only S-Curve AutoCalTDCoff CBff PxOff",size=8)
            plt.tight_layout()
    plt.savefig(fig_path+"/"+chip_figname+"_NoiseOnly_S-Curve_autoCalVaried_TDCEnabled_"+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")+".png")
    del triggerbit_full_Scurve

def trigger_bit_noisescan_plot_autoCalVaried_selfTriggered(i2c_conn, hostname, chip_address, chip_figtitle, chip_figname, s_flag, d_flag, a_flag, scan_list):
    root = '../ETROC-Data'
    file_pattern = "*FPGA_Data.dat"
    scan_name = chip_figname+"_VRef_SCurve_NoiseOnly"
    # BL_map_THCal,NW_map_THCal,_ = i2c_conn.get_auto_cal_maps(chip_address)
    triggerbit_full_Scurve = {row:{col:{} for col in range(16)} for row in range(16)}

    today = datetime.date.today()
    todaystr = root+"/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)

    fig_outdir = Path('../ETROC-figures')
    fig_outdir = fig_outdir / (today.isoformat() + '_Array_Test_Results')
    fig_outdir.mkdir(exist_ok=True)
    fig_path = str(fig_outdir)
    
    for row,col in scan_list:
        path_pattern = f"*{today.isoformat()}_Array_Test_Results/{scan_name}_Pixel_C{col}_R{row}"
        file_list = []
        for path, subdirs, files in os.walk(root):
            if not fnmatch(path, path_pattern): continue
            for name in files:
                pass
                if fnmatch(name, file_pattern):
                    file_list.append(os.path.join(path, name))
        for file_index, file_name in enumerate(file_list):
            with open(file_name) as infile:
                for line in infile:
                    text_list = line.split(',')
                    FPGA_triggerbit = int(text_list[5])
                    DAC = int(text_list[-1])
                    if DAC == -1: continue
                    triggerbit_full_Scurve[row][col][DAC] = FPGA_triggerbit
    row_list, col_list = zip(*scan_list)
    u_cl = np.sort(np.unique(col_list))
    u_rl = np.sort(np.unique(row_list))
    fig = plt.figure(dpi=200, figsize=(len(np.unique(u_cl))*5,len(np.unique(u_rl))*5))
    gs = fig.add_gridspec(len(np.unique(u_rl)),len(np.unique(u_cl)))
    for ri,row in enumerate(u_rl):
        for ci,col in enumerate(u_cl):
            ax0 = fig.add_subplot(gs[len(u_rl)-ri-1,len(u_cl)-ci-1])
            # i2c_conn.open_TDC_pixel(chip_address, row, col, verbose=True, chip=None, row_indexer_handle=None, column_indexer_handle=None, alreadySetPixel=False)
            i2c_conn.enable_pixel(row, col, verbose=True, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
            parser = run_script.getOptionParser()
            (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {hostname} -o CanRemove -v -w --reset_till_trigger_linked --counter_duration 0x0001 --nodaq -s {s_flag} -d {int('000111'+format(485, '010b'), base=2)} -a {a_flag} -p 0x000b".split())
            IPC_queue = multiprocessing.Queue()
            process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_test'))
            process.start()
            process.join()
            del IPC_queue
            for attempt in range(10):
                i2c_conn.auto_cal_pixel_TDCon(chip_figname, row, col, verbose=True, chip_address=chip_address, chip=None, data=None, row_indexer_handle=None, column_indexer_handle=None)
                BL_map_THCal,NW_map_THCal,_ = i2c_conn.get_auto_cal_maps(chip_address)
                ax0.axvline(BL_map_THCal[row][col], color='k', label=f"AutoBL = {BL_map_THCal[row][col]}", lw=0.7)
                # ax0.axvline(BL_map_THCal[row][col]+NW_map_THCal[row][col], color='r', ls='-', label=f"AutoNW = $\pm${NW_map_THCal[row][col]}", lw=0.7)
                # ax0.axvline(BL_map_THCal[row][col]-NW_map_THCal[row][col], color='r', ls='-', lw=0.7)
            # i2c_conn.close_TDC_pixel(chip_address, row, col, verbose=True, chip=None, row_indexer_handle=None, column_indexer_handle=None, alreadySetPixel=False)
            i2c_conn.disable_pixel(row, col, verbose=True, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
            (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {hostname} -o CanRemove -v -w --reset_till_trigger_linked --counter_duration 0x0001 --nodaq -s {s_flag} -d {d_flag} -a {a_flag} -p 0x000b".split())
            IPC_queue = multiprocessing.Queue()
            process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_test'))
            process.start()
            process.join()
            ax0.plot(triggerbit_full_Scurve[row][col].keys(), triggerbit_full_Scurve[row][col].values(), '.-', color='b',lw=0.5,markersize=2)
            ax0.set_xlabel("DAC Value [decimal]")
            ax0.set_ylabel("Trigger Bit Counts [decimal]")
            max_x_point = np.array(list(triggerbit_full_Scurve[row][col].keys()))[np.argmax(np.array(list(triggerbit_full_Scurve[row][col].values())))]
            ax0.set_xlim(left=max_x_point-20, right=max_x_point+20)
            plt.legend(loc="upper right")
            plt.yscale("linear")
            plt.title(f"{chip_figtitle}, Pixel ({row},{col}) Noise Only S-Curve AutoCalTDCon CBon PxEn SelfTrig",size=8)
            plt.tight_layout()
    plt.savefig(fig_path+"/"+chip_figname+"_NoiseOnly_S-Curve_autoCalVaried_TDCEnabled_"+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")+".png")
    del triggerbit_full_Scurve, IPC_queue, parser, process

def pixel_turnoff_points(i2c_conn, hostname, chip_address, chip_figname, s_flag, d_flag, a_flag, scan_list, verbose=False, QInjEns=[27]):
    DAC_scan_max = 1020
    scan_name = chip_figname+"_VRef_SCurve_BinarySearch_TurnOff"
    fpga_time = 3

    today = datetime.date.today()
    todaystr = "../ETROC-Data/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)

    BL_map_THCal,_,_ = i2c_conn.get_auto_cal_maps(chip_address)
    for row, col in scan_list:
        i2c_conn.enable_pixel_binarysearch_data(row=row, col=col, verbose=verbose, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
        pixel_connected_chip = i2c_conn.get_pixel_chip(chip_address, row, col)
        for QInj in QInjEns:
            i2c_conn.pixel_decoded_register_write("QSel", format(QInj, '05b'), pixel_connected_chip)
            threshold_name = scan_name+f'_Pixel_C{col}_R{row}_QInj_{QInj}'
            parser = run_script.getOptionParser()
            (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {hostname} -o {threshold_name} -v -w --reset_till_trigger_linked -s {s_flag} -d {d_flag} -a {a_flag} -p 0x000b --counter_duration 0x0001 --fpga_data_time_limit {int(fpga_time)} --fpga_data_QInj --check_trigger_link_at_end --nodaq --clear_fifo".split())
            IPC_queue = multiprocessing.Queue()
            process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_link'))
            process.start()
            process.join()

            a = BL_map_THCal[row][col]
            b = DAC_scan_max
            header_max = -1
            while b-a>1:
                DAC = int(np.floor((a+b)/2))
                # Set the DAC to the value being scanned
                i2c_conn.pixel_decoded_register_write("DAC", format(DAC, '010b'), pixel_connected_chip)
                (options, args) = parser.parse_args(args=f"--useIPC --hostname {hostname} -o {threshold_name} -v --reset_till_trigger_linked --counter_duration 0x0001 --fpga_data_time_limit {int(fpga_time)} --fpga_data_QInj --check_trigger_link_at_end --nodaq --DAC_Val {int(DAC)}".split())
                IPC_queue = multiprocessing.Queue()
                process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'process_outputs/main_process_{DAC}'))
                process.start()
                process.join()
                
                continue_flag = False
                root = '../ETROC-Data'
                file_pattern = "*FPGA_Data.dat"
                path_pattern = f"*{today.isoformat()}_Array_Test_Results/{threshold_name}"
                file_list = []
                for path, subdirs, files in os.walk(root):
                    if not fnmatch(path, path_pattern): continue
                    for name in files:
                        pass
                        if fnmatch(name, file_pattern):
                            file_list.append(os.path.join(path, name))
                for file_index, file_name in enumerate(file_list):
                    with open(file_name) as infile:
                        lines = infile.readlines()
                        last_line = lines[-1]
                        first_line = lines[0]
                        header_max = int(first_line.split(',')[4])
                        text_list = last_line.split(',')
                        FPGA_state = text_list[0]
                        line_DAC = int(text_list[-1])
                        if(FPGA_state==0 or line_DAC!=DAC): 
                            continue_flag=True
                            continue
                        TDC_data = int(text_list[3])
                        # Condition handling for Binary Search
                        if(TDC_data>=header_max/2.):
                            a = DAC
                        else:
                            b = DAC                     
                if(continue_flag): continue  
        i2c_conn.disable_pixel(row=row, col=col, verbose=verbose, chip_address=chip_address, chip=None, row_indexer_handle=None, column_indexer_handle=None)
        print(f"Turn-Off points for Pixel ({row},{col}) for chip {hex(chip_address)} were found")
        del parser, IPC_queue, process, pixel_connected_chip

def charge_peakDAC_plot(i2c_conn, chip_address, chip_figtitle, chip_figname, scan_list, QInjEns):
    root = '../ETROC-Data'
    file_pattern = "*FPGA_Data.dat"
    scan_name = chip_figname+"_VRef_SCurve_BinarySearch_TurnOff"
    BL_map_THCal,NW_map_THCal,_ = i2c_conn.get_auto_cal_maps(chip_address)
    QInj_Peak_DAC_map = {row:{col:{q:0 for q in QInjEns} for col in range(16)} for row in range(16)}

    today = datetime.date.today()
    todaystr = root+"/" + today.isoformat() + "_Array_Test_Results/"
    base_dir = Path(todaystr)
    base_dir.mkdir(exist_ok=True)

    fig_outdir = Path('../ETROC-figures')
    fig_outdir = fig_outdir / (today.isoformat() + '_Array_Test_Results')
    fig_outdir.mkdir(exist_ok=True)
    fig_path = str(fig_outdir)
    
    for row,col in scan_list:
        for QInj in QInjEns:
            threshold_name = scan_name+f'_Pixel_C{col}_R{row}_QInj_{QInj}'
            path_pattern = f"*{today.isoformat()}_Array_Test_Results/{threshold_name}"
            file_list = []
            for path, subdirs, files in os.walk(root):
                if not fnmatch(path, path_pattern): continue
                for name in files:
                    pass
                    if fnmatch(name, file_pattern):
                        file_list.append(os.path.join(path, name))
            for file_index, file_name in enumerate(file_list):
                with open(file_name) as infile:
                    last_line = infile.readlines()[-1]
                    text_list = last_line.split(',')
                    DAC = int(text_list[-1])
                    QInj_Peak_DAC_map[row][col][QInj] = DAC

    row_list, col_list = zip(*scan_list)
    u_cl = np.sort(np.unique(col_list))
    u_rl = np.sort(np.unique(row_list))
    fig = plt.figure(dpi=200, figsize=(len(np.unique(u_cl))*7,len(np.unique(u_rl))*5))
    gs = fig.add_gridspec(len(np.unique(u_rl)),len(np.unique(u_cl)))
    for ri,row in enumerate(u_rl):
        for ci,col in enumerate(u_cl):
            BL = int(np.floor(BL_map_THCal[row][col]))
            NW = abs(int(np.floor(NW_map_THCal[row][col])))
            ax0 = fig.add_subplot(gs[len(u_rl)-ri-1,len(u_cl)-ci-1])
            ax0.axhline(BL, color='k', lw=0.8, label=f"BL = {BL} DAC LSB")
            ax0.axhline(BL+NW, color='k',ls="--", lw=0.8, label=f"NW = $\pm${NW} DAC LSB")
            ax0.axhline(BL-NW, color='k',ls="--", lw=0.8)
            X = []
            Y = []
            for QInj in QInjEns:
                ax0.plot(QInj, QInj_Peak_DAC_map[row][col][QInj], 'rx')
                X.append(QInj)
                Y.append(QInj_Peak_DAC_map[row][col][QInj])
            X = np.array(X[:])
            Y = np.array(Y[:])
            (m, b), cov = np.polyfit(X, Y, 1, cov = True)
            n = Y.size
            Yfit = np.polyval((m,b), X)
            errorbars = np.sqrt(np.diag(cov))
            x_range = np.linspace(0, 35, 100)
            y_est = b + m*x_range
            resid = Y - Yfit
            s_err = np.sqrt(np.sum(resid**2)/(n - 2))
            t = stats.t.ppf(0.95, n - 2)
            ci2= t * s_err * np.sqrt(    1/n + (x_range - np.mean(X))**2/(np.sum((X)**2)-n*np.sum((np.mean(X))**2)))
            
            ax0.plot(x_range, y_est, 'b-', lw=-.8, label=f"DAC_TH = ({m:.3f}$\pm${errorbars[0]:.3f} [1/fC])$\cdot$Q + ({b:.3f}$\pm${errorbars[1]:.3f})")
            plt.fill_between(x_range, y_est+ci2, y_est-ci2, color='b',alpha=0.2, label="95% Confidence Interval on Linear Fit")
            ax0.set_xlabel("Charge Injected [fC]")
            ax0.set_ylabel("DAC Threshold [LSB]")
            plt.title(f"{chip_figtitle}, Pixel ({row},{col}) Qinj Sensitivity Plot",size=10)
            plt.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(fig_path+"/"+chip_figname+"_QInj_Sensitivity_"+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")+".png")
    del QInj_Peak_DAC_map

def run_scans(
        chip_names: list,
        chip_addresses: list,
        extra_str,
        i2c_port = "/dev/ttyACM0",
        fpga_ip = "192.168.2.3",
        th_offset = 0x18,
        do_fullAutoCal: bool = False,
        do_saveHistory: bool = False,
        do_skipConfig: bool = False,
        do_skipCalibration: bool = False,
        do_skipLEDCheck: bool = False,
        do_Counter: bool = False,
        do_pixel_turnon_points: bool = False,
        do_trigger_bit_noisescan_quietCB: bool = False,
        do_trigger_bit_noisescan_activeCB: bool = False,
        do_trigger_bit_noisescan_activeCBwNB: bool = False,
        do_trigger_bit_noisescan_plot_quietCB: bool = False,
        do_trigger_bit_noisescan_plot_activeCB: bool = False,
        do_trigger_bit_noisescan_plot_activeCBwNB: bool = False,
        do_trigger_bit_noisescan_plot_autoCalVaried: bool = False,
        do_trigger_bit_noisescan_plot_autoCalVaried_selfTriggered: bool = False,
        do_pixel_turnoff_points: bool = False,
        do_charge_peakDAC_plot: bool = False
    ):
    # It is very important to correctly set the chip name, this value is stored with the data
    chip_fignames = f'{chip_names}_{extra_str}'
    chip_fignames = f'{extra_str}_'+'_'.join(chip_names)
    chip_figtitles = chip_fignames

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

    QInjEns = [5, 6, 8, 15, 22, 27]

    # Config chips
    ### Key is (Disable Pixels, Auto Cal, Chip Peripherals, Basic Peri Reg Check, Pixel Check)
    # 0 - 0 - (disable & auto_cal all pixels) - (disable default all pixels) - (auto_TH_CAL) - (set basic peripherals) - (peripheral reg check) -  (pixel ID check)
    if not do_skipConfig:
        i2c_conn.config_chips('00001111')

    # Define pixels of interest
    row_list = [14, 14, 14, 14]
    col_list = [6, 7, 8, 9]
    scan_list = list(zip(row_list, col_list))

    if not do_skipConfig:
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
                plt.savefig(fig_path+"/BL_NW_"+chip_name+"_"+datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")+".png")

            full_BL_df = pd.concat(frames)
            if do_saveHistory:
                push_history_to_git(full_BL_df, f'{extra_str}', 'ETROC-History-Cosmic')

            col_list, row_list = np.meshgrid(np.arange(16), np.arange(16))
            scan_list = list(zip(row_list.flatten(), col_list.flatten()))

        else:
            tmp_data = []
            for chip_address, chip_name in zip(chip_addresses, chip_names):
                for row, col in scan_list:
                    i2c_conn.auto_cal_pixel(chip_name=chip_name, row=row, col=col, verbose=False, chip_address=chip_address, chip=None, data=tmp_data, row_indexer_handle=None, column_indexer_handle=None)
            BL_df = pandas.DataFrame(data = tmp_data)
            if do_saveHistory:
                push_history_to_git(BL_df, f'{extra_str}', 'ETROC-History-Cosmic')

    ### Enable pixels of Interest
    if not do_skipConfig:
        i2c_conn.enable_select_pixels_in_chips(scan_list)

    offset = th_offset
    for chip_address in chip_addresses[:]:
        chip = i2c_conn.get_chip_i2c_connection(chip_address)
        row_indexer_handle,_,_ = chip.get_indexer("row")
        column_indexer_handle,_,_ = chip.get_indexer("column")
        if do_skipConfig:
            col_list, row_list = np.meshgrid(np.arange(16), np.arange(16))
            scan_list = list(zip(row_list.flatten(), col_list.flatten()))
        for row, col in scan_list:
            print(f"Operating on chip {hex(chip_address)} Pixel ({row},{col})")
            column_indexer_handle.set(col)
            row_indexer_handle.set(row)
            i2c_conn.pixel_decoded_register_write("TH_offset", format(offset, '06b'), chip)
            i2c_conn.pixel_decoded_register_write("QInjEn", "0", chip)
        del chip, row_indexer_handle, column_indexer_handle

    if not do_skipCalibration:
        # Calibrate PLL
        for chip_address in chip_addresses[:]:
            i2c_conn.calibratePLL(chip_address, chip=None)

        # Calibrate FC
        for chip_address in chip_addresses[:]:
            i2c_conn.asyResetGlobalReadout(chip_address, chip=None)
            i2c_conn.asyAlignFastcommand(chip_address, chip=None)

    # plzDelDir = data_outdir / 'PlzDelete_Board013_NoLinkCheck'
    # if not plzDelDir.is_dir():
    print('\nOne time DAQ run for checking LED lights')
    # Run One Time DAQ to Set FPGA Firmware
    parser = run_script.getOptionParser()
    (options, args) = parser.parse_args(args=f"-f --useIPC --hostname {fpga_ip} -t 15 -o PlzDelete_Board013_NoLinkCheck -v -w -s 0x0000 -p 0x000b -d 0x0800 -a 0x0011 --clear_fifo".split())
    IPC_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=run_script.main_process, args=(IPC_queue, options, f'main_process_Start_LEDs_Board013_NoLinkCheck'))
    process.start()

    IPC_queue.put('memoFC Start Triggerbit QInj L1A')
    while not IPC_queue.empty():
        pass
    time.sleep(8)
    IPC_queue.put('stop DAQ')
    IPC_queue.put('memoFC Triggerbit')
    while not IPC_queue.empty():
        pass
    IPC_queue.put('allow threads to exit')
    process.join()
    del IPC_queue, process, parser
    
    print('\nFinished one time DAQ run for checking LED lights \n')
    # hold for keyboard input
    if not do_skipLEDCheck:
        input("Are LEDs looking okay? Press the Enter key to continue: ")

    for chip_address,chip_figname,chip_figtitle in zip(chip_addresses,chip_fignames,chip_figtitles):
        if chip_address is None: continue
        if do_Counter:
            print("Running do_Counter")
            func_fpga_data(
                chip_names = chip_names,
                fpga_ip = fpga_ip,   
            )
        if do_pixel_turnon_points:
            print("Running pixel_turnon_points")
            pixel_turnon_points(
                i2c_conn, fpga_ip,
                chip_address, chip_figname, 
                "0x0000", "0x1800", "0x0011", "0x000b", 
                scan_list, 
                verbose=False, 
                calibrate=True
            )
        if do_trigger_bit_noisescan_quietCB:
            print("Running do_trigger_bit_noisescan_quietCB")
            trigger_bit_noisescan(
                i2c_conn, fpga_ip,
                chip_address, chip_figtitle, chip_figname, 
                "0x0000", "0x1800", "0x0011", '0x000b', 
                scan_list, 
                verbose=False, 
                pedestal_scan_step = 1, attempt='_quietCB', busyCB=False
            )
        if do_trigger_bit_noisescan_activeCB:
            print("Running do_trigger_bit_noisescan_activeCB")
            trigger_bit_noisescan(
                i2c_conn, fpga_ip,
                chip_address, chip_figtitle, chip_figname, 
                "0x0000", "0x1800", "0x0011", '0x000b', 
                scan_list, 
                verbose=False, 
                pedestal_scan_step = 1, attempt='_activeCB', busyCB=True
            )
        if do_trigger_bit_noisescan_activeCBwNB:
            print("Running do_trigger_bit_noisescan_activeCBwNB")
            trigger_bit_noisescan(
                i2c_conn, fpga_ip,
                chip_address, chip_figtitle, chip_figname, 
                "0x0000", "0x1800", "0x0011", '0x000b', 
                scan_list, 
                verbose=False, 
                pedestal_scan_step = 1, attempt='_activeCBwNB', busyCB=True, neighbors=True
            )
        if do_trigger_bit_noisescan_plot_quietCB:
            print("Running do_trigger_bit_noisescan_plot_quietCB")
            trigger_bit_noisescan_plot(
                i2c_conn,
                chip_address, chip_figtitle, chip_figname, 
                scan_list, 
                attempt='_quietCB', tag=" Quiet CB", autoBL=True, gaus=True
            )
        if do_trigger_bit_noisescan_plot_activeCB:
            print("Running do_trigger_bit_noisescan_plot_activeCB")
            trigger_bit_noisescan_plot(
                i2c_conn,
                chip_addresses[0], chip_figtitles[0], chip_fignames[0],
                scan_list,
                attempt='_activeCB', tag=" Active CB", autoBL=True, gaus=True
            )
        if do_trigger_bit_noisescan_plot_activeCBwNB:
            print("Running do_trigger_bit_noisescan_plot_activeCBwNB")
            trigger_bit_noisescan_plot(
                i2c_conn,
                chip_address, chip_figtitle, chip_figname, 
                scan_list,
                attempt='_activeCBwNB', tag=" Active CB w/ Neighbors", autoBL=True, gaus=True
            )
        if do_trigger_bit_noisescan_plot_autoCalVaried:
            print("Running do_trigger_bit_noisescan_plot_autoCalVaried")
            trigger_bit_noisescan_plot_autoCalVaried(
                i2c_conn,
                chip_address, chip_figtitle, chip_figname,
                scan_list
            )
        if do_trigger_bit_noisescan_plot_autoCalVaried_selfTriggered:
            print("Running do_trigger_bit_noisescan_plot_autoCalVaried_selfTriggered")
            trigger_bit_noisescan_plot_autoCalVaried_selfTriggered(
                i2c_conn, fpga_ip,
                chip_address, chip_figtitle, chip_figname, 
                "0x0000", "0x1800", "0x0011", 
                scan_list
            )
        if do_pixel_turnoff_points:
            print("Running do_pixel_turnoff_points")
            pixel_turnoff_points(
                i2c_conn, fpga_ip,
                chip_address, chip_figname, 
                "0x0000", "0x1800", "0x0011", 
                scan_list, 
                verbose=False, 
                QInjEns=QInjEns
            )
        if do_charge_peakDAC_plot:
            print("Running do_charge_peakDAC_plot")
            QInjEns = [5, 6, 8, 15, 22, 27]
            charge_peakDAC_plot(
                i2c_conn,
                chip_address, chip_figtitle, chip_figname, 
                scan_list, 
                QInjEns
            )
        # else:
        #     print('Run mode was not specified. Exit the script and disconnect I2C.')

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
        '--do_skipConfig',
        help = '',
        action = 'store_true',
        dest = 'do_skipConfig',
    )
    parser.add_argument(
        '--do_skipCalibration',
        help = '',
        action = 'store_true',
        dest = 'do_skipCalibration',
    )
    parser.add_argument(
        '--do_skipLEDCheck',
        help = 'skip the user checking step of FPGA LEDs',
        action = 'store_true',
        dest = 'do_skipLEDCheck',
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
        '--do_Counter',
        help = '',
        action = 'store_true',
        dest = 'do_Counter',
    )
    parser.add_argument(
        '--do_pixel_turnon_points',
        help = '',
        action = 'store_true',
        dest = 'do_pixel_turnon_points',
    )
    parser.add_argument(
        '--do_trigger_bit_noisescan_quietCB',
        help = '',
        action = 'store_true',
        dest = 'do_trigger_bit_noisescan_quietCB',
    )
    parser.add_argument(
        '--do_trigger_bit_noisescan_activeCB',
        help = '',
        action = 'store_true',
        dest = 'do_trigger_bit_noisescan_activeCB',
    )
    parser.add_argument(
        '--do_trigger_bit_noisescan_activeCBwNB',
        help = '',
        action = 'store_true',
        dest = 'do_trigger_bit_noisescan_activeCBwNB',
    )
    parser.add_argument(
        '--do_trigger_bit_noisescan_plot_quietCB',
        help = '',
        action = 'store_true',
        dest = 'do_trigger_bit_noisescan_plot_quietCB',
    )
    parser.add_argument(
        '--do_trigger_bit_noisescan_plot_activeCB',
        help = '',
        action = 'store_true',
        dest = 'do_trigger_bit_noisescan_plot_activeCB',
    )
    parser.add_argument(
        '--do_trigger_bit_noisescan_plot_activeCBwNB',
        help = '',
        action = 'store_true',
        dest = 'do_trigger_bit_noisescan_plot_activeCBwNB',
    )
    parser.add_argument(
        '--do_trigger_bit_noisescan_plot_autoCalVaried',
        help = '',
        action = 'store_true',
        dest = 'do_trigger_bit_noisescan_plot_autoCalVaried',
    )
    parser.add_argument(
        '--do_trigger_bit_noisescan_plot_autoCalVaried_selfTriggered',
        help = '',
        action = 'store_true',
        dest = 'do_trigger_bit_noisescan_plot_autoCalVaried_selfTriggered',
    )
    parser.add_argument(
        '--do_pixel_turnoff_points',
        help = '',
        action = 'store_true',
        dest = 'do_pixel_turnoff_points',
    )
    parser.add_argument(
        '--do_charge_peakDAC_plot',
        help = '',
        action = 'store_true',
        dest = 'do_charge_peakDAC_plot',
    )

    args = parser.parse_args()

    full_chip_names = [args.board0_name, args.board1_name, args.board2_name, args.board3_name]
    full_chip_addresses = [args.board0_i2c, args.board1_i2c, args.board2_i2c, args.board3_i2c]

    chip_names = list(filter(lambda item: item is not None, full_chip_names))
    chip_addresses = list(filter(lambda item: item is not None, full_chip_addresses))

    def signal_handler(sig, frame):
        print("Exiting gracefully")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    run_scans(
        chip_names = chip_names,
        chip_addresses = chip_addresses,
        extra_str = args.extra_str,
        i2c_port = "/dev/ttyACM0",
        fpga_ip = "192.168.2.3",
        th_offset = 0x19,
        do_fullAutoCal =  args.fullAutoCal,
        do_saveHistory = args.saveHistory,
        do_skipConfig = args.do_skipConfig,
        do_skipCalibration = args.do_skipCalibration,
        do_skipLEDCheck = args.do_skipLEDCheck,
        do_Counter = args.do_Counter,
        do_pixel_turnon_points = args.do_pixel_turnon_points,
        do_trigger_bit_noisescan_quietCB = args.do_trigger_bit_noisescan_quietCB,
        do_trigger_bit_noisescan_activeCB =  args.do_trigger_bit_noisescan_activeCB,
        do_trigger_bit_noisescan_activeCBwNB = args.do_trigger_bit_noisescan_activeCBwNB,
        do_trigger_bit_noisescan_plot_quietCB = args.do_trigger_bit_noisescan_plot_quietCB,
        do_trigger_bit_noisescan_plot_activeCB = args.do_trigger_bit_noisescan_plot_activeCB,
        do_trigger_bit_noisescan_plot_activeCBwNB = args.do_trigger_bit_noisescan_plot_activeCBwNB,
        do_trigger_bit_noisescan_plot_autoCalVaried = args.do_trigger_bit_noisescan_plot_autoCalVaried,
        do_trigger_bit_noisescan_plot_autoCalVaried_selfTriggered = args.do_trigger_bit_noisescan_plot_autoCalVaried_selfTriggered,
        do_pixel_turnoff_points = args.do_pixel_turnoff_points,
        do_charge_peakDAC_plot = args.do_charge_peakDAC_plot
    )


if __name__ == "__main__":
    main()