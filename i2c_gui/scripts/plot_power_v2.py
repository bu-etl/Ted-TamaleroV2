#############################################################################
# zlib License
#
# (C) 2023 Cristóvão Beirão da Cruz e Silva <cbeiraod@cern.ch>
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.
#############################################################################

from pathlib import Path
import sqlite3
import pandas
import datetime
import matplotlib.pyplot as plt

def plot_power(
        hours: int,
        endHours: int,
        file: Path,
    ):
    with sqlite3.connect(file) as sqlite3_connection:
        data_df = pandas.read_sql('SELECT * FROM power_v2', sqlite3_connection, index_col=None)
        action_df = pandas.read_sql('SELECT * FROM actions_v2', sqlite3_connection, index_col=None)

        data_df['timestamp'] = pandas.to_datetime(data_df['timestamp'], infer_datetime_format=True, format='mixed')
        action_df['timestamp'] = pandas.to_datetime(action_df['timestamp'], infer_datetime_format=True, format='mixed')

        if endHours is not None:
            tmp_sel = data_df['timestamp'] > datetime.datetime.now() - datetime.timedelta(hours=(hours + endHours))
            tmp_sel = tmp_sel & (data_df['timestamp'] < datetime.datetime.now() - datetime.timedelta(hours=endHours))
            tmp_df = data_df.loc[tmp_sel]

            tmp_sel = action_df['timestamp'] > datetime.datetime.now() - datetime.timedelta(hours=(hours + endHours))
            tmp_sel = tmp_sel & (action_df['timestamp'] < datetime.datetime.now() - datetime.timedelta(hours=endHours))
            action_df = action_df.loc[tmp_sel]
        else:
            tmp_df = data_df.loc[data_df['timestamp'] > datetime.datetime.now() - datetime.timedelta(hours=hours)]
            action_df = action_df.loc[action_df['timestamp'] > datetime.datetime.now() - datetime.timedelta(hours=hours)]

        power_df = action_df.loc[action_df['system'] == "Power"].copy()
        power_df = power_df.loc[power_df['type'] != "Logging"].copy()
        cooling_df = action_df.loc[action_df['system'] == "Cooling"].copy()
        config_df = action_df.loc[action_df['system'] == "Config"].copy()

        instruments = tmp_df['Instrument'].unique()

        for instrument in instruments:
            instrument_df = tmp_df.loc[tmp_df['Instrument'] == instrument].copy()
            channels_df = instrument_df.groupby(['Channel', 'channel_id']).size().reset_index().drop(0, axis=1)

            for index, row in channels_df.iterrows():
                channel = row['Channel']
                channel_id = row['channel_id']
                
                channel_df = instrument_df[instrument_df['Channel'] == channel].copy()
                this_power_df = power_df[(power_df['message'] == f"{instrument} {channel_id}") | (power_df['message'] == 'All channels')].copy()

                channel_df['V'] = (channel_df['V'].str.replace('V','')).astype(float)
                channel_df['I'] = (channel_df['I'].str.replace('A','')).astype(float)

                # Show voltage on top and current below
                figure, axis = plt.subplots(
                    nrows=2,
                    ncols=1,
                    sharex='col',
                    #sharey='row',
                )

                figure.suptitle(f'Voltage and Current plots for channel {channel} of instrument {instrument}')

                this_ax = axis[0]
                channel_df.plot(
                    x = 'timestamp',
                    y = f'V',
                    kind = 'scatter',
                    ax=this_ax,
                    #kind = 'line',
                )

                this_ax = axis[1]
                channel_df.plot(
                    x = 'timestamp',
                    y = f'I',
                    kind = 'scatter',
                    ax=this_ax,
                    #kind = 'line',
                )

                # Order of the loops below is important since the last one will be on top of the first
                for cooling_index, cooling_row in cooling_df.iterrows():
                    axis[0].axvline(
                        x = cooling_row['timestamp'],
                        color = 'c',
                    )
                    axis[1].axvline(
                        x = cooling_row['timestamp'],
                        color = 'c',
                    )

                for config_index, config_row in config_df.iterrows():
                    axis[0].axvline(
                        x = config_row['timestamp'],
                        color = 'y',
                    )
                    axis[1].axvline(
                        x = config_row['timestamp'],
                        color = 'y',
                    )

                for power_index, power_row in this_power_df.iterrows():
                    if power_row['type'] == 'On':
                        color = 'g'
                    elif power_row['type'] == 'Off':
                        color = 'r'

                    axis[0].axvline(
                        x = power_row['timestamp'],
                        color = color,
                    )
                    axis[1].axvline(
                        x = power_row['timestamp'],
                        color = color,
                    )

                plt.show()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
                    prog='Plot Power',
                    description='Show it!',
                    #epilog='Text at the bottom of help'
                    )
    
    parser.add_argument(
        '-t',
        '--hours',
        metavar = 'HOURS',
        type = int,
        help = 'Hours to go back and plot. Default: 24',
        default = 24,
        dest = 'hours',
    )
    parser.add_argument(
        '-e',
        '--endHours',
        metavar = 'HOURS',
        type = int,
        help = 'From when to go back and plot. Default: None',
        default = None,
        dest = 'endHours',
    )
    parser.add_argument(
        '-f',
        '--file',
        metavar = 'PATH',
        type = Path,
        help = 'sqlite file with the power data. must be a v2 format file',
        required = True,
        dest = 'file',
    )

    args = parser.parse_args()

    plot_power(args.hours, args.endHours, args.file)
