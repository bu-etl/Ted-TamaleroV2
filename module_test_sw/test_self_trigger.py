from tamalero.ReadoutBoard import ReadoutBoard
from tamalero.FIFO import FIFO
from tamalero.DataFrame import DataFrame
from tamalero import utils
import time

kcu = utils.get_kcu("192.168.0.10", verbose=True)
rb = ReadoutBoard(
    rb = 0,
    kcu = kcu,
    trigger = True, # this sets up servant lpGBT i believe...
    config = "modulev2",
    verbose = True
)
con = input('Turn Vref on, continue [y]/[n]')
if not con == 'y':
    raise ValueError("Incorrect input, only type y to continue.")

utils.header(rb.configured)
time.sleep(0.01)
rb.connect_modules(
    moduleids=[0, 0, 207], # third slot
    hard_reset = True, 
    ext_vref = False # uses whatever in the config to power up / down vref
)

# taking first connected etroc and module
connected_modules = [mod for mod in rb.modules if mod.connected]
if not connected_modules:
    raise ValueError("No connected modules found")
module = connected_modules[0]
connected_etrocs = [etroc for etroc in module.ETROCs if etroc.is_connected()]
if not connected_etrocs:
    raise ValueError("No connected ETROCs found")
etroc = connected_etrocs[0]
# ensure internal VREF is powered down
etroc.power_down_VRef()

etroc.set_power_mode("high")

module.show_status()
time.sleep(0.01)
rb.MUX64.read_channels()
time.sleep(0.01)
rb.DAQ_LPGBT.read_adcs()
time.sleep(0.01)
rb.disable_MUX64()
time.sleep(0.01)
etroc.wr_reg("workMode", 0, broadcast=True)
start_temp = etroc.read_temp(mode="VOLT")
print("**********START TEMP**********", start_temp)

while input("temp ok? hv on :) ") != 'y':
    print(etroc.read_temp(mode="VOLT"))
#input("Turn on HV")

baseline, noise_width = etroc.run_threshold_scan(offset=25)
print("BASELINE AND NOISEWIDTH")
print(baseline)
print("----------------")
print(noise_width)

######### SELF TRIGGER ###########
print("Enabling self trigger")
print("--------------------")

module.show_status()
etroc.bypass_THCal()
time.sleep(1)

etroc.configure_self_trig(refresh_self_trig = True)
module.show_status()
time.sleep(0.01)
df = DataFrame()
fifo = FIFO(rb=rb)
fifo.reset()
delay = 10
i = 0
j = 0
L1Adelay = 501
RBL1Adelay = 504
q = 25
nPulses = 350
etroc.QInj_set(q, delay, L1Adelay, row=i, col=j, broadcast = False)
time.sleep(0.01)
#etroc.wr_reg('DAC', 325, row=i, col=j, broadcast=False)

kcu.write_node(f'READOUT_BOARD_{rb.rb}.EVENT_CNT_RESET', 1)
time.sleep(0.01)
kcu.write_node(f'READOUT_BOARD_{rb.rb}.EVENT_CNT_RESET', 0)
time.sleep(0.01)

rb.self_trig_start()
print("Sending Pulse, current event count: ", kcu.read_node(f'READOUT_BOARD_{rb.rb}.EVENT_CNT').value())

for i in range(10):
    print("sending pulse", i)
    rb.kcu.write_node("READOUT_BOARD_0.QINJ_PULSE", 1)
    print(kcu.read_node(f'READOUT_BOARD_{rb.rb}.EVENT_CNT').value(), 'events detected.')
    time.sleep(0.5)

import numpy as np
print("End")
print("BASELINE",np.mean(baseline), np.std(baseline))
print("NOISEWIDTH",np.mean(noise_width), np.std(noise_width))
print("VOLTAGE TEMP START", start_temp)
print("VOLTAGE TEMP START", etroc.read_temp(mode="VOLT"))
rb.self_trig_status()
print("-----------------------------")
##################################
