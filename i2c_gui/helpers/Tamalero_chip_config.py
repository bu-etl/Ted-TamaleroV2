import helpers.i2c_gui2_helpers as helpers
import datetime
import numpy as np
from tqdm import tqdm
import sys
sys.path.append("/home/naomi/repos/ted_original/module_test_sw")
from tamalero.ReadoutBoard import ReadoutBoard
from tamalero import utils
import time
import argparse

def dcardSW(rb=None):
    chip_names = ["ET2p03_Bare19", "ET2p03_Bare20", "ET2p03_Bare21", "ET2p03_Bare22"]
    # chip_names = ["ET2p01_IME_5"]
    
    
    # 'The port name the USB-ISS module is connected to. Default: /dev/ttyACM0'
    port = "/dev/ttyACM1"
    #chip_addresses = [0x60, 0x61, 0x62, 0x63]
    #chip_addresses = [0x73] # RBF3 & Module
    chip_addresses = [0x70] # RBF3 & D-card

    ws_addresses = [None] * len(chip_addresses)
    
    i2c_conn = helpers.i2c_connection(port,chip_addresses,ws_addresses,chip_names, rb=rb)
    
    '''
    # Uncomment this out to check if we are reading the expected peripheral config values
    chip = i2c_conn.get_chip_i2c_connection(0x73)
    chip.read_all()

    for i in range(32):
        reg_name = f"PeriCfg{i}"
        val = chip["ETROC2", "Peripheral Config", reg_name]
        print(f"{reg_name:9s} = 0x{val:02x}")
    '''

    '''
    # Uncomment this out to test the read & write functions
    chip = i2c_conn.get_chip_i2c_connection(0x70)
    for i in range(50):
        chip.set_decoded_value("ETROC2", "Pixel Config", "upperTOT", 0x1ff)
        chip.write_decoded_value("ETROC2", "Pixel Config", "upperTOT")
        chip.read_decoded_value("ETROC2", "Pixel Config", "upperTOT")
        val = chip.get_decoded_value("ETROC2", "Pixel Config", "upperTOT")
        chip.set_decoded_value("ETROC2", "Pixel Config", "upperTOT", 0)
        chip.write_decoded_value("ETROC2", "Pixel Config", "upperTOT")
        chip.read_decoded_value("ETROC2", "Pixel Config", "upperTOT")
        val2 = chip.get_decoded_value("ETROC2", "Pixel Config", "upperTOT")
        print(f"Before: {val}, After: {val2}")
    '''
    print('PLL and FC calibration')
    # Calibrate PLL
    for chip_address in chip_addresses[:]:
        i2c_conn.calibratePLL(chip_address, chip=None)
    # Calibrate FC for all I2C
    for chip_address in chip_addresses[:]:
        i2c_conn.asyResetGlobalReadout(chip_address, chip=None)
        i2c_conn.asyAlignFastcommand(chip_address, chip=None)
    
    print('Run auto BL and NW calibration')
    i2c_conn.config_chips(
        do_pixel_check=False,
        do_basic_peripheral_register_check=False, ### Need to re-visit
        do_disable_all_pixels=False,
        do_auto_calibration=False,
        do_disable_and_calibration=True,
        do_prepare_ws_testing=False
    )
    
    ### Save BL and NW
    now = datetime.datetime.now().isoformat(sep=' ', timespec='seconds')
    i2c_conn.save_baselines(hist_dir='./RESULTS/', save_notes=f'{now}')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kcu", default="192.168.0.10", help="KCU IP/hostname")
    ap.add_argument("--rb", type=int, default=0, help="ReadoutBoard index (for multi-rb config)")
    ap.add_argument("--config", default="modulev2", help="ReadoutBoard + Module version config") 
    ap.add_argument("--module", type = int, default = 1, help = 'Which module slot to use on RB')
    ap.add_argument("--moduleid", type = int, default = 40021, help = 'Serial number of module being used')
    ap.add_argument("--hv_pause", action="store_true", help="Request input after powering on etroc to supply HV. ")
    args = ap.parse_args()

    kcu = utils.get_kcu(args.kcu, verbose=True)
    rb = ReadoutBoard(
        rb=args.rb,
        kcu=kcu,
        trigger=True,   
        config=args.config,
        verbose=True,
    )

    utils.header(rb.configured)
    time.sleep(0.01)

    if (args.module < 1) or (args.module > 3):
        raise ValueError("RBF3 expexted. Range of slot numbers is 1-3")

    moduleids=[0, 0, 0]
    moduleids[args.module - 1] = args.moduleid
    rb.connect_modules(
    moduleids=moduleids, 
    hard_reset=True, 
    ext_vref=True # uses whatever in the config to power up / down vref
    )
    rb.select_module(args.module - 1)
    time.sleep(0.05)
    if args.hv_pause:
        input("Turn on HV! just press enter or CNTRL-C :) ")
    
    dcardSW(rb=rb)

    return kcu, rb, args


kcu, rb, args = main()
