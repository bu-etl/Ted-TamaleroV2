from bs4 import BeautifulSoup
import pandas as pd
import requests
# import schedule
import signal
import time
import argparse
import sqlite3
from pathlib import Path

channels = [f"{i}" for i in range(0,8)]

def convert_voltage(value):
    if isinstance(value, (int, float)):  # Handle numeric input directly
        return value
    elif isinstance(value, str):
        if value.endswith(" V"):
            return float(value.removesuffix(" V")) * 1
        elif value.endswith(" mV"):
            return float(value.removesuffix(" mV")) * 1e-3
        elif value.endswith(" uV"):
            return float(value.removesuffix(" uV")) * 1e-6
    raise ValueError(f"Invalid voltage format: {value}")  # Handle unexpected inputs

def convert_current(value):
    if isinstance(value, (int, float)):  # Handle numeric input directly
        return value
    elif isinstance(value, str):
        if value.endswith(" A"):
            return float(value.removesuffix(" A")) * 1
        elif value.endswith(" mA"):
            return float(value.removesuffix(" mA")) * 1e-3
        elif value.endswith(" uA"):
            return float(value.removesuffix(" uA")) * 1e-6
    raise ValueError(f"Invalid current format: {value}")  # Handle unexpected inputs

def read_single_data():
    while True:
        try:
            url = requests.get('http://192.168.21.26/')
            soup = BeautifulSoup(url.content, 'html.parser')
            break

        except requests.exceptions.ConnectionError as e:
            print(f'Request failed: {e}. Retrying in 5 seconds.')
            print(pd.Timestamp.now().isoformat(sep=' ', timespec='seconds'))
            time.sleep(5)

    timestamp = pd.Timestamp.now().isoformat(sep=' ', timespec='seconds')

    #print(f'>> Log successful at {timestamp}')

    result = soup.find_all("body")[0]
    # Obtenemos todas las filas
    rows = result.find_all("tr")
    output_rows = []

    for row in rows:
        ### Check there are no errors ##
        #if 'Current too high' in str(row):
        #    bot_send_message(str(row), dont_send)

        if not any(ch in str(row) for ch in channels):
            continue
        # obtenemos todas las columns
        cells = row.find_all("td")
        output_row = []
        if len(cells) > 0:
            for cell in cells:
                output_row.append(cell.text)
            output_rows.append(output_row)

    #format_result = output_rows.text
    data = pd.DataFrame(output_rows)
    data.columns = ["Channel",
                    "Voltage",
                    "Current",
                    "Sense Voltage",
                    "Sense Current_uA",
                    "Terminal Voltage",
                    "Status"]

    data = data[["Channel",
                "Sense Voltage",
                "Sense Current_uA",
                "Terminal Voltage"]]

    data["timestamp"] = timestamp
    data = data[1:9]

    ### Surgery
    data['Channel'] = range(8)
    data['Channel'] = data['Channel'].astype('uint8')
    data['Sense Voltage'] = data['Sense Voltage'].apply(convert_voltage)
    data['Sense Voltage'] = data['Sense Voltage'].astype('float32')
    data['Terminal Voltage'] = data['Terminal Voltage'].apply(convert_voltage)
    data['Terminal Voltage'] = data['Terminal Voltage'].astype('float32')
    data['Sense Current_uA'] = data['Sense Current_uA'].apply(convert_current)
    data['Sense Current_uA'] = data['Sense Current_uA'].astype('float32')

    outfile = outpath / 'HV_History.sqlite'
    with sqlite3.connect(outfile) as sqlconn:
        data.to_sql('hv', sqlconn, if_exists='append', index=False)

global exit_loop
exit_loop = False

if __name__=='__main__':
    parser = argparse.ArgumentParser(
                    prog='HV Logger',
                    description='Log output of DESY TB21 NI Crate HV',
                    )

    parser.add_argument(
        '-d',
        '--output-directory',
        type = Path,
        help = 'Path to where the json file should be stored. Default: ./',
        dest = 'output_directory',
        default = Path("./"),
    )

    parser.add_argument(
        '-t',
        '--time-limit',
        type = int,
        help = 'Amount of time to log for. Default: 5',
        dest = 'time_limit',
        default = 5,
    )

    args = parser.parse_args()

    outpath = Path(args.output_directory)
    time_limit = args.time_limit

    #chat_id = "-4149555368" #Del grupo donde está el Bot
    #api_key = "7086061035:AAEslZSr3pPEsedeMFgWROmeBKuXljLfSzY"

    print('------------------- Start of run ---------------------')
    print(f'Output is saved to {outpath}')
    print(f'Will be logging for every {time_limit} seconds.')

    def signal_handler(sig, frame):
        global exit_loop
        print("Exiting gracefully")
        exit_loop = True

    signal.signal(signal.SIGINT, signal_handler)

    while not exit_loop:
        read_single_data()
        time.sleep(args.time_limit)

    signal.pause()
