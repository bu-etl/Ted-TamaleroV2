import os
from tqdm import tqdm

outdir = '/home/etl/Test_Stand/Ted-TamaleroV2/ETROC-figures/stuck_tests/RBF_Module/rbfmodule20nobias4/Tamalero_chip_config'
N = 50

fail_cntr = 0
os.makedirs(outdir, exist_ok = True)
for i in tqdm(range(N)):
    state = 'Other Failure'
    with open(f'{outdir}/output_{i}.txt', 'r') as f:
        lines = f.readlines()
        for l in lines:
            if "Retry counter reaches at 5! // Auto_Calibration Scan has failed for row" in l:
                print(f"ETROC Autothreshold Calibration Stuck {i}th run")
                fail_cntr += 1
                break

print(f"Total Failures: {fail_cntr}")