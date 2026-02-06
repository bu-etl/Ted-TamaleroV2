import os
from bs4 import BeautifulSoup
import pandas as pd
import requests
import schedule
import json
import time
import argparse
from pathlib import Path

channels = [f"U  {i}" for i in [0,1,2,3,4,5,6,7]]

def read_single_data():
    url = requests.get('http://192.168.21.26/')
    soup = BeautifulSoup(url.content, 'html.parser')
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
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
                    "Measured Sense Voltage",
                    "Measured Current",
                    "Measured Terminal Voltage",
                    "Status"]
    data = data[["Channel",
                "Measured Sense Voltage",
                "Measured Current",
                "Measured Terminal Voltage"]].to_dict(orient="list")
    data["timestamp"] = timestamp
    json.dump(data, f)
    f.write('\n')

def bot_send_message(bot_message, dont_send):
    if dont_send: return
    bot_token = api_key
    bot_chatID = chat_id
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
    response = requests.get(send_text)
    print(response)
    dont_send = True

if __name__=='__main__':
    parser = argparse.ArgumentParser(
                    prog='HV Logger',
                    description='Log output of DESY TB21 NI Crate HV',
                    )

    parser.add_argument(
        '-o',
        '--output-file',
        type = str,
        help = 'The name of the json file with HV vals. Default: "out" makes out.json',
        dest = 'output_file',
        default = 'out',
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
    outdir = outpath / 'HV_logging'
    outdir.mkdir(exist_ok=True)
    outfile = outdir / (args.output_file+'.json')
    time_limit = args.time_limit

    #chat_id = "-4149555368" #Del grupo donde está el Bot
    #api_key = "7086061035:AAEslZSr3pPEsedeMFgWROmeBKuXljLfSzY"

    print('------------------- Start of run ---------------------')
    print(f'Outfile is {outfile}.')
    print(f'Will be logging for {time_limit} seconds.')
    start_time = time.time()

    schedule.every(1).seconds.do(read_single_data)
    dont_send = True
    with open(outfile, 'a') as f:
        while (time.time() - start_time) < time_limit:
            schedule.run_pending()
