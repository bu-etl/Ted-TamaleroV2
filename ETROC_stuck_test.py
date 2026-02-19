import os
from tqdm import tqdm
from lv_driver import PowerSupply
from hv_driver import HVPowerSupply
import time

data = []

run_tag = 'run2_n40_biased'
base_dir = f'ETROC-figures/stuck_tests/D_card_20/{run_tag}'
outdir_testtamalero = f'{base_dir}/test_tamalero'
outdir = f'{base_dir}/Tamalero_chip_config'
outdir_time = f'{base_dir}/time'

N = 40
wait = 15
os.makedirs(outdir, exist_ok = True)
os.makedirs(outdir_testtamalero, exist_ok = True)
os.makedirs(outdir_time, exist_ok = True)

D1_VREF2 = PowerSupply('name',"192.168.2.4")
RBF2 = PowerSupply('name',"192.168.2.1")
caen = HVPowerSupply("/dev/ttyACM2")
for i in tqdm(range(N)):
    D1_VREF2.power_up("CH1")
    time.sleep(1)
    D1_VREF2.power_up("CH2")
    time.sleep(1)
    RBF2.power_up("CH2")
    time.sleep(1)
    os.system(f'python3 module_test_sw/test_tamalero.py --kcu 192.168.0.11 --power_up --adcs --verbose > {outdir_testtamalero}/output_{i}.txt 2> {outdir_testtamalero}/errors_{i}.txt')
    caen.set_channel_on()
    try:
        caen.wait_ramp(True, 1)
    except Exception as e:
        print("Wait ramp exception:", e)
        break
    time.sleep(1)
    os.chdir("i2c_gui")
    time.sleep(1)
    start_time = time.perf_counter()
    os.system(f'python3 -m helpers.Tamalero_chip_config.py --kcu 192.168.0.11 > ../{outdir}/output_{i}.txt 2> ../{outdir}/errors_{i}.txt')
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time - 37.0 # 37s is the time I measured for Tamalero_chip_config to get to the row calibration. Not exact, but close enough to notice differences
    os.system(f"echo 'time: {elapsed_time}' > ../{outdir_time}/time_{i}.txt ")
    os.chdir(f"..")
    caen.set_channel_off()
    caen.wait_ramp(False, 1)
    time.sleep(1)
    D1_VREF2.power_down("CH1")
    time.sleep(1)
    D1_VREF2.power_down("CH2")
    time.sleep(1)
    RBF2.power_down("CH2")
    time.sleep(wait)
    
