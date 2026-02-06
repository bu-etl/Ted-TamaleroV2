import numpy as np
import json
import argparse
import matplotlib.pyplot as plt
from yaml import load, Loader
import os

from tamalero.ETROC import ETROC
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.utils import get_kcu

import mplhep as hep
hep.style.use('CMS')

def toPixNum(row, col, w):
    return col*w+row

def fromPixNum(pix, w):
    row = pix%w
    col = int(np.floor(pix/w))
    return row, col

def plot_threshold(matrix, outdir, mode, args):
        module_id = args.module_slot
        chip_no = args.etroc
        fig, ax = plt.subplots(1,1,figsize=(15,15))
        
        if mode == 'noise_width':
            cax = ax.matshow(matrix, vmax=16, vmin=0)
        else:
            cax = ax.matshow(matrix)            
        ax.xaxis.tick_bottom()
        fig.colorbar(cax,ax=ax,shrink=0.8)
        for i in range(16):
            for j in range(16):
                text = ax.text(j, i, int(matrix[i,j]),
                        ha="center", va="center", color="w", fontsize="xx-small")
                
        ax.text(0.0, 1.005, "CMS", fontsize=32, color='black', horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes, fontweight='bold')
        ax.text(0.12, 1.01, "ETL Preliminary", fontsize=24, color='black', horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes, fontstyle='italic')
        ax.text(1.0, 1.01, f"Module {module_id}", fontsize=24, color='black', horizontalalignment='right', verticalalignment='bottom', transform=ax.transAxes)
        
        fig.savefig(f'{outdir}/module_{module_id}_etroc_{chip_no}_{mode}.png', bbox_inches = 'tight')
        
        if mode == 'noise_width':
            fig, ax = plt.subplots(1,1,figsize=(11,9))
            ax.text(0.0, 1.005, "CMS", fontsize=32, color='black', horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes, fontweight='bold')
            ax.text(0.12, 1.01, "ETL Preliminary", fontsize=24, color='black', horizontalalignment='left', verticalalignment='bottom', transform=ax.transAxes, fontstyle='italic')
            ax.text(1.0, 1.01, f"Module {module_id}", fontsize=24, color='black', horizontalalignment='right', verticalalignment='bottom', transform=ax.transAxes)
            mean = np.round(np.mean(matrix), 2)
            std =  np.round(np.std(matrix), 2)
            ax.text(0.9, 0.85, rf"$\mu =  {mean}$" + '\n' + rf"$\sigma = {std}$", fontsize=24, color='black', horizontalalignment='right', verticalalignment='bottom', transform=ax.transAxes)
            ax.hist(matrix.flatten(), bins=np.linspace(0, 16, 17), histtype='step', edgecolor='tab:blue', linewidth=2)
            ax.set_xlabel('Noise width')
            ax.set_ylabel('Number of pixels')
            ax.set_xticks([0, 2, 4, 6, 8, 10, 12, 14, 16])
            ax.set_xticklabels(["0", "2", "4", "6", "8", "10", "12", "14", "16"])
            ax.set_xlim(0, 16)
            fig.savefig(f'{outdir}/module_{module_id}_etroc_{chip_no}_noise_width_histogram.png')

argParser = argparse.ArgumentParser(description = "Argument parser")
argParser.add_argument('--filepath', '-f',  action='store', help="path to file")
argParser.add_argument('--module', '-m',  action='store', help="path to file")
argParser.add_argument('--module_slot', '-ms',  action='store', help="path to file")
argParser.add_argument('--etroc', '-e',  action='store', help="path to file")
argParser.add_argument('--timestamp', '-t',  action='store', help="timestamp")
argParser.add_argument('--s_curves',  action='store_true', help="option to make/store single pixel s-curves. Manual Only")
args = argParser.parse_args()

if args.filepath:
   result_dir = args.filepath
   out_dir = args.filepath.replace('results', 'outputs')
   names = args.filepath.split('/')
   args.module = names[1]
   args.timestamp = names[2]
elif args.module and args.timestamp:
   result_dir = f'results/{args.module}/{args.timestamp}/'
   out_dir = result_dir.replace('results', 'outputs')

