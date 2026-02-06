#!/usr/bin/env python3

import time
import os
import copy
import glob
from emoji import emojize
import pandas as pd
from tqdm import tqdm
import numpy as np

from yaml import load
from yaml import CLoader as Loader, CDumper as Dumper
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import get_kcu, load_yaml
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame
from tamalero.Module import Module
from test_module import setup, readout_tests, isolate
import argparse

def qinj(etroc, fifo):
        i = np.random.randint(16)
        j = np.random.randint(16)
        q = 32
        L1ADelay = 501
        RB1Delay = 504
        DAC = 550
        
        etroc.wr_reg('disDataReadout', 1, broadcast=True)
        etroc.wr_reg("QInjEn", 0, broadcast=True)
        etroc.wr_reg('disTrigPath', 1, broadcast=True)
        
        etroc.wr_reg('Bypass_THCal', 1, row = row, col = col)
        etroc.wr_reg('disDataReadout', 0, row = row, col = col)
        etroc.wr_reg("QInjEn", 1, row = row, col = col)
        etroc.wr_reg("L1Adelay", 501, broadcast=True)
        etroc.wr_reg('disTrigPath', 0, row = row, col = col)
        etroc.wr_reg('QSel', 30, row = row, col = col)
        etroc.wr_reg('chargeInjectionDelay', 10, row = row, col = col)
        etroc.wr_reg('DAC', DAC, row=i, col=j, broadcast=False)
        fifo.rb.kcu.write_node("READOUT_BOARD_%s.L1A_INJ_DLY"%self.rb.rb, delay)
        
        for _ in tqdm(range(20)):
            fifo.rb.kcu.write_node("READOUT_BOARD_%s.L1A_QINJ_PULSE" % self.rb.rb, 0x01)
        	
        result = fifo.pretty_read(df)
        print(result[:10])
        
        hits = 0
        for word in result:
            if(word[0] == 'data'):
                hits += 1
        print(hits, 'hits found!')

if __name__ == '__main__':

    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('--configuration', action='store', default='modulev2', choices=['modulev0b', 'modulev1', 'modulev2'], help="Board configuration to be loaded")
    argParser.add_argument('--kcu', action='store', default='192.168.0.10', help="IP Address of KCU105 board")
    argParser.add_argument('--host', action='store', default='localhost', help="Hostname for control hub")
    argParser.add_argument('--module', action='store', default=0, choices=['1','2','3'], help="Module to test")
    argParser.add_argument('--rb', action='store', default=0, type = int, help="")
    argParser.add_argument('--etrocs', action = 'store', nargs = '*', type = int, default = [0], help = 'ETROC to use on a multi-ETROC module')
    argParser.add_argument('--pixel_masks', action='store', nargs = '*', default=['None'], help="Pixel mask to apply")
    argParser.add_argument('--moduleid', action='store', default=0, help="")
    argParser.add_argument('--show_plots', action = 'store_true')

    args = argParser.parse_args()
    args.threshold = 'auto'
    MID = int(args.moduleid)
    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
    # if args.run_tag:
    #     timestamp += '_' + args.run_tag
    result_dir = f"results/{MID}/{timestamp}/" #MultiETROC
    out_dir = f"outputs/{MID}/{timestamp}/"
    if not os.path.isdir(result_dir):
        os.makedirs(result_dir)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    print(f"Will test module with ID {MID}.") #MultiETROC
    print(f"All results will be stored under timestamp {timestamp}")

    kcu = get_kcu(args.kcu, control_hub=True, host=args.host, verbose=False)
    rb = ReadoutBoard(args.rb, kcu=kcu, config=args.configuration)
    moduleids = [0,0,0]
    # moduleids[int(args.module)-1] = MID
    rb.connect_modules(moduleids=moduleids, hard_reset=True, ext_vref=False)

    # rb.enable_external_trigger()

    if len(args.pixel_masks)==1 and args.pixel_masks[0] == 'None':
        args.pixel_masks = ['None']*12
    module, etrocs, masks = setup(rb, args)



    for n, etroc in enumerate(etrocs):
        mask = masks[n]
        if not etroc.is_connected():
            print('Skipping ETROC', n+1)
            continue
        else:
            print('Working on ETROC', n+1)
        #isolate(etrocs, n)
        thresholds = readout_tests(etroc, mask, rb, args, result_dir =  result_dir, out_dir = out_dir)
        
        i = np.random.randint(16)
        j = np.random.randint(16)
        thresh = int(thresholds[i, j] + 75)
        q = 32
        print(f'Using pixel at Row {i} Col {j} with threshold {thresh}')
        df = DataFrame()
        fifo = FIFO(rb=rb)
        fifo.reset()
        log = {
            'L1Adelay':[],
            'RBL1Adelay':[],
            'chargeInjDelay':[],
            'Hits':[]
        }

        
        etroc.bypass_THCal()
        for L1Adelay in tqdm(range(480,512)):
            for RBL1Adelay in tqdm(range(480,512), leave = False, desc = f'Working on L1Adelay = {L1Adelay}'):
                for chargeInjDelay in range(16):
                    try: 
                        etroc.QInj_set(q, chargeInjDelay, L1Adelay, row=i, col=j, broadcast = False)
                        etroc.wr_reg('DAC', thresh, row=i, col=j, broadcast=False)
                        fifo.send_QInj(count=15, delay=RBL1Adelay) #send Qinj pulses with L1Adelay
                        result = fifo.pretty_read(df)
                    except KeyboardInterrupt:
                        print(f'Interupted by keyboard. Terminating run')
                        raise
                    hits = 0
                    for word in result:
                        if(word[0] == 'trailer'):
                            hits+=word[1]['hits']
                    fifo.reset()
                    if hits > 0:
                        log['L1Adelay'].append(L1Adelay)
                        log['RBL1Adelay'].append(RBL1Adelay)
                        log['chargeInjDelay'].append(chargeInjDelay)
                        log['Hits'].append(hits)
        log = pd.DataFrame(log)
        if not any(log['Hits'] > 0):
            print('Unable to find any hits for any timing combination')
        else:
            print('Found some hits:')
            print()
            log = log.sort_values('Hits', ascending = False)
            print(log[:10].to_markdown(index = False))
                    

