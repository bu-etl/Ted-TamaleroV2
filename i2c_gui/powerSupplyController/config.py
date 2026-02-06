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

supplyConfig = {
    # "Power":{
    #     "type": "regular",
    #     "manufacturer": "THURLBY-THANDAR",
    #     "model": "PL330DP",
    #     "serial": "0",
    # },
    "Power":{
        "type": "regular",
        "manufacturer": "KEITHLEY INSTRUMENTS",
        "model": "MODEL 2470",
        "serial": "04448012",
    },
    # "PowerGW":{
    #     "type": "tcp",
    #     "manufacturer": "GW Instek",
    #     "model": "GPP-3060",
    #     "serial": "Serial",
    #     "resource": "TCPIP0::192.168.10.4::1026::SOCKET",
    # },
}

channelConfig = {
    # "Power":{
    #     "Analog":{
    #         "channel":1,
    #         "config":{"Vset": 1.3 + 0.0,"Ilimit": 0.75,}
    #     },
    #     "Digital":{
    #         "channel":2,
    #         "config":{"Vset": 1.2 + 0.0,"Ilimit": 0.50,}
    #     },
    # },

    # "Power":{
    #     "HV":{
    #         "channel":1,
    #         "config":{"Vset": 5,"Ilimit": 0.0001,}
    #     },
    # },
    "Power":{
        "HV":{
            "channel":1,
            "config":{"Vset": 5,"Ilimit": 0.1,}
        },
    },

    # "Power":{
    #     "Analog":{
    #         "channel":1,
    #         "config":{"Vset": 1.2 + 0.0,"Ilimit": 0.75,"IRange": "High",}
    #     },
    #     "Digital":{
    #         "channel":2,
    #         "config":{"Vset": 1.2 + 0.0,"Ilimit": 0.50,"IRange": "Low",}
    #     },
    # },
}

ignore_list = ["ttyS", "ttyUSB", "ttyACM"]