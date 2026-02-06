import helpers.i2c_gui2_helpers as helpers
import datetime
import numpy as np
from tqdm import tqdm

chip_names = ["ET2p03_Bare19", "ET2p03_Bare20", "ET2p03_Bare21", "ET2p03_Bare22"]
# chip_names = ["ET2p01_IME_5"]


# 'The port name the USB-ISS module is connected to. Default: /dev/ttyACM0'
port = "/dev/ttyACM1"
#chip_addresses = [0x60, 0x61, 0x62, 0x63]
chip_addresses = [0x60]
ws_addresses = [None] * len(chip_addresses)

i2c_conn = helpers.i2c_connection(port,chip_addresses,ws_addresses,chip_names)

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
i2c_conn.save_baselines(hist_dir='./results', save_notes=f'{now}')

### Define pixels of interest
#qinj_test = True
#if (qinj_test):
#    row_list = [12, 12, 13, 13]
#    col_list = [6, 9, 6, 9]
#    scan_list = list(zip(row_list, col_list))
#
#else:
#    col_list, row_list = np.meshgrid(np.arange(16),np.arange(16))
#    scan_list = list(zip(row_list.flatten(),col_list.flatten()))
#
#print('Pixel of interest:')
#print(scan_list)
#
### Set pixels
#bypass_on = True
#if (qinj_test):
#    i2c_conn.enable_select_pixels_in_chips(scan_list, Qsel=30, QInjEn=True, Bypass_THCal=bypass_on, power_mode='high', verbose=False)
#else:
#    i2c_conn.enable_select_pixels_in_chips(scan_list, Qsel=5, QInjEn=False, Bypass_THCal=bypass_on, power_mode='high', verbose=False)
#
#print('Set Offset')
#### Set Offset
#offset_broadcast = False
#offsets = #{
#    0x60: 20, # Bar 4
#    0x61: 20, # Bar 12
#    0x62: 20, # PT-NH8
#    0x63: 20, # IME-5
#}
#
#if (qinj_test):
#    offsets = {
#        0x60: 10, # Bar 4
#        0x61: 10, # Bar 12
#        0x62: 10, # PT-NH8
#        0x63: 10, # IME-5
#    }
#
#for chip_address in chip_addresses:
#    chip = i2c_conn.get_chip_i2c_connection(chip_address)
#
#    if offset_broadcast:
#        i2c_conn.set_chip_offsets_broadcast(chip_address, offset=offsets[chip_address], chip=chip)
#        del chip
#    else:
#        i2c_conn.set_chip_offsets(chip_address, pixel_list=scan_list, offset=offsets[chip_address], chip=chip, verbose=False)
#        del chip
#
### Print Invalid FC counter
# for `chip_address in chip_addresses:
#     chip = i2c_conn.get_chip_i2c_connection(chip_address)
#     chip.read_decoded_value("ETROC2", "Peripheral Status", 'invalidFCCount')
#     value_invalidFCCount = chip.get_decoded_value("ETROC2", "Peripheral Status", "invalidFCCount")
#     print(`f"Chip {hex(chip_address)} Invalid FC Counter: {value_invalidFCCount}")
