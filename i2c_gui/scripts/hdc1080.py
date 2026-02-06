import json
import logging
import struct
import time
import datetime
import pandas as pd
import sqlite3
import serial
from crccheck.crc import Crc8

SERIAL_TIMEOUT = 2
ADDR_TEMP = 0x00
ADDR_HUMID = 0x01
PACKET_HEADER = [0, 0x4c330100]
PACKET_TYPE = [1, [0x340, 0x440]]  # REQ, RESP
PACKET_ADDR = [2, [ADDR_TEMP, ADDR_HUMID]]
PACKET_VALUE = 3
PACKET_CRC1 = 4
PACKET_CRC2 = 5
PACKET_DATA_LEN = 9
PACKET_LEN = 22

SENSOR_VALUES = {'TEMP': 0, 'HUMID': 0}

ti_hdc1080_template = {
    'timestamp': [],
    'temperature': [],
    'humidity': [],
    'which_hdc1080': [],
}

def serial_req(addr):
    result = False
    tx_data = bytearray(
        struct.pack('>LHBBB', PACKET_HEADER[1], PACKET_TYPE[1][0], PACKET_ADDR[1][addr], 0x02, 0x00))
    tx_data[-1] = Crc8.calc(tx_data[:-1])
    rx_data = []

    ser.flushInput()
    ser.write(tx_data)
    timeout = time.time() + SERIAL_TIMEOUT
    while ser.is_open and time.time() < timeout:
        time.sleep(5)
        if ser.inWaiting() > 0:
            rx_data += ser.read(ser.inWaiting())
            if len(rx_data) >= PACKET_LEN:
                if len(rx_data) == PACKET_LEN:
                    data_elems = struct.unpack('>LHBHBxxxxxxxxxxxB', bytearray(rx_data))
                    if data_elems[PACKET_HEADER[0]] == PACKET_HEADER[1] and \
                            data_elems[PACKET_TYPE[0]] == PACKET_TYPE[1][1] and \
                            data_elems[PACKET_ADDR[0]] in PACKET_ADDR[1] and \
                            data_elems[PACKET_CRC1] == data_elems[PACKET_CRC2] and \
                            data_elems[PACKET_CRC1] == Crc8.calc(rx_data[0:PACKET_DATA_LEN]):
                        if data_elems[PACKET_ADDR[0]] == PACKET_ADDR[1][0]:
                            SENSOR_VALUES['TEMP'] = round((data_elems[PACKET_VALUE] * 165.0) / 65536.0 - 40.0, 3)
                            result = True
                        elif data_elems[PACKET_ADDR[0]] == PACKET_ADDR[1][1]:
                            SENSOR_VALUES['HUMID'] = round((data_elems[PACKET_VALUE] * 100.0) / 65536.0, 3)
                            result = True
                ser.flushInput()
                break
    return result


if __name__ == '__main__':
    ser = serial.Serial()
    outfile = '/media/daq/X9/DESYJune2024/ETROC-History/ti1080_sensor_data.sqlite'
    try:
        logging.info('INIT')
        ser = serial.Serial("/dev/ttyACM2", 115200, timeout=SERIAL_TIMEOUT)
        logging.info('LOOP')
        while True:
            data = json.loads(json.dumps(ti_hdc1080_template))
            if serial_req(ADDR_TEMP) and serial_req(ADDR_HUMID):
                data['timestamp'].append(datetime.datetime.now())
                data['temperature'].append(SENSOR_VALUES['TEMP'])
                data['humidity'].append(SENSOR_VALUES['HUMID'])
                data['which_hdc1080'].append(1)

                data_df = pd.DataFrame(data)
                with sqlite3.connect(outfile) as sqlconn:
                    data_df.to_sql('ti_hdc1080', sqlconn, if_exists='append', index=False)
    except Exception:
        logging.exception('MAIN')
    finally:
        try:
            ser.close()
        except Exception:
            pass
