#############################################################################
# zlib License
#
# (C) 2024 Cristóvão Beirão da Cruz e Silva <cbeiraod@cern.ch>
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
import mplhep
from matplotlib.dates import DateFormatter

def plot_adc(
        start: datetime.datetime,
        end: datetime.datetime,
        channel: int,
        file: Path,
        title: str,
        do_calibrated: bool = False,
        do_line: bool = False,
    ):
    mplhep.style.use("CMS")

    with sqlite3.connect(file) as sqlite3_connection:
        data_df = pandas.read_sql(f'SELECT * FROM adc WHERE channel = {channel}', sqlite3_connection, index_col=None)
        if len(data_df) == 0:
            raise RuntimeError(f"There is no data for channel {channel}")

        data_df['Time'] = pandas.to_datetime(data_df['timestamp'], format='mixed')

        print("Timestamps in database file cover range:")
        print("Min:", data_df['Time'].min())
        print("Max", data_df['Time'].max())

        if start is not None:
            data_df = data_df.loc[data_df['Time'] >= start]
        if end is not None:
            data_df = data_df.loc[data_df['Time'] <= end]

        unit = 'V'
        data_df['Data'] = data_df["voltage"]
        if do_calibrated:
            calibrated = data_df['calibrated'].unique()
            if len(calibrated) > 1 or calibrated[0] is not None:
                data_df['Data'] = data_df["calibrated"]
                unit = data_df['calibrated_units'].unique()
                if len(unit) != 1:
                    raise RuntimeError("There is a problem in the data where a single channel has multiple units. Perhaps separate runs were accidentally concatenated?")
                unit = unit[0]


        figure, axis = plt.subplots(
            nrows = 1,
            ncols = 1,
            sharex='col',
            layout='constrained',
            figsize=(16, 9),
        )
        figure.suptitle(f'{title}')

        kind = 'scatter'
        if do_line:
            kind = 'line'

        if unit == 'C':
            label = "Temperature [C]"
        elif unit == 'V':
            label = "Voltage [V]"
        else:
            label = f"Measurement [{unit}]"

        mplhep.cms.text(loc=0, ax=axis, text='Preliminary', fontsize=25)
        data_df.plot(
            x = 'Time',
            y = 'Data',

            kind = kind,
            ax=axis,
        )
        axis.set_ylabel(label)

        date_form = DateFormatter("%Y-%m-%d %H:%M")
        axis.xaxis.set_major_formatter(date_form)
        plt.xticks(rotation=60, fontsize=18)
        plt.yticks(fontsize=18)

        #axis.set_xlabel(fontsize=10)
        #axis.set_xticklabels(rotation=90, fontsize=9)

        plt.show()

        return

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
                    prog='Plot ADC',
                    description='Show it!',
                    #epilog='Text at the bottom of help'
                    )

    parser.add_argument(
        '-s',
        '--start',
        metavar = 'DATETIME',
        type = str,
        help = 'Start time for plotting, use format "YYYY-MM-DD hh:mm:ss". Default: None',
        default = None,
        dest = 'start',
    )
    parser.add_argument(
        '-e',
        '--end',
        metavar = 'DATETIME',
        type = str,
        help = 'End time for plotting, use format "YYYY-MM-DD hh:mm:ss". Default: None',
        default = None,
        dest = 'end',
    )
    parser.add_argument(
        '-t',
        '--title',
        metavar = 'TITLE',
        type = str,
        help = 'Title to be used in the plots',
        required = True,
        dest = 'title',
    )
    parser.add_argument(
        '-f',
        '--file',
        metavar = 'PATH',
        type = Path,
        help = 'sqlite file with the adc data',
        required = True,
        dest = 'file',
    )
    parser.add_argument(
        '-c',
        '--channel',
        metavar = 'CHANNEL',
        type = int,
        help = 'The ADC channel to plot',
        required = True,
        dest = 'channel',
    )
    parser.add_argument(
        '--calibrated',
        action = 'store_true',
        help = 'If set, will plot the calibrated values instead of the raw voltage',
        dest = 'do_calibrated',
    )
    parser.add_argument(
        '--line',
        action = 'store_true',
        help = 'If set, will make the plot as a line instead of a scatter plot',
        dest = 'do_line',
    )

    args = parser.parse_args()

    plot_adc(args.start, args.end, args.channel, args.file, args.title, args.do_calibrated, args.do_line)
