from plx_gpib_ethernet import PrologixGPIBEthernet
from time import sleep
from datetime import datetime
from copy import deepcopy
import argparse
import pandas
import sqlite3

parser = argparse.ArgumentParser(
    prog='Record Vtemp',
    description='Control this!',
)

parser.add_argument(
    '-s',
    '--sleep_time',
    metavar = 'TIME',
    type = int,
    help = 'interval in seconds reading voltage from a multimeter',
    required = True,
    dest = 'sleep_time',
)

args = parser.parse_args()

gpib = PrologixGPIBEthernet('192.168.2.25')

vtemp_dict = {
    'date' : [],
    'time' : [],
    'vtemp': [],
}

# open connection to Prologix GPIB-to-Ethernet adapter
gpib.connect()

try:
    while True:

        gpib.select(22)
        gpib.write('MEAS:VOLT:DC?')
        now = datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M:%S")

        file_d = deepcopy(vtemp_dict)
        file_d['date'].append(now.split(' ')[0])
        file_d['time'].append(now.split(' ')[1])
        file_d['vtemp'].append(gpib.read().strip())
        sleep(args.sleep_time)

        print(file_d)

        df = pandas.DataFrame(data = file_d)
        vtemp_file = 'VTempHistory.sqlite'

        with sqlite3.connect(vtemp_file) as sqlconn:
            df.to_sql('vtemp', sqlconn, if_exists='append', index=False)

except KeyboardInterrupt:
    print('Stop recording!')
    gpib.close()

