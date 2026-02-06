"""
For plotting of 
"""
import time
import numpy as np
from tamalero.utils import load_yaml, ffs, bit_count
from tamalero.colors import red, green, yellow
from yaml import load, dump, safe_load
from yaml import CLoader as Loader, CDumper as Dumper
import os
from random import randrange

import mplhep as hep

from matplotlib import pyplot as plt
plt.style.use(hep.style.CMS)


UXtoTamalero = {1:0, 2:2, 3:1, 4:3}
cbar_labels = {'baseline_auto':'Baseline', 'noise_width_auto':'Noise width', 'thresholds_auto':'Thresholds'}

if __name__ == '__main__':
    import argparse
    argParser = argparse.ArgumentParser(description = "Argument parser")
    #Setup Options
    argParser.add_argument('--input', action='store', help="Input file")
    argParser.add_argument('--module', action='store', help="Module id")
    args = argParser.parse_args()

    input_data = args.input
    moduleid = args.module
    etrocs = [True, True, True, True]
    view = 'top-module'
    UXs = [2, 1, 3, 4] if view=='top-board' else [1, 2, 3, 4]
    invert = [False, False, True, True] if view=='top-board' else [False, False, True, True]

    for result in ['baseline_auto', 'noise_width_auto', 'thresholds_auto']:

        vmatrix = []
        images = []

        for UX in UXs:
            etroc = UXtoTamalero[UX]
            try:
                with open(f'{input_data}/module_{moduleid}_etroc_{etroc}_{result}.yaml', 'r') as f:
                    matrix = np.array(safe_load(f))
            except:
                print(f"U{UX} doesn't seem to have data, skipping")
                matrix = np.zeros((16,16))
            vmatrix.append(matrix)

        vmin = 0 if 'noise_width' in result else min([np.min(matrix) for matrix in vmatrix])
        vmax = 16 if 'noise_width' in result else max([np.max(matrix) for matrix in vmatrix])

        plt.style.use(hep.style.CMS)
        fig, axs = plt.subplots(2, 2, figsize=(20, 16), gridspec_kw={'wspace': 0.2, 'hspace': 0.2})

        axes = axs.flat
        for m, etroc in enumerate(zip(vmatrix, UXs)):
            ax = axes[m]
            UX = etroc[1]
            im = ax.matshow(etroc[0], vmin=vmin, vmax=vmax)
            images.append(im)
            for i in range(16):
                for j in range(16):
                    text = ax.text(j, i, int(etroc[0][i,j]), ha="center", va="center", color="w", fontsize=10)
            ax.set_xlabel('Column')
            ax.set_ylabel('Row')
            if invert[m]:
                ax.invert_yaxis() 
                ax.invert_xaxis()
            ax.minorticks_off()
            ax.xaxis.set_ticks_position('bottom')
            ax.xaxis.set_label_position('bottom')
            ax.text(0.0, 1.01, f"U{UX}", ha="left", va="bottom", transform=ax.transAxes, fontsize=18, fontweight = "bold")
            ax.text(0.1, 1.01, fr"$<\mu>$ = {np.round(np.mean(etroc[0]), 2)}, $\sigma$ = {np.round(np.std(etroc[0]), 2)} ", ha="left", va="bottom", transform=ax.transAxes, fontsize=18)

        cbar = fig.colorbar(images[0], ax=axs)
        cbar.set_label(cbar_labels[result], fontsize = 34)

        fig.text(0.08, 0.92, "CMS", fontsize=44, ha="left", va="bottom", fontweight='bold')
        fig.text(0.155, 0.924, "ETL Preliminary", fontsize=34, ha="left", va="bottom", style='italic')
        fig.text(0.82, 0.924, f"Module {moduleid}", fontsize=34, ha="right", va="bottom")

        fig.savefig(f'{input_data}/module-view_{moduleid}_{result}.png', dpi = 150)
        fig.savefig(f'{input_data}/module-view_{moduleid}_{result}.pdf')
