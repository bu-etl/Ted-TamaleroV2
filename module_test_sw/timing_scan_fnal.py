#!/usr/bin/env python3

import time
import os
import copy
import glob
from emoji import emojize

from yaml import load
from yaml import CLoader as Loader, CDumper as Dumper
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import get_kcu, load_yaml
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame
from tamalero.Module import Module
from test_module import setup
import argparse

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--configuration', action='store', default='modulev2', choices=['modulev0b', 'modulev1', 'modulev2'], help="Board configuration to be loaded")
    argParser.add_argument('--kcu', action='store', default='192.168.0.10', help="IP Address of KCU105 board")
    argParser.add_argument('--host', action='store', default='localhost', help="Hostname for control hub")
    argParser.add_argument('--module', action='store', default=0, choices=['1','2','3'], help="Module to test")
    argParser.add_argument('--rb', action='store', default=0, type = int, help="")
    argParser.add_argument('--etrocs', action = 'store', nargs = '*', type = int, default = [0], help = 'ETROC to use on a multi-ETROC module')
    argParser.add_argument('--pixel_masks', action='store', nargs = '*', default=['None'], help="Pixel mask to apply")

    args = argParser.parse_args()

    kcu = get_kcu(args.kcu, control_hub=True, host=args.host, verbose=False)
    rb = ReadoutBoard(args.rb, kcu=kcu, config=args.configuration)
    moduleids = [0,0,0]
    # moduleids[int(args.module)-1] = MID
    rb.connect_modules(moduleids=moduleids, hard_reset=True, ext_vref=False)

    rb.enable_external_trigger()

    if len(args.pixel_masks)==1 and args.pixel_masks[0] == 'None':
        args.pixel_masks = ['None']*12
    module, etrocs, masks = setup(rb, args)

    for n, etroc in enumerate(etrocs):
        if not etroc.is_connected():
            print('Skipping ETROC', n+1)
            continue
        else:
            print('Working on ETROC', n+1)

        etroc.physics_config(
            offset = 10, 
            L1Adelay = 100, 
            out_dir = "/home/etl/Test_Stand/ETL_TestingDAQ/Test_Beam_Data/DebugTB", 
            powerMode = "high")
        # isolate(etrocs, n)
        for i in range(500,512):
            first = True
            start_time = time.time()
            print(f"Probing delay {i}")
            etroc.wr_reg("L1Adelay", i, broadcast=True)
            rb.reset_data_error_count()
            kcu.write_node(f"READOUT_BOARD_0.EVENT_CNT_RESET", 0x1)
            while kcu.read_node(f"READOUT_BOARD_0.EVENT_CNT").value()<250:
                time.sleep(0.01)
                if kcu.read_node(f"READOUT_BOARD_0.EVENT_CNT").value()>100 and first:
                    s=time.gmtime(time.time())
                    current=time.strftime("%Y-%m-%d %H:%M:%S", s)
                    print(f"{current} - Received 1000 L1As, still waiting...")
                    first=False
                if time.time() - start_time > 13:
                    print("Have been in the same setting for 2mins, breaking")
                    break


            data_count = rb.read_data_count(elink=0, slave=False)
            trigger_count = kcu.read_node(f"READOUT_BOARD_0.EVENT_CNT").value()
            if data_count > 0:
                print(f"!!! Found data for delay {i} !!!")
            print(i, data_count, trigger_count)
    ### Uncomment if code above fails (not tested during test beam)
    #module = Module(rb, i=1, poke=True)
    #etroc = module.ETROCs[2]

    #for i in range(12,16):
    #    first = True
    #    start_time = time.time()
    #    print(f"Probing delay {i}")
    #    etroc.wr_reg("L1Adelay", i, broadcast=True)
    #    rb.reset_data_error_count()
    #    kcu.write_node(f"READOUT_BOARD_0.EVENT_CNT_RESET", 0x1)
    #    while kcu.read_node(f"READOUT_BOARD_0.EVENT_CNT").value()<5000:
    #        time.sleep(0.01)
    #        if kcu.read_node(f"READOUT_BOARD_0.EVENT_CNT").value()>1000 and first:
    #            s=time.gmtime(time.time())
    #            current=time.strftime("%Y-%m-%d %H:%M:%S", s)
    #            print(f"{current} - Received 1000 L1As, still waiting...")
    #            first=False
    #        if time.time() - start_time > 70:
    #            print("Have been in the same setting for 1mins, breaking")
    #            break


    #    data_count = rb.read_data_count(elink=0, slave=False)
    #    trigger_count = kcu.read_node(f"READOUT_BOARD_0.EVENT_CNT").value()
    #    if data_count > 0:
    #        print(f"!!! Found data for delay {i} !!!")
    #    print(i, data_count, trigger_count)
