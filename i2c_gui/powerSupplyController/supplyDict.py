#############################################################################
# zlib License
#
# (C) 2024 Murtaza Safdari <musafdar@cern.ch>
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

# class supplyDict():
#     def __init__():
#         pass

supplyDict = {
    "PL303QMD-P":{
        "set_voltage":"V{channel} {voltage}",
        "set_current":"I{channel} {current}",
        "get_state":'OP{channel}?',
        "power_on":"OP{channel} 1",
        "power_off":"OP{channel} 0",
        "get_voltage":"V{channel}O?",
        "get_current":"I{channel}O?",
        "set_remote":"IFLOCK",
        "set_local":"IFUNLOCK",
        "lock_query":True,
        "write_termination":'\n',
        "read_termination":'\r\n',
        "states": {"0": False, "1":True},
        "IRange_states": {"High":2, "Low":1},
        "IRange":"IRANGE{channel} {state}",
    },
    "TSX3510P":{
        "set_voltage":"V{channel} {voltage}",
        "set_current":"I{channel} {current}",
        "get_state":'OP{channel}?',
        "power_on":"OP{channel} 1",
        "power_off":"OP{channel} 0",
        "get_voltage":"V{channel}O?",
        "get_current":"I{channel}O?",
        "lock_query":False,
        "set_remote":"",
        "set_local":"",
        "write_termination":'\n',
        "read_termination":'\r\n',
        "states": {"0": False, "1":True}
    },
    "TSX1820P":{
        "set_voltage":"V {voltage}",
        "set_current":"I {current}",
        "get_state":'', # IO?
        "power_on":"OP 1",
        "power_off":"OP 0",
        "get_voltage":"VO?",
        "get_current":"IO?",
        "lock_query":False,
        "set_remote":"",
        "set_local":"",
        "write_termination":'\n',
        "read_termination":'\n',
        "states": {" 0.00A\n": False, "1":True}
    },
    "PL330DP":{
        "set_voltage":"V{channel} {voltage}",
        "set_current":"I{channel} {current}",
        "get_state":'',
        "power_on":"OP{channel} 1",
        "power_off":"OP{channel} 0",
        "get_voltage":"V{channel}O?",
        "get_current":"I{channel}O?",
        "lock_query":False,
        "set_remote":"",
        "set_local":"",
        "write_termination":'\r\n',
        "read_termination":'\n',
        "states": {' 0.00V\n':False, '':True},
    },
    "E36311A":{
        "set_voltage":"SOUR:VOLT {voltage}, (@{channel})",
        "set_current":"SOUR:CURR {current}, (@{channel})",
        "get_state":'OUTP? (@{channel})',
        "power_on":"OUTP ON, (@{channel})",
        "power_off":"OUTP OFF, (@{channel})",
        "get_voltage":"MEAS:VOLT? (@{channel})",
        "get_current":"MEAS:CURR? (@{channel})",
        "lock_query":False,
        "set_remote":"SYST:RWL",
        "set_local":"SYST:LOC",
        "write_termination":"\r\n",
        "read_termination":"\n",
        "states": {"0": False, "1":True},
        "Mode_states": {"2wire":"INT", "4wire":"EXT"},
        "Mode":"VOLT:SENS:SOUR {state}, (@{channel})",
    },
    "E36312A":{
        "set_voltage":"SOUR:VOLT {voltage}, (@{channel})",
        "set_current":"SOUR:CURR {current}, (@{channel})",
        "get_state":'OUTP? (@{channel})',
        "power_on":"OUTP ON, (@{channel})",
        "power_off":"OUTP OFF, (@{channel})",
        "get_voltage":"MEAS:VOLT? (@{channel})",
        "get_current":"MEAS:CURR? (@{channel})",
        "lock_query":False,
        "set_remote":"SYST:RWL",
        "set_local":"SYST:LOC",
        "write_termination":"\r\n",
        "read_termination":"\n",
        "states": {"0": False, "1":True},
        "Mode_states": {"2wire":"INT", "4wire":"EXT"},
        "Mode":"VOLT:SENS:SOUR {state}, (@{channel})",
    },
    "EDU36311A":{
        "set_voltage":"SOUR:VOLT {voltage}, (@{channel})",
        "set_current":"SOUR:CURR {current}, (@{channel})",
        "get_state":'OUTP? (@{channel})',
        "power_on":"OUTP ON, (@{channel})",
        "power_off":"OUTP OFF, (@{channel})",
        "get_voltage":"MEAS:VOLT? (@{channel})",
        "get_current":"MEAS:CURR? (@{channel})",
        "lock_query":False,
        "set_remote":"SYST:RWL",
        "set_local":"SYST:LOC",
        "write_termination":"\r\n",
        "read_termination":"\n",
        "states": {"0": False, "1":True},
    },
    "GPP-3060":{
        "set_voltage":"SOUR{channel}:VOLT {voltage}",
        "set_current":"SOUR{channel}:CURR {current}",
        "get_state":'OUTP{channel}?',
        "power_on":"OUTP{channel} ON",
        "power_off":"OUTP{channel} OFF",
        "get_voltage":"MEAS{channel}:VOLT?",
        "get_current":"MEAS{channel}:CURR?",
        "lock_query":False,
        "set_remote":"SYST:REM",
        "set_local":"SYST:LOC",
        "write_termination":"\r\n",
        "read_termination":"\n",
        "states": {"OFF": False, "ON":True},
    },
    "MODEL 2470":{
        "set_voltage":":SOUR:VOLT {voltage}",
        "set_current":":SOUR:VOLT:ILIMIT {current}",
        "get_state":'OUTP?',
        "power_on":"OUTP ON",
        "power_off":"OUTP OFF",
        "get_voltage":"MEAS:VOLT?",
        "get_current":"MEAS:CURR?",
        "lock_query":False,
        "set_remote":"",
        "set_local":"",
        "write_termination":"\r\n",
        "read_termination":"\n",
        "states": {"0": False, "1":True},
        # "init": [":SOUR:FUNC VOLT",''':SENSE:FUNC "CURR"''',":ROUT:TERM FRONT",":CURR:RANG:AUTO ON"],
        "init": [":SOUR:FUNC VOLT",":ROUT:TERM FRONT",],
    },

}