files = os.listdir(result_dir)
if f'module_{args.module_slot}_etroc_{args.etroc}_noise_width.yaml' in files:
    pixpre = ''
    with open(result_dir + 'noise_width.yaml', 'r') as f:
        noise_matrix = np.array(load(f, Loader = Loader))
    with open(result_dir + 'baseline.yaml', 'r') as f:
        max_matrix = np.array(load(f, Loader = Loader))
    with open(result_dir + 'thresholds.yaml', 'r') as f:
        threshold_matrix = np.array(load(f, Loader = Loader))
    pix
elif f'module_{args.module_slot}_etroc_{args.etroc}_noise_width_auto.yaml' in files:
    pixpre = f'module_{args.module_slot}_etroc_{args.etroc}_'
    with open(result_dir + pixpre + 'noise_width_auto.yaml', 'r') as f:
        noise_matrix = np.array(load(f, Loader = Loader))
    with open(result_dir + pixpre + 'baseline_auto.yaml', 'r') as f:
        max_matrix = np.array(load(f, Loader = Loader))
    with open(result_dir + pixpre + 'thresholds_auto.yaml', 'r') as f:
        threshold_matrix = np.array(load(f, Loader = Loader))
else:
    pixpre = f'module_{args.module_slot}_etroc_{args.etroc}_'
    with open(result_dir + pixpre + 'noise_width_manual.yaml', 'r') as f:
        noise_matrix = np.array(load(f, Loader = Loader))
    with open(result_dir + pixpre + 'baseline_manual.yaml', 'r') as f:
        max_matrix = np.array(load(f, Loader = Loader))
    with open(result_dir + pixpre + 'thresholds_manual.yaml', 'r') as f:
        threshold_matrix = np.array(load(f, Loader = Loader))

plot_threshold(noise_matrix, out_dir, 'noise_width', args)
plot_threshold(max_matrix, out_dir, 'baseline', args)
plot_threshold(threshold_matrix, out_dir, 'thresholds', args)

if args.s_curves:
    outfiles = os.listdir(result_dir)
    if pixpre + 'manual_thresh_scan_data.json' in outfiles:
        datapath = result_dir + pixpre + 'manual_thresh_scan_data.json'
    else:
       datapath = result_dir + pixpre + 'thresh_scan_data.json'
    with open(datapath, 'r') as f:
       data = json.load(f)
       print('Found file at ' + datapath)

    vth_axis    = np.array([float(v) for v in data])
    hit_rate    = np.array([data[v] for v in data], dtype = float).T
    N_pix       = len(hit_rate) # total # of pixels
    N_pix_w     = int(round(np.sqrt(N_pix))) # N_pix in NxN layout
    max_indices = np.argmax(hit_rate, axis=1)
    maximums    = vth_axis[max_indices]
    max_matrix  = np.empty([N_pix_w, N_pix_w])
    noise_matrix  = np.empty([N_pix_w, N_pix_w])
    threshold_matrix = np.empty([N_pix_w, N_pix_w])
    for pix in range(N_pix):
        r, c = fromPixNum(pix, N_pix_w)
        max_matrix[r][c] = maximums[pix]
        noise_matrix[r][c] = np.size(np.nonzero(hit_rate[pix]))
        max_value = vth_axis[hit_rate[pix]==max(hit_rate[pix])]
        if isinstance(max_value, np.ndarray):
            max_value = max_value[-1]
        zero_dac_values = vth_axis[((vth_axis>(max_value)) & (hit_rate[pix]==0))]
        if len(zero_dac_values)>0:
            threshold_matrix[r][c] = zero_dac_values[0] + 2
        else:
            threshold_matrix[r][c] = dac_max + 2
    
        fig = plt.figure(figsize = (9, 7))
        pixdat = hit_rate[pix, :]
        width = 25
        idxlim = [np.min([0, np.argmin(pixdat - width)]), np.max([len(pixdat), np.argmax(pixdat + width)])]
        x = vth_axis[idxlim[0]:idxlim[1]]
        y = pixdat[idxlim[0]:idxlim[1]]
        plt.plot(x, y, '-o')
        hep.cms.label(llabel = 'ETL Preliminary', rlabel = f'Row {r} Col {c} Manual Threshold Scan', fontsize = 18)
        if not os.path.exists(out_dir + '/mts_individual_pixels'):
            os.mkdir(out_dir + '/mts_individual_pixels')
        plt.savefig(out_dir + '/mts_individual_pixels/' + pixpre + f'r{r}c{c}_mts_results.png')
        if r == 15 and c == 0:
            print(r, c)
            plt.show()
        plt.close()

