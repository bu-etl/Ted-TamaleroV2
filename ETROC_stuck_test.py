import os
import sys
import argparse
from pathlib import Path
from tqdm import tqdm
from lv_driver import PowerSupply
import time

parser = argparse.ArgumentParser()
parser.add_argument('-r', '--run_tag', type=str, default='run1_test', help='Run tag for the output directory')
parser.add_argument('--hv', nargs='?', const='/dev/ttyACM2', default=None, help='HV port (default: /dev/ttyACM2)')
parser.add_argument('--chip_addr', type=str, default="0x73", help='Chip address (default: 0x73)')
parser.add_argument('--rbf_channel', type=str, default="CH1", help='RBF Channel (default: CH1)')
parser.add_argument('--lv_ip', type=str, default="192.168.1.41", help='LV Power Supply IP (default: 192.168.1.41)')
parser.add_argument('--vref_ip', type=str, default=None, help='VREF Power Supply IP')
parser.add_argument('-n', '--num', type=int, default=50, help='Number of iterations (default: 50)')
parser.add_argument('--wait', type=int, default=5, help='Wait time in seconds (default: 5)')
args = parser.parse_args()

data = []
if args.hv:
    from hv_driver import HVPowerSupply
    caen = HVPowerSupply(args.hv)

run_tag = args.run_tag
base_dir = Path('ETROC-figures/stuck_tests/') / run_tag
outdir = base_dir / 'tamalero'
outdir_tam = base_dir / 'test_tamalero'
outdir_time = base_dir / 'time'

outdir.mkdir(parents=True, exist_ok=True)
outdir_time.mkdir(parents=True, exist_ok=True)
outdir_tam.mkdir(parents=True, exist_ok=True)
'''
if args.vref_ip:
    D1_VREF2 = PowerSupply('name', args.vref_ip)
RB_LV = PowerSupply('name', args.lv_ip)
'''

ps = PowerSupply('name', '192.168.2.1')

for i in tqdm(range(args.num)):
    '''
    if args.vref_ip:
        D1_VREF2.power_up("CH1")
        time.sleep(1)
        D1_VREF2.power_up("CH2")
        time.sleep(1)
    RB_LV.power_up(args.rbf_channel)
    '''
    #ps.power_up("CH1")
    #time.sleep(1)
    ps.power_up("CH2")
    time.sleep(1)
    if args.hv:
        caen.set_channel_on()
        try:
            caen.wait_ramp(True, 1)
        except Exception as e:
            print("Wait ramp exception:", e)
            break
    time.sleep(1)
    
    #os.chdir("i2c_gui")
    os.chdir("module_test_sw")
    time.sleep(1)
    
    # Construct paths relative to i2c_gui module_test_sw for output
    rel_outdir = Path('..') / outdir
    rel_outdir_time = Path('..') / outdir_time
    rel_outdir_tam = Path('..') / outdir_tam
    os.system(f'python3 test_tamalero.py --power_up --adcs --verbose --kcu 192.168.0.11 > "{rel_outdir_tam}/output_{i}.txt" 2> "{rel_outdir_tam}/errors_{i}.txt"')


    start_time = time.perf_counter()
    #os.system(f'{sys.executable} -m helpers.chip_config.py > "{rel_outdir}/output_{i}.txt" 2> "{rel_outdir}/errors_{i}.txt"')
    os.system(f'python3 test_module.py --external_vref --kcu 192.168.0.11 --moduleid 40024 --test_chip > "{rel_outdir}/output_{i}.txt" 2> "{rel_outdir}/errors_{i}.txt"')
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time # 37s is the time I measured for Tamalero_chip_config to get to the row calibration. Not exact, but close enough to notice differences
    os.system(f"echo 'time: {elapsed_time}' > \"{rel_outdir_time}/time_{i}.txt\" ")
    os.chdir("..")
    if args.hv:
        caen.set_channel_off()
        caen.wait_ramp(False, 1)
    time.sleep(1)
    '''
    if args.vref_ip:
        D1_VREF2.power_down("CH1")
        time.sleep(1)
        D1_VREF2.power_down("CH2")
        time.sleep(1)
    RB_LV.power_down(args.rbf_channel)
    '''
    #ps.power_down("CH1")
    #time.sleep(1)
    ps.power_down("CH2")
    time.sleep(args.wait)
    
