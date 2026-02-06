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

import datetime
import pandas
import sqlite3
from pathlib import Path

def log_action_v2(output_path: Path, action_system: str, action_type: str, action_message: str, time_override = None):
    timestamp = datetime.datetime.now().isoformat(sep=' ')
    if time_override is not None:
        timestamp = time_override
    data = {
            'timestamp': [timestamp],
            'system': [action_system],
            'type': [action_type],
            'message': [action_message],
    }
    df = pandas.DataFrame(data)

    outfile = output_path / 'PowerHistory_v2.sqlite'
    with sqlite3.connect(outfile) as sqlconn:
        df.to_sql('actions_v2', sqlconn, if_exists='append', index=False)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
                    prog='Read Current',
                    description='Control them!\nBy default, this script will take no action apart from finding and attempting to connect to the configured power supplies. Use the --turn-on --log --turn-off options to control what actions the script takes',
                    #epilog='Text at the bottom of help'
                    )

    parser.add_argument(
        '-o',
        '--output-directory',
        type = Path,
        help = 'The directory where the log file is saved to. Default: ./',
        dest = 'output_directory',
        default = Path("./"),
    )
    parser.add_argument(
        '-s',
        '--action-system',
        type = str,
        help = "The type of action to log",
        dest = 'action_system',
        default = None,
        choices = [None, "Power", "Cooling", "Config"],
    )
    parser.add_argument(
        '-t',
        '--action-type',
        type = str,
        help = "The type of action to log",
        dest = 'action_type',
        default = "Info",
    )
    parser.add_argument(
        '-m',
        '--action-message',
        type = str,
        help = "The type of action to log",
        dest = 'action_message',
        required = True,
    )
    parser.add_argument(
        '--time-override',
        type = str,
        help = "Override the timestamp field with this value",
        dest = 'time_override',
    )

    args = parser.parse_args()

    log_action_v2(Path(args.output_directory), args.action_system, args.action_type, args.action_message, args.time_override)
