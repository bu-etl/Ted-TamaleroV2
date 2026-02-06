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

import tkinter as tk
import tkinter.ttk as ttk  # For themed widgets (gives a more native visual to the elements)
import logging
import io
import re
from usb_iss import UsbIss, defs
from PIL import ImageTk, Image

__version__ = '0.0.1'
__register_columns__ = 5
__decoded_columns__ = 2
__swap_endian__ = True  # Whether to swap register address bytes to correct for mixed up endianness
__no_connect__ = True
__platform__ = None
__base_path__ = None

common_configuration_register_map = {
    "PeriCfg0": {
        "address": 0x0000,
        "default": 0x2C,
    },
    "PeriCfg1": {
        "address": 0x0001,
        "default": 0x98,
    },
    "PeriCfg2": {
        "address": 0x0002,
        "default": 0x29,
    },
    "PeriCfg3": {
        "address": 0x0003,
        "default": 0x18,
    },
    "PeriCfg4": {
        "address": 0x0004,
        "default": 0x21,
    },
    "PeriCfg5": {
        "address": 0x0005,
        "default": 0x00,
    },
    "PeriCfg6": {
        "address": 0x0006,
        "default": 0x03,
    },
    "PeriCfg7": {
        "address": 0x0007,
        "default": 0xA3,
    },
    "PeriCfg8": {
        "address": 0x0008,
        "default": 0xE3,
    },
    "PeriCfg9": {
        "address": 0x0009,
        "default": 0xE3,
    },
    "PeriCfg10": {
        "address": 0x000A,
        "default": 0xD0,
    },
    "PeriCfg11": {
        "address": 0x000B,
        "default": 0x10,
    },
    "PeriCfg12": {
        "address": 0x000C,
        "default": 0x00,
    },
    "PeriCfg13": {
        "address": 0x000D,
        "default": 0x80,
    },
    "PeriCfg14": {
        "address": 0x000E,
        "default": 0xF0,
    },
    "PeriCfg15": {
        "address": 0x000F,
        "default": 0x60,
    },
    "PeriCfg16": {
        "address": 0x0010,
        "default": 0x90,
    },
    "PeriCfg17": {
        "address": 0x0011,
        "default": 0x98,
    },
    "PeriCfg18": {
        "address": 0x0012,
        "default": 0x00,
    },
    "PeriCfg19": {
        "address": 0x0013,
        "default": 0x56,
    },
    "PeriCfg20": {
        "address": 0x0014,
        "default": 0x40,
    },
    "PeriCfg21": {
        "address": 0x0015,
        "default": 0x2C,
    },
    "PeriCfg22": {
        "address": 0x0016,
        "default": 0x00,
    },
    "PeriCfg23": {
        "address": 0x0017,
        "default": 0x00,
    },
    "PeriCfg24": {
        "address": 0x0018,
        "default": 0x00,
    },
    "PeriCfg25": {
        "address": 0x0019,
        "default": 0x00,
    },
    "PeriCfg26": {
        "address": 0x001A,
        "default": 0xC5,
    },
    "PeriCfg27": {
        "address": 0x001B,
        "default": 0x8C,
    },
    "PeriCfg28": {
        "address": 0x001C,
        "default": 0xC7,
    },
    "PeriCfg29": {
        "address": 0x001D,
        "default": 0xAC,
    },
    "PeriCfg30": {
        "address": 0x001E,
        "default": 0xBB,
    },
    "PeriCfg31": {
        "address": 0x001F,
        "default": 0x0B,
    },
}

common_status_register_map = {
    "PeriStat0": {
        "address": 0x0000,
        "default": 0x00
    },
    "PeriStat1": {
        "address": 0x0001,
        "default": 0x00
    },
    "PeriStat2": {
        "address": 0x0002,
        "default": 0x00
    },
    "PeriStat3": {
        "address": 0x0003,
        "default": 0x00
    },
    "PeriStat4": {
        "address": 0x0004,
        "default": 0x00
    },
    "PeriStat5": {
        "address": 0x0005,
        "default": 0x00
    },
    "PeriStat6": {
        "address": 0x0006,
        "default": 0x00
    },
    "PeriStat7": {
        "address": 0x0007,
        "default": 0x00
    },
    "PeriStat8": {
        "address": 0x0008,
        "default": 0x00
    },
    "PeriStat9": {
        "address": 0x0009,
        "default": 0x00
    },
    "PeriStat10": {
        "address": 0x000A,
        "default": 0x00
    },
    "PeriStat11": {
        "address": 0x000B,
        "default": 0x00
    },
    "PeriStat12": {
        "address": 0x000C,
        "default": 0x00
    },
    "PeriStat13": {
        "address": 0x000D,
        "default": 0x00
    },
    "PeriStat14": {
        "address": 0x000E,
        "default": 0x00
    },
    "PeriStat15": {
        "address": 0x000F,
        "default": 0x00
    },
}

pixel_configuration_register_map = {
    "PixCfg0": {
        "address": 0x0000,
        "default": 0b1011100,
    },
    "PixCfg1": {
        "address": 0x0001,
        "default": 0b000110,
    },
    "PixCfg2": {
        "address": 0x0002,
        "default": 0b01111,
    },
    "PixCfg3": {
        "address": 0x0003,
        "default": 0b00000101,
    },
    "PixCfg4": {
        "address": 0x0004,
        "default": 0b00000000,
    },
    "PixCfg5": {
        "address": 0x0005,
        "default": 0b00101000,
    },
    "PixCfg6": {
        "address": 0x0006,
        "default": 0b11000010,
    },
    "PixCfg7": {
        "address": 0x0007,
        "default": 0b00000001,
    },
    "PixCfg8": {
        "address": 0x0008,
        "default": 0b10000001,
    },
    "PixCfg9": {
        "address": 0x0009,
        "default": 0b11110101,
    },
    "PixCfg10": {
        "address": 0x000a,
        "default": 0b00010000,
    },
    "PixCfg11": {
        "address": 0x000b,
        "default": 0b00000000,
    },
    "PixCfg12": {
        "address": 0x000c,
        "default": 0b00001000,
    },
    "PixCfg13": {
        "address": 0x000d,
        "default": 0b00000010,
    },
    "PixCfg14": {
        "address": 0x000e,
        "default": 0b10000000,
    },
    "PixCfg15": {
        "address": 0x000f,
        "default": 0b00010000,
    },
    "PixCfg16": {
        "address": 0x0010,
        "default": 0b00000000,
    },
    "PixCfg17": {
        "address": 0x0011,
        "default": 0b01000010,
    },
    "PixCfg18": {
        "address": 0x0012,
        "default": 0b00000000,
    },
    "PixCfg19": {
        "address": 0x0013,
        "default": 0b00100000,
    },
    "PixCfg20": {
        "address": 0x0014,
        "default": 0b00100000,
    },
    "PixCfg21": {
        "address": 0x0015,
        "default": 0b00000000,
    },
    "PixCfg22": {
        "address": 0x0016,
        "default": 0b01000010,
    },
    "PixCfg23": {
        "address": 0x0017,
        "default": 0b00000000,
    },
    "PixCfg24": {
        "address": 0x0018,
        "default": 0b00000100,
    },
    "PixCfg25": {
        "address": 0x0019,
        "default": 0x00,
    },
    "PixCfg26": {
        "address": 0x001a,
        "default": 0x00,
    },
    "PixCfg27": {
        "address": 0x001b,
        "default": 0x00,
    },
    "PixCfg28": {
        "address": 0x001c,
        "default": 0x00,
    },
    "PixCfg29": {
        "address": 0x001d,
        "default": 0x00,
    },
    "PixCfg30": {
        "address": 0x001e,
        "default": 0x00,
    },
    "PixCfg31": {
        "address": 0x001f,
        "default": 0x00,
    },
}

pixel_status_register_map = {
    "PixStat0": {
        "address": 0x0000,
        "default": 0x00
    },
    "PixStat1": {
        "address": 0x0001,
        "default": 0x00
    },
    "PixStat2": {
        "address": 0x0002,
        "default": 0x00
    },
    "PixStat3": {
        "address": 0x0003,
        "default": 0x00
    },
    "PixStat4": {
        "address": 0x0004,
        "default": 0x00
    },
    "PixStat5": {
        "address": 0x0005,
        "default": 0x00
    },
    "PixStat6": {
        "address": 0x0006,
        "default": 0x00
    },
    "PixStat7": {
        "address": 0x0007,
        "default": 0x00
    },
}

common_configuration_register_decoding = {
    "PLL_ClkGen_disCLK": {
        "bits": 1,
        "position": [("PeriCfg0", "0", "0")]  # The tuple should be 1st position is the register, 2nd position the bits in the register, 3rd position the bits in the value
    },
    "PLL_ClkGen_disDES": {
        "bits": 1,
        "position": [("PeriCfg0", "1", "0")]
    },
    "PLL_ClkGen_disEOM": {
        "bits": 1,
        "position": [("PeriCfg0", "2", "0")]
    },
    "PLL_ClkGen_disSER": {
        "bits": 1,
        "position": [("PeriCfg0", "3", "0")]
    },
    "PLL_ClkGen_disVCO": {
        "bits": 1,
        "position": [("PeriCfg0", "4", "0")]
    },
    "CLKSel": {
        "bits": 1,
        "position": [("PeriCfg0", "5", "0")]
    },
    "PLL_FBDiv_clkTreeDisable": {
        "bits": 1,
        "position": [("PeriCfg0", "6", "0")]
    },
    "PLL_FBDiv_skip": {
        "bits": 1,
        "position": [("PeriCfg0", "7", "0")]
    },
    "PLL_BiasGen_CONFIG": {
        "bits": 4,
        "position": [("PeriCfg1", "3-0", "3-0")]
    },
    "PLL_CONFIG_I_PLL": {
        "bits": 4,
        "position": [("PeriCfg1", "7-4", "3-0")]
    },
    "PLL_CONFIG_P_PLL": {
        "bits": 4,
        "position": [("PeriCfg2", "3-0", "3-0")]
    },
    "PLL_R_CONFIG": {
        "bits": 4,
        "position": [("PeriCfg2", "7-4", "3-0")]
    },
}

common_status_register_decoding = {
}

pixel_configuration_register_decoding = {
}

pixel_status_register_decoding = {
}

def validate_8bit_register(string: str):
    digit_regex = r"\d{0,3}"
    hex_regex   = r"0x[a-fA-F\d]{0,2}"

    if string == "":
        return True

    if re.fullmatch(digit_regex, string) is not None:
        if int(string, 10) < 256:
            return True

    if re.fullmatch(hex_regex, string) is not None:
        return True

    return False

def validate_i2c_address(string: str):
    digit_regex = r"\d{0,3}"
    hex_regex   = r"0x[a-fA-F\d]{0,2}"

    if string == "":
        return True

    if re.fullmatch(digit_regex, string) is not None:
        if int(string, 10) < 127:
            return True

    if re.fullmatch(hex_regex, string) is not None:
        if string == "0x" or int(string, 16) < 127:
            return True

    return False

def validate_pixel_index(string: str):
    if string == "":
        return True
    digit_regex = r"\d{0,2}"

    if re.fullmatch(digit_regex, string) is not None:
        if int(string, 10) < 16:
            return True

    return False




class ETROC_I2C_Helper:
    def __init__(self):
        self._parent = None
        self._frame = None

        raise RuntimeError("You should not directly instantiate an ETROC_I2C_Helper class, please use the specific classes for your needs")

    def send_message(self, message: str):
        self._parent.send_message(message=message)

    def modified(self):
        self._parent.modified()

    @property
    def is_connected(self):
        return self._parent.is_connected

    def set_connection_status(self, status: str):
        raise RuntimeError("set_connection_status not implemented for class {}".format(self.__class__.__name__))

    def set_local_status(self, status: str):
        raise RuntimeError("set_local_status not implemented for class {}".format(self.__class__.__name__))

    def broadcast_connection_status(self, value: bool):
        raise RuntimeError("broadcast_connection_status not implemented for class {}".format(self.__class__.__name__))

class ETROC_I2C_Registers_Helper(ETROC_I2C_Helper):
    def __init__(self, parent: ETROC_I2C_Helper, element: tk.Tk, col, row, logger: logging.Logger, base_address, qualifier, frame_title, button_string, register_map, decoding_map):
        self._parent = parent
        self._logger = logger

        self._base_address = base_address
        self._register_map = register_map
        self._decoding_map = decoding_map
        self._qualifier = qualifier
        self._frame_title = frame_title
        self._button_string = button_string

        self._frame = ttk.LabelFrame(element, text=frame_title)
        self._frame.columnconfigure(0, weight=1)
        self._frame.grid(column=col, row=row, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._control_frame = ttk.Frame(self._frame)
        self._control_frame.grid(column=0, row=1, sticky=(tk.N, tk.E))

        self._enabled = False
        self._read_button = ttk.Button(self._control_frame, text="Read " + button_string, command=self.read_all_registers, state="disabled")
        self._read_button.grid(column=0, row=0, sticky=(tk.W, tk.E))

        self._write_button = ttk.Button(self._control_frame, text="Write " + button_string, command=self.write_all_registers, state="disabled")
        self._write_button.grid(column=1, row=0, sticky=(tk.W, tk.E))

        self._register_frame = ttk.Frame(self._frame)
        self._register_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._register_handle = {}
        self._internal_memory = [ None for y in range( len(self._register_map) ) ]
        self._register_display_vars = [ tk.StringVar() for y in range( len(self._register_map) ) ]

        index = 0
        columns = __register_columns__
        for col in range(columns):
            self._register_frame.columnconfigure(col, weight=1)
        for register in self._register_map:
            self._register_handle[register] = ETROC_I2C_Register_Display(self, self._register_frame, register, self._register_map[register], int(index%columns), int(index/columns), logger)
            index += 1

    def build_decoded_display(self, element: tk.Tk, col, row):
        self._decoded_frame = ttk.LabelFrame(element, text=self._frame_title)
        self._decoded_frame.grid(column=col, row=row, sticky=(tk.N, tk.W, tk.E, tk.S), padx=5, pady=5)

        for col in range(__decoded_columns__):
            self._decoded_frame.columnconfigure(col, weight=1)

        self._value_handle = {}

        if self._decoding_map is None:
            return

        self._value_display_vars = {}
        for value in self._decoding_map:
            self._value_display_vars[value] = tk.StringVar()

        registers_to_decode = []
        for value in self._decoding_map:
            for position in self._decoding_map[value]["position"]:
                if position[0] not in registers_to_decode:
                    registers_to_decode += [position[0]]

        self._register_update_lambdas = {}
        for register in registers_to_decode:
            address = self._register_map[register]["address"]
            self._register_update_lambdas[register] = lambda var=None, index=None, mode=None, l_register=register, l_address=address:self._update_value_repr(l_register, l_address, var, index, mode)
            self._register_display_vars[address].trace('w', self._register_update_lambdas[register])

        idx = 0
        for value in self._decoding_map:
            col = int(idx % __decoded_columns__)
            row = int(idx / __decoded_columns__)
            self._value_handle[value] = ETROC_I2C_Value_Display(self, self._decoded_frame, value, self._decoding_map[value], col, row, self._logger)
            idx += 1
        pass

    def _update_value_repr(self, register, address, var, index, mode):
        register_value = self.register_display_var(address=address).get()
        if register_value == "" or register_value == "0x":
            register_value = 0

        for value in self._decoding_map:
            pass

    def register_memory(self, address) -> int:
        return self._internal_memory[address]

    def register_display_var(self, address) -> tk.StringVar:
        return self._register_display_vars[address]

    def value_display_var(self, name) -> tk.StringVar:
        return self._value_display_vars[name]

    def modified(self):
        self._parent.modified()

    def read_register(self, memory_address, byte_count = 1):
        return self._parent.read_register(memory_address=memory_address+self._base_address, byte_count=byte_count)

    def write_register(self, memory_address, data):
        self._parent.write_register(memory_address=memory_address+self._base_address, data=data)

    def read_single_register(self, memory_address):
        self._internal_memory[memory_address] = self.read_register(memory_address=memory_address, byte_count=1)[0]
        self._register_display_vars[memory_address].set(hex(self._internal_memory[memory_address]))

    def write_single_register(self, memory_address):
        if self._register_display_vars[memory_address].get() == "" or self._register_display_vars[memory_address].get() == "0x":
            raise RuntimeError("Somehow an invalid register value state slipped through and was not caught")

        self._internal_memory[memory_address] = int(self._register_display_vars[memory_address].get(), 16)
        self.write_register(memory_address=memory_address, data=[self._internal_memory[memory_address]])

    def read_all_registers(self):
        self.send_message("Read all {} {}".format(self._qualifier, self._frame_title))
        self._internal_memory = self.read_register(memory_address=0, byte_count=len(self._internal_memory))

        for idx in range(len(self._internal_memory)):
            self._register_display_vars[idx].set(hex(self._internal_memory[idx]))

        self._parent.check_modified()

    def write_all_registers(self):
        for register in self._register_handle:
            if not self._register_handle[register].validate_register():
                self.send_message("Unable to write register {}, invalid data".format(register))
                return

        self.send_message("Write all {} {}".format(self._qualifier, self._frame_title))
        for idx in range(len(self._internal_memory)):
            self._internal_memory[idx] = int(self._register_display_vars[idx].get(), 16)

        self.write_register(memory_address=0, data=self._internal_memory)

        self._parent.check_modified()

    def get_register_display(self, register: str):
        return self._register_handle[register]

    def broadcast_connection_status(self, value: bool):
        for register in self._register_handle:
            self._register_handle[register].broadcast_connection_status(value)

        if value == True:
            self._read_button.config(state="normal")
            self._write_button.config(state="normal")
            self._enabled = True
        else:
            self._read_button.config(state="disabled")
            self._write_button.config(state="disabled")
            self._enabled = False

    def is_modified(self):
        for register in self._register_handle:
            if self._register_handle[register].is_modified():
                return True
        return False

    def check_modified(self):
        self._parent.check_modified()

class ETROC_I2C_Value_Display(ETROC_I2C_Helper):
    def __init__(self, parent: ETROC_I2C_Registers_Helper, element: tk.Tk, name, metadata, col, row, logger: logging.Logger):
        self._parent = parent
        self._logger = logger
        self._name = name
        self._metadata = metadata
        self._enabled = False

        self._frame = ttk.LabelFrame(element, text=name)
        self._frame.grid(column=col, row=row, sticky=(tk.N, tk.W, tk.E, tk.S), padx=5, pady=5)

        self._value_label = ttk.Label(self._frame, text="Value:")
        self._value_label.grid(column=0, row=0, sticky=tk.E)

class ETROC_I2C_Register_Display(ETROC_I2C_Helper):
    def __init__(self, parent: ETROC_I2C_Registers_Helper, element: tk.Tk, name, metadata, col, row, logger: logging.Logger):
        self._parent = parent
        self._logger = logger
        self._name = name
        self._metadata = metadata
        self._enabled = False

        self._frame = ttk.LabelFrame(element, text=name)
        self._frame.grid(column=col, row=row, sticky=(tk.N, tk.W, tk.E, tk.S), padx=5, pady=5)

        #self._register_frame = ttk.Frame(self._frame)
        #self._register_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._value_label = ttk.Label(self._frame, text="Value:")
        self._value_label.grid(column=0, row=0, sticky=tk.E)

        self._register_value = self._parent.register_display_var(self._metadata["address"])
        self._register_value.set(hex(self._metadata["default"]))
        self._value = ttk.Entry(self._frame, textvariable=self._register_value, state="disabled", width=5)
        self._value.grid(column=1, row=0, sticky=tk.W)
        self._register_value.trace('w', self._update_binary_repr)

        self._register_validate_cmd = (self._frame.register(validate_8bit_register), '%P')
        self._register_invalid_cmd  = (self._frame.register(self.invalid_register_value), '%P')
        self._value.config(validate='key', validatecommand=self._register_validate_cmd, invalidcommand=self._register_invalid_cmd)


        self._value_binary_label = ttk.Label(self._frame, text="Binary:")
        self._value_binary_label.grid(column=0, row=1, sticky=tk.E)

        self._value_binary_frame = ttk.Frame(self._frame)
        self._value_binary_frame.grid(column=1, row=1)
        self._frame.rowconfigure(1, weight=1)
        self._value_binary_frame.rowconfigure(0, weight=1)

        self._value_binary_prefix = ttk.Label(self._value_binary_frame, font='TkFixedFont', text="0b")
        self._value_binary_prefix.grid(column=0, row=0)

        self._value_binary_bit7 = ttk.Label(self._value_binary_frame, font='TkFixedFont', text="0")
        self._value_binary_bit7.grid(column=1, row=0)
        self._value_binary_bit7.bind("<Button-1>", lambda e:self._toggle_bit(7))

        self._value_binary_bit6 = ttk.Label(self._value_binary_frame, font='TkFixedFont', text="0")
        self._value_binary_bit6.grid(column=2, row=0)
        self._value_binary_bit6.bind("<Button-1>", lambda e:self._toggle_bit(6))

        self._value_binary_bit5 = ttk.Label(self._value_binary_frame, font='TkFixedFont', text="0")
        self._value_binary_bit5.grid(column=3, row=0)
        self._value_binary_bit5.bind("<Button-1>", lambda e:self._toggle_bit(5))

        self._value_binary_bit4 = ttk.Label(self._value_binary_frame, font='TkFixedFont', text="0")
        self._value_binary_bit4.grid(column=4, row=0)
        self._value_binary_bit4.bind("<Button-1>", lambda e:self._toggle_bit(4))

        self._value_binary_bit3 = ttk.Label(self._value_binary_frame, font='TkFixedFont', text="0")
        self._value_binary_bit3.grid(column=5, row=0)
        self._value_binary_bit3.bind("<Button-1>", lambda e:self._toggle_bit(3))

        self._value_binary_bit2 = ttk.Label(self._value_binary_frame, font='TkFixedFont', text="0")
        self._value_binary_bit2.grid(column=6, row=0)
        self._value_binary_bit2.bind("<Button-1>", lambda e:self._toggle_bit(2))

        self._value_binary_bit1 = ttk.Label(self._value_binary_frame, font='TkFixedFont', text="0")
        self._value_binary_bit1.grid(column=7, row=0)
        self._value_binary_bit1.bind("<Button-1>", lambda e:self._toggle_bit(1))

        self._value_binary_bit0 = ttk.Label(self._value_binary_frame, font='TkFixedFont', text="0")
        self._value_binary_bit0.grid(column=8, row=0)
        self._value_binary_bit0.bind("<Button-1>", lambda e:self._toggle_bit(0))


        self._read_button = ttk.Button(self._frame, text="R", state="disabled", command=self.read_register, width=1.5)
        self._read_button.grid(column=3, row=0, sticky=(tk.N, tk.W, tk.E, tk.S), padx=(10,0))

        self._write_button = ttk.Button(self._frame, text="W", state="disabled", command=self.write_register, width=1.5)
        self._write_button.grid(column=3, row=1, sticky=(tk.N, tk.W, tk.E, tk.S), padx=(10,0))


        self._update_binary_repr()

    def _toggle_bit(self, bit_idx):
        if self._enabled:
            value = int(self._register_value.get(), 0)
            self._register_value.set(hex(value ^ (1 << bit_idx)))

    def _update_binary_repr(self, var=None, index=None, mode=None):
        binary_string = "00000000"
        if self._register_value.get() != '' and self._register_value.get() != '0x':  # If value is set, decode the binary string
            binary_string = format(int(self._register_value.get(), 0), 'b')
            if len(binary_string) < 8:
                prepend = '0'*(8-len(binary_string))
                binary_string = prepend + binary_string
        for bit in range(8):
            value = binary_string[7-bit]
            getattr(self, "_value_binary_bit{}".format(bit)).config(text=value)

        if self.is_modified():
            self._parent.modified()
        pass

    def invalid_register_value(self, string: str):
        self.send_message("Invalid value trying to be set for register {}: {}".format(self._name, string))

    def broadcast_connection_status(self, value: bool):
        if value == True:
            self._value.config(state="normal")
            self._read_button.config(state="normal")
            self._write_button.config(state="normal")
            self._enabled = True
        else:
            self._value.config(state="disabled")
            self._read_button.config(state="disabled")
            self._write_button.config(state="disabled")
            self._enabled = False

    def validate_register(self):
        if self._register_value.get() == "" or self._register_value.get() == "0x":
            return False
        self._register_value.set(hex(int(self._register_value.get(), 0)))
        return True

    def read_register(self):
        self.send_message("Reading register {}".format(self._name))
        self._parent.read_single_register(memory_address=self._metadata["address"])

        self._parent.check_modified()

    def write_register(self):
        if not self.validate_register():
            self.send_message("Unable to write register {}, invalid data".format(self._name))
            return

        self.send_message("Writing register {}".format(self._name))
        self._parent.write_single_register(memory_address=self._metadata["address"])

        self._parent.check_modified()

    def is_modified(self):
        if self._parent.register_display_var(self._metadata["address"]).get() == "0x":
            return True
        if self._parent.register_display_var(self._metadata["address"]).get() == "":
            return True
        if self._parent.register_memory(self._metadata["address"]) != int(self._parent.register_display_var(self._metadata["address"]).get(), 0):
            return True
        return False


class ETROC_I2C_Common_Config_Registers(ETROC_I2C_Registers_Helper):
    def __init__(self, parent: ETROC_I2C_Helper, element: tk.Tk, col, row, logger: logging.Logger):
        super().__init__(
            parent=parent,
            element=element,
            col=col,
            row=row,
            logger=logger,
            base_address=0x0000,
            qualifier="Common",
            frame_title="Configuration Registers",
            button_string="Config",
            register_map=common_configuration_register_map,
            decoding_map=common_configuration_register_decoding
            )

class ETROC_I2C_Common_Status_Registers(ETROC_I2C_Registers_Helper):
    def __init__(self, parent: ETROC_I2C_Helper, element: tk.Tk, col, row, logger: logging.Logger):
        super().__init__(
            parent=parent,
            element=element,
            col=col,
            row=row,
            logger=logger,
            base_address=0x0100,
            qualifier="Common",
            frame_title="Status Registers",
            button_string="Status",
            register_map=common_status_register_map,
            decoding_map=None
            )

class ETROC_I2C_Pixel_Config_Registers(ETROC_I2C_Registers_Helper):
    def __init__(self, parent: ETROC_I2C_Helper, element: tk.Tk, col, row, logger: logging.Logger):
        super().__init__(
            parent=parent,
            element=element,
            col=col,
            row=row,
            logger=logger,
            base_address=0x0000,  # Not used because we immediately update it (below)
            qualifier="Pixel",
            frame_title="Configuration Registers",
            button_string="Config",
            register_map=pixel_configuration_register_map,
            decoding_map=None
            )

        self.update_base_address(row=0, column=0, broadcast=False)

        self._modified_base_address = False

    def update_base_address(self, row, column, broadcast):
        base = 0b1000000000000000
        if broadcast:
            base = base | 0b0010000000000000

        base = base | (column << 9)
        base = base | (row << 5)

        if base != self._base_address:
            self._modified_base_address = True
        self._base_address = base

    def is_modified(self):
        if self._modified_base_address:
            return True
        return super().is_modified()

    def read_all_registers(self):
        self._modified_base_address = False
        super().read_all_registers()

    def write_all_registers(self):
        self._modified_base_address = False
        super().write_all_registers()

class ETROC_I2C_Pixel_Status_Registers(ETROC_I2C_Registers_Helper):
    def __init__(self, parent: ETROC_I2C_Helper, element: tk.Tk, col, row, logger: logging.Logger):
        super().__init__(
            parent=parent,
            element=element,
            col=col,
            row=row,
            logger=logger,
            base_address=0x0100,  # Not used because we immediately update it (below)
            qualifier="Pixel",
            frame_title="Status Registers",
            button_string="Status",
            register_map=pixel_status_register_map,
            decoding_map=None
            )

        self.update_base_address(row=0, column=0, broadcast=False)

        self._modified_base_address = False

    def update_base_address(self, row, column, broadcast):
        base = 0b1100000000000000
        if broadcast:
            base = base | 0b0010000000000000

        base = base | (column << 9)
        base = base | (row << 5)

        if base != self._base_address:
            self._modified_base_address = True
        self._base_address = base

    def is_modified(self):
        if self._modified_base_address:
            return True
        return super().is_modified()

    def read_all_registers(self):
        self._modified_base_address = False
        super().read_all_registers()

    def write_all_registers(self):
        self._modified_base_address = False
        super().write_all_registers()

class ETROC_I2C_Register_Notebook(ETROC_I2C_Helper):
    def __init__(self, parent: ETROC_I2C_Helper, col, row, logger: logging.Logger):
        self._parent = parent
        self._logger = logger

        self._notebook = ttk.Notebook(parent._frame)
        self._notebook.grid(column=col, row=row, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._global_frame = ttk.Frame(parent._frame)
        self._global_frame.grid(column=col, row=row+1, sticky=(tk.N, tk.E, tk.S))

        self._enabled = False
        self._read_button = ttk.Button(self._global_frame, text="Read All", command=self.read_all, state="disabled")
        self._read_button.grid(column=0, row=0, sticky=(tk.W, tk.E))

        self._write_button = ttk.Button(self._global_frame, text="Write All", command=self.write_all, state="disabled")
        self._write_button.grid(column=1, row=0, sticky=(tk.W, tk.E))

        self._do_check_modified = False

        # ----------------------- Graphical Interface ----------------------- #
        self._graphical_frame = ttk.Frame(self._notebook)
        self._graphical_frame.columnconfigure(0, weight=1)
        self._graphical_frame.rowconfigure(0, weight=1)
        self._notebook.add(self._graphical_frame, text='Graphical View')

        # ----------------------- Simple Interface ----------------------- #
        self._simple_frame = ttk.Frame(self._notebook)
        self._simple_frame.columnconfigure(0, weight=1)
        self._simple_frame.rowconfigure(0, weight=1)
        self._notebook.add(self._simple_frame, text='Simple View')

        # ----------------------- Common Registers ----------------------- #
        self._frame = ttk.Frame(self._notebook)
        self._frame.columnconfigure(0, weight=1)
        self._frame.rowconfigure(0, weight=1)
        self._notebook.add(self._frame, text='Common Registers')

        self._common_canvas = tk.Canvas(self._frame, borderwidth=0, highlightthickness=0)
        self._common_canvas.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._common_scrollbar = ttk.Scrollbar(self._frame, command=self._common_canvas.yview)
        self._common_scrollbar.grid(column=1, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._common_frame = ttk.Frame(self._common_canvas)
        self._common_frame.columnconfigure(0, weight=1)
        self._common_window = self._common_canvas.create_window(0, 0, window=self._common_frame, anchor=tk.N+tk.W)

        self._common_config = ETROC_I2C_Common_Config_Registers(self, self._common_frame, 0, 0, logger)
        self._common_status = ETROC_I2C_Common_Status_Registers(self, self._common_frame, 0, 1, logger)

        self._frame.update_idletasks()
        self._common_canvas.config(width=self._common_frame.winfo_reqwidth(), height=min(700, self._common_frame.winfo_reqheight()))
        self._common_canvas.config(yscrollcommand=self._common_scrollbar.set,
                                   scrollregion=(
                                    0,
                                    0,
                                    self._common_frame.winfo_reqwidth(),
                                    self._common_frame.winfo_reqheight()
                                    ))
        self._common_canvas.bind('<Configure>', self._update_common_canvas)
        self._frame.bind('<Enter>', self._bound_frame1_to_mousewheel)
        self._frame.bind('<Leave>', self._unbound_frame1_to_mousewheel)

        # ----------------------- Pixel Registers ----------------------- #
        self._frame2 = ttk.Frame(self._notebook)
        self._frame2.columnconfigure(0, weight=1)
        self._frame2.rowconfigure(0, weight=1)
        self._notebook.add(self._frame2, text='Pixel Registers')

        self._pixel_canvas = tk.Canvas(self._frame2, borderwidth=0, highlightthickness=0)
        self._pixel_canvas.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._pixel_scrollbar = ttk.Scrollbar(self._frame2, command=self._pixel_canvas.yview)
        self._pixel_scrollbar.grid(column=1, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._pixel_frame = ttk.Frame(self._pixel_canvas)
        self._pixel_frame.columnconfigure(0, weight=1)
        self._pixel_window = self._pixel_canvas.create_window(0, 0, window=self._pixel_frame, anchor=tk.N+tk.W)

        self._pixel_selection_frame = ttk.LabelFrame(self._pixel_frame, text="Pixel Selection")
        self._pixel_selection_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._row_label = ttk.Label(self._pixel_selection_frame, text="Row:")
        self._row_label.grid(column=0, row=0, sticky=(tk.W, tk.E), padx=(10,0))

        self._row_var = tk.StringVar()
        self._row_var.set("0")
        self._row_entry = ttk.Entry(self._pixel_selection_frame, textvariable=self._row_var, width=3, state="disabled")
        self._row_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=(0,30))

        self._row_validate_cmd = (self._frame.register(validate_pixel_index), '%P')
        self._row_invalid_cmd  = (self._frame.register(self.invalid_pixel_row), '%P')
        self._row_entry.config(validate='key', validatecommand=self._row_validate_cmd, invalidcommand=self._row_invalid_cmd)

        self._column_label = ttk.Label(self._pixel_selection_frame, text="Column:")
        self._column_label.grid(column=2, row=0, sticky=(tk.W, tk.E))

        self._column_var = tk.StringVar()
        self._column_var.set("0")
        self._column_entry = ttk.Entry(self._pixel_selection_frame, textvariable=self._column_var, width=3, state="disabled")
        self._column_entry.grid(column=3, row=0, sticky=(tk.W, tk.E), padx=(0,30))

        self._column_validate_cmd = (self._frame.register(validate_pixel_index), '%P')
        self._column_invalid_cmd  = (self._frame.register(self.invalid_pixel_column), '%P')
        self._column_entry.config(validate='key', validatecommand=self._column_validate_cmd, invalidcommand=self._column_invalid_cmd)

        self._pixel_selection_frame.columnconfigure(4, weight=1)

        self._broadcast_var = tk.BooleanVar(value=False)
        self._broadcast_check = ttk.Checkbutton(self._pixel_selection_frame, text="Broadcast command", variable=self._broadcast_var, state="disabled")
        self._broadcast_check.grid(column=5, row=0, sticky=(tk.W, tk.E), padx=(0,0))

        self._row_var.trace('w', self.update_pixel_base_address)
        self._column_var.trace('w', self.update_pixel_base_address)
        self._broadcast_var.trace('w', self.update_pixel_base_address)

        self._pixel_selection_frame.columnconfigure(6, weight=1)

        self._pixel_config = ETROC_I2C_Pixel_Config_Registers(self, self._pixel_frame, 0, 1, logger)
        self._pixel_status = ETROC_I2C_Pixel_Status_Registers(self, self._pixel_frame, 0, 2, logger)

        self._frame2.update_idletasks()
        self._pixel_canvas.config(width=self._pixel_frame.winfo_reqwidth(), height=min(700, self._pixel_frame.winfo_reqheight()))
        self._pixel_canvas.config(yscrollcommand=self._pixel_scrollbar.set,
                                   scrollregion=(
                                    0,
                                    0,
                                    self._pixel_frame.winfo_reqwidth(),
                                    self._pixel_frame.winfo_reqheight()
                                    ))
        self._pixel_canvas.bind('<Configure>', self._update_pixel_canvas)
        self._frame2.bind('<Enter>', self._bound_frame2_to_mousewheel)
        self._frame2.bind('<Leave>', self._unbound_frame2_to_mousewheel)

        # ----------------------- Common Registers Decoded ----------------------- #
        self._frame3 = ttk.Frame(self._notebook)
        self._frame3.columnconfigure(0, weight=1)
        self._frame3.rowconfigure(0, weight=1)
        self._notebook.add(self._frame3, text='Common Registers Decoded')

        self._common_decoded_canvas = tk.Canvas(self._frame3, borderwidth=0, highlightthickness=0)
        self._common_decoded_canvas.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._common_decoded_scrollbar = ttk.Scrollbar(self._frame3, command=self._common_decoded_canvas.yview)
        self._common_decoded_scrollbar.grid(column=1, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._common_decoded_frame = ttk.Frame(self._common_decoded_canvas)
        self._common_decoded_frame.columnconfigure(0, weight=1)
        self._common_decoded_frame.columnconfigure(1, weight=1)
        self._common_decoded_window = self._common_decoded_canvas.create_window(0, 0, window=self._common_decoded_frame, anchor=tk.N+tk.W)

        self._common_config.build_decoded_display(self._common_decoded_frame, 0, 0)
        self._common_status.build_decoded_display(self._common_decoded_frame, 1, 0)

        self._frame3.update_idletasks()
        self._common_decoded_canvas.config(width=self._common_decoded_frame.winfo_reqwidth(), height=min(700, self._common_decoded_frame.winfo_reqheight()))
        self._common_decoded_canvas.config(yscrollcommand=self._common_decoded_scrollbar.set,
                                   scrollregion=(
                                    0,
                                    0,
                                    self._common_decoded_frame.winfo_reqwidth(),
                                    self._common_decoded_frame.winfo_reqheight()
                                    ))
        self._common_decoded_canvas.bind('<Configure>', self._update_common_decoded_canvas)
        self._frame3.bind('<Enter>', self._bound_frame3_to_mousewheel)
        self._frame3.bind('<Leave>', self._unbound_frame3_to_mousewheel)

        # ----------------------- Pixel Registers Decoded ----------------------- #
        self._frame4 = ttk.Frame(self._notebook)
        self._frame4.columnconfigure(0, weight=1)
        self._frame4.rowconfigure(0, weight=1)
        self._notebook.add(self._frame4, text='Pixel Registers Decoded')

        self._pixel_decoded_canvas = tk.Canvas(self._frame4, borderwidth=0, highlightthickness=0)
        self._pixel_decoded_canvas.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._pixel_decoded_scrollbar = ttk.Scrollbar(self._frame4, command=self._pixel_decoded_canvas.yview)
        self._pixel_decoded_scrollbar.grid(column=1, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._pixel_decoded_frame = ttk.Frame(self._pixel_decoded_canvas)
        self._pixel_decoded_frame.columnconfigure(0, weight=1)
        self._pixel_decoded_frame.columnconfigure(1, weight=1)
        self._pixel_decoded_window = self._pixel_decoded_canvas.create_window(0, 0, window=self._pixel_decoded_frame, anchor=tk.N+tk.W)

        self._pixel_config.build_decoded_display(self._pixel_decoded_frame, 0, 0)
        self._pixel_status.build_decoded_display(self._pixel_decoded_frame, 1, 0)

        self._frame4.update_idletasks()
        self._pixel_decoded_canvas.config(width=self._pixel_decoded_frame.winfo_reqwidth(), height=min(700, self._pixel_decoded_frame.winfo_reqheight()))
        self._pixel_decoded_canvas.config(yscrollcommand=self._pixel_decoded_scrollbar.set,
                                   scrollregion=(
                                    0,
                                    0,
                                    self._pixel_decoded_frame.winfo_reqwidth(),
                                    self._pixel_decoded_frame.winfo_reqheight()
                                    ))
        self._pixel_decoded_canvas.bind('<Configure>', self._update_pixel_decoded_canvas)
        self._frame4.bind('<Enter>', self._bound_frame4_to_mousewheel)
        self._frame4.bind('<Leave>', self._unbound_frame4_to_mousewheel)


        self._do_check_modified = True
        self._connected = False

    def update_pixel_base_address(self, var=None, index=None, mode=None):
        row = self._row_var.get()
        column = self._column_var.get()

        if row == "":
            row = 0
        else:
            row = int(row)

        if column == "":
            column = 0
        else:
            column = int(column)

        if self._broadcast_var.get():
            self.send_message("Updating pixel address to pixel: ({}, {}) [with broadcast]".format(row, column))
        else:
            self.send_message("Updating pixel address to pixel: ({}, {}) [no broadcast]".format(row, column))

        self._pixel_config.update_base_address(
            row = row,
            column = column,
            broadcast = self._broadcast_var.get()
        )

        self._pixel_status.update_base_address(
            row = row,
            column = column,
            broadcast = self._broadcast_var.get()
        )

        self.check_modified()

    def invalid_pixel_row(self, row: str):
        self.send_message("Invalid row value for pixel index: {}".format(row))

    def invalid_pixel_column(self, column: str):
        self.send_message("Invalid column value for pixel index: {}".format(column))

    def _bound_frame1_to_mousewheel(self, event: tk.Event):
        self._common_canvas.bind_all("<MouseWheel>", self._frame1_on_mousewheel)

    def _unbound_frame1_to_mousewheel(self, event: tk.Event):
        self._common_canvas.unbind_all("<MouseWheel>")

    def _bound_frame2_to_mousewheel(self, event: tk.Event):
        self._pixel_canvas.bind_all("<MouseWheel>", self._frame2_on_mousewheel)

    def _unbound_frame2_to_mousewheel(self, event: tk.Event):
        self._pixel_canvas.unbind_all("<MouseWheel>")

    def _bound_frame3_to_mousewheel(self, event: tk.Event):
        self._common_decoded_canvas.bind_all("<MouseWheel>", self._frame3_on_mousewheel)

    def _unbound_frame3_to_mousewheel(self, event: tk.Event):
        self._common_decoded_canvas.unbind_all("<MouseWheel>")

    def _bound_frame4_to_mousewheel(self, event: tk.Event):
        self._pixel_decoded_canvas.bind_all("<MouseWheel>", self._frame4_on_mousewheel)

    def _unbound_frame4_to_mousewheel(self, event: tk.Event):
        self._pixel_decoded_canvas.unbind_all("<MouseWheel>")

    def _mousewheel_scroll(self, event: tk.Event, canvas: tk.Canvas):
        if __platform__ == "aqua":
            canvas.yview_scroll(int(-1*(event.delta)), "units")
        else:
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _frame1_on_mousewheel(self, event: tk.Event):
        self._mousewheel_scroll(event, self._common_canvas)

    def _frame2_on_mousewheel(self, event: tk.Event):
        self._mousewheel_scroll(event, self._pixel_canvas)

    def _frame3_on_mousewheel(self, event: tk.Event):
        self._mousewheel_scroll(event, self._common_decoded_canvas)

    def _frame4_on_mousewheel(self, event: tk.Event):
        self._mousewheel_scroll(event, self._pixel_decoded_canvas)

    def _update_common_canvas(self, event: tk.Event):
        self._common_canvas.itemconfigure(self._common_window, width=event.width)

    def _update_common_decoded_canvas(self, event: tk.Event):
        self._common_decoded_canvas.itemconfigure(self._common_decoded_window, width=event.width)

    def _update_pixel_canvas(self, event: tk.Event):
        self._pixel_canvas.itemconfigure(self._pixel_window, width=event.width)

    def _update_pixel_decoded_canvas(self, event: tk.Event):
        self._pixel_decoded_canvas.itemconfigure(self._pixel_decoded_window, width=event.width)

    def broadcast_connection_status(self, value: bool):
        self._common_config.broadcast_connection_status(value)
        self._common_status.broadcast_connection_status(value)
        self._pixel_config.broadcast_connection_status(value)
        self._pixel_status.broadcast_connection_status(value)

        if value == True:
            self._read_button.config(state="normal")
            self._write_button.config(state="normal")
            self._column_entry.config(state="normal")
            self._row_entry.config(state="normal")
            self._broadcast_check.config(state="normal")
            self._enabled = True
        else:
            self._read_button.config(state="disabled")
            self._write_button.config(state="disabled")
            self._column_entry.config(state="disabled")
            self._row_entry.config(state="disabled")
            self._broadcast_check.config(state="disabled")
            self._enabled = False

        if value == True and value != self._connected:
            self.read_all()

        self._connected = value

    def read_register(self, memory_address, byte_count = 1):
        return self._parent.read_register(memory_address=memory_address, byte_count=byte_count)

    def write_register(self, memory_address, data):
        self._parent.write_register(memory_address=memory_address, data=data)

    def read_all(self):
        self.send_message("Read all registers")
        self._do_check_modified = False
        self._common_config.read_all_registers()
        self._common_status.read_all_registers()
        self._pixel_config.read_all_registers()
        self._pixel_status.read_all_registers()
        # Add others here too
        self._do_check_modified = True

        self.check_modified()

    def write_all(self):
        self.send_message("Write all registers")
        self._do_check_modified = False
        self._common_config.write_all_registers()
        self._common_status.write_all_registers()
        self._pixel_config.write_all_registers()
        self._pixel_status.write_all_registers()
        # Add others here too
        self._do_check_modified = True

        self.check_modified()

    def check_modified(self):
        if not self._do_check_modified:
            return

        modified = False

        if self._common_config.is_modified():
            modified = True
        if self._common_status.is_modified():
            modified = True
        if self._pixel_config.is_modified():
            modified = True
        if self._pixel_status.is_modified():
            modified = True

        if modified:
            self._parent.set_local_status("Modified")
        else:
            self._parent.set_local_status("Unmodified")

class ETROC_I2C_Status(ETROC_I2C_Helper):
    def __init__(self, parent: ETROC_I2C_Helper, col, row, logger: logging.Logger):
        self._parent = parent
        self._logger = logger

        self._stream = io.StringIO()
        self._stream_handler = logging.StreamHandler(self._stream)
        self._stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s:%(name)s:%(message)s'))
        self._logger.handlers.clear()
        self._do_logging = False
        self._logger.disabled = True
        self._logging_window_status_var = tk.StringVar()
        self._logging_window_status_var.set("Logging Disabled")

        self._frame = ttk.Frame(parent._frame)
        self._frame.grid(column=col, row=row, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._connection_status_var = tk.StringVar()
        self._connection_status_var.set("Not Connected")

        self._local_status_var = tk.StringVar()
        self._local_status_var.set("Unknown")

        self._message_var = tk.StringVar()

        self._connection_status = ttk.Label(self._frame, textvariable=self._connection_status_var)
        self._connection_status.grid(column=0, row=0, sticky=(tk.W, tk.E), padx=(0,15))

        self._local_status = ttk.Label(self._frame, textvariable=self._local_status_var)
        self._local_status.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=(0,15))

        self._message = ttk.Label(self._frame, textvariable=self._message_var)
        self._message.grid(column=2, row=0, sticky=tk.E)
        self._frame.columnconfigure(2, weight=1)

        self._connect_button = ttk.Button(self._frame, text="Logging", command=self.display_logging)
        self._connect_button.grid(column=3, row=0, sticky=(tk.W, tk.E), padx=(10,0))

    @property
    def connection_status(self):
        return self._connection_status_var.get()

    @connection_status.setter
    def connection_status(self, value):
        if value not in ["Not Connected", "Connected", "Error"]:
            raise ValueError("Invalid connection status was attempted to be set: \"{}\"".format(value))
        self._connection_status_var.set(value)

    @property
    def local_status(self):
        return self._local_status_var.get()

    @local_status.setter
    def local_status(self, value):
        if value not in ["Unknown", "Modified", "Unmodified", "Error"]:
            raise ValueError("Invalid local status was attempted to be set: \"{}\"".format(value))
        self._local_status_var.set(value)

    @property
    def logging(self):
        return self._do_logging

    @logging.setter
    def logging(self, value):
        if value not in [True, False]:
            raise TypeError("Logging can only be true or false")

        self._do_logging = value

        if self._do_logging:
            if self._stream_handler not in self._logger.handlers:
                self._logger.addHandler(self._stream_handler)
            self._logger.disabled = False
            self._logging_window_status_var.set("Logging Enabled")
        else:
            if self._stream_handler in self._logger.handlers:
                self._logger.removeHandler(self._stream_handler)
            self._logger.disabled = True
            self._logging_window_status_var.set("Logging Disabled")


    def send_message(self, message: str):
        self._logger.info("Message: {}".format(message))
        self._message_var.set(message)

    def get_log(self):
        return self._stream.getvalue()

    def display_logging(self):
        if hasattr(self, "_logging_window"):
            self._logger.info("Logging window already open")
            return

        # Find the parent which holds the root window
        parent = self._parent
        while not hasattr(parent, "_root"):
            parent = parent._parent

        self._logging_window = tk.Toplevel(parent._root)
        self._logging_window.title("ETROC I2C GUI - Event Logs")
        self._logging_window.protocol('WM_DELETE_WINDOW', self.close_logging)
        self._logging_window.columnconfigure(0, weight=1)
        self._logging_window.rowconfigure(0, weight=1)

        self._logging_frame = ttk.Frame(self._logging_window, padding="5 5 5 5")
        self._logging_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self._logging_frame.columnconfigure(0, weight=1)
        self._logging_frame.rowconfigure(0, weight=1)

        self._logging_text_frame = ttk.Frame(self._logging_frame)
        self._logging_text_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self._logging_text_frame.columnconfigure(0, weight=1)
        self._logging_text_frame.rowconfigure(0, weight=1)

        self._logging_text = tk.Text(self._logging_text_frame, state='disabled', width=150, wrap='none')
        self._logging_text.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._logging_scrollbar = ttk.Scrollbar(self._logging_text_frame, command=self._logging_text.yview)
        self._logging_scrollbar.grid(row=0, column=1, sticky='nsew')
        self._logging_text.config(yscrollcommand=self._logging_scrollbar.set)

        self._logging_bottom = ttk.Frame(self._logging_frame)
        self._logging_bottom.grid(column=0, row=1, sticky=(tk.N, tk.W, tk.E, tk.S))
        self._logging_bottom.columnconfigure(2, weight=1)

        self._enable_logging_button = ttk.Button(self._logging_bottom, text="Enable Logging", command=self.enable_logging)
        self._enable_logging_button.grid(column=0, row=0, sticky=(tk.W, tk.E), padx=(0,5))

        self._enable_logging_button = ttk.Button(self._logging_bottom, text="Disable Logging", command=self.disable_logging)
        self._enable_logging_button.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=(0,5))

        self._logging_status_label = ttk.Label(self._logging_bottom, textvariable=self._logging_window_status_var)
        self._logging_status_label.grid(column=2, row=0, sticky=(tk.W, tk.E), padx=(0,30))

        self._autorefresh_val = tk.BooleanVar(value=False)
        self._autorefresh_check = ttk.Checkbutton(self._logging_bottom, text="Auto-refresh", variable=self._autorefresh_val, command=self.toggle_autorefresh)
        self._autorefresh_check.grid(column=3, row=0, sticky=(tk.W, tk.E), padx=(0,10))

        self._refresh_button = ttk.Button(self._logging_bottom, text="Refresh", command=self.refresh_logging)
        self._refresh_button.grid(column=4, row=0, sticky=(tk.W, tk.E))

        self._logging_window.update()
        self._logging_window.minsize(self._logging_window.winfo_width(), self._logging_window.winfo_height())

    def toggle_autorefresh(self):
        autorefresh = self._autorefresh_val.get()
        if autorefresh:
            self.send_message("Turn on logging auto-refresh")
            self.autorefresh_logging()
            self._refresh_button.configure(state='disabled', text="Disabled")
        else:
            self.send_message("Turn off logging auto-refresh")
            self._refresh_button.configure(state='normal', text="Refresh")

    def autorefresh_logging(self):
        self.refresh_logging()

        autorefresh = self._autorefresh_val.get()
        if autorefresh:
            self._logging_text.after(500, self.autorefresh_logging)

    def close_logging(self):
        if not hasattr(self, "_logging_window"):
            self._logger.info("Logging window does not exist")
            return

        self._logging_window.destroy()
        del self._logging_window

    def enable_logging(self):
        self.logging = True

    def disable_logging(self):
        self.logging = False

    def refresh_logging(self):
        pos = self._logging_scrollbar.get()
        vw = self._logging_text.yview()

        #print(pos)
        #print(vw)
        # TODO: Scrollbar is still jumping around when updating. It is related to when the lines of text wrap to the next line
        # Disabling line wrapping seems to have "fixed" (hidden) the issue

        self._logging_text.configure(state='normal')
        self._logging_text.delete("1.0", tk.END)
        self._logging_text.insert('end', self.get_log())
        self._logging_text.configure(state='disabled')
        #self._logging_text.yview_moveto(pos[0])
        self._logging_text.yview_moveto(vw[0])

class ETROC_I2C_Global_Controls(ETROC_I2C_Helper):
    def __init__(self, parent: ETROC_I2C_Helper, col, row, logger: logging.Logger):
        self._parent = parent
        self._logger = logger

        self._frame = ttk.Frame(parent._frame)
        self._frame.grid(column=col, row=row, sticky=(tk.N, tk.W, tk.E, tk.S))


    def broadcast_connection_status(self, value: bool):
        pass

class ETROC_I2C_Connection_Display(ETROC_I2C_Helper):
    def __init__(self, parent: ETROC_I2C_Helper, col, row, logger: logging.Logger):
        self._is_connected = False
        self._logger = logger

        self._iss = UsbIss()

        self._parent = parent
        self._frame = ttk.LabelFrame(parent._frame, text="Connection Configuration")
        self._frame.grid(column=col, row=row, sticky=(tk.N, tk.W, tk.E, tk.S))

        self._port_label = ttk.Label(self._frame, text="Port:")
        self._port_label.grid(column=0, row=0, sticky=(tk.W, tk.E))

        self._port_var = tk.StringVar()
        self._port_var.set("COM3")
        self._port = ttk.Entry(self._frame, textvariable=self._port_var, width=10)
        self._port.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=(0,30))

        self._frame.columnconfigure(2, weight=1)

        self._clk_options = [ # These are the frequencies supported by the USB-ISS module (in kHz), two of them are supported in both hardware and software
            20,   # Supported in software bit bashed
            50,   # Supported in software bit bashed
            100,  # Supported in software bit bashed and hardware
            400,  # Supported in software bit bashed and hardware
            1000  # Supported in hardware
        ]

        self._clk_label = ttk.Label(self._frame, text="Clock Frequency:")
        self._clk_label.grid(column=3, row=0, sticky=(tk.W, tk.E))

        self._clk_var = tk.IntVar(self._frame)
        self._clk = ttk.OptionMenu(self._frame, self._clk_var, self._clk_options[2], *self._clk_options)
        self._clk.grid(column=4, row=0, sticky=(tk.W, tk.E))

        self._clk_units_label = ttk.Label(self._frame, text="kHz")
        self._clk_units_label.grid(column=5, row=0, sticky=(tk.W, tk.E), padx=(0,30))

        self._frame.columnconfigure(6, weight=1)

        self._i2c_address_label = ttk.Label(self._frame, text="I2C Address:")
        self._i2c_address_label.grid(column=7, row=0, sticky=(tk.W, tk.E))

        self._i2c_address_var = tk.StringVar()
        self._i2c_address_var.set("0x72")
        self._i2c_address = ttk.Entry(self._frame, textvariable=self._i2c_address_var, width=5)
        self._i2c_address.grid(column=8, row=0, sticky=(tk.W, tk.E), padx=(0,30))

        self._i2c_validate_cmd = (self._frame.register(validate_i2c_address), '%P')
        self._i2c_invalid_cmd  = (self._frame.register(self.invalid_i2c_address), '%P')
        self._i2c_address.config(validate='key', validatecommand=self._i2c_validate_cmd, invalidcommand=self._i2c_invalid_cmd)

        self._frame.columnconfigure(9, weight=1)

        self._connect_button = ttk.Button(self._frame, text="Connect", command=self.connect)
        self._connect_button.grid(column=10, row=0, sticky=(tk.W, tk.E))

    def connect(self):
        if self.is_connected:
            self.disconnect()

        if self._i2c_address_var.get() == "0x" or self._i2c_address_var.get() == "":
            self.send_message("Please enter a valid I2C address")
            return
        if self._port_var.get() == "":
            self.send_message("Please enter a valid port")
            return

        i2c_address = hex(int(self._i2c_address_var.get(), 0))
        self._i2c_address_var.set(i2c_address)

        port = self._port_var.get()

        # Use hardware I2C
        use_hardware = True
        if self._clk_var.get() < 100:
            use_hardware = False

        if not __no_connect__:
            try:
                self._iss.open(port)
                self._iss.setup_i2c(clock_khz=self._clk_var.get(), use_i2c_hardware=use_hardware)
                if not self._iss.i2c.test(int(i2c_address, 16)):
                    raise RuntimeError("Unable to connect")
            except:
                self.send_message("Unable to connect to a device at address {} on port {} using I2C at {} kHz".format(i2c_address, port, self._clk_var.get()))
                return

        self._connected_i2c_address = int(i2c_address, 16)

        # If connection successfull:
        self._connect_button.config(text="Disconnect", command=self.disconnect)
        self._port.config(state="disabled")
        self._clk.config(state="disabled")
        self._i2c_address.config(state="disabled")
        self._parent.set_connection_status("Connected")
        self.is_connected = True
        pass

    def disconnect(self):
        if not self.is_connected:
            return

        self._iss.close()

        self._connect_button.config(text="Connect", command=self.connect)
        self._port.config(state="normal")
        self._clk.config(state="normal")
        self._i2c_address.config(state="normal")
        self._parent.set_connection_status("Not Connected")
        self._parent.set_local_status("Unknown")
        self.is_connected = False
        pass

    @property
    def is_connected(self):
        return self._is_connected

    @is_connected.setter
    def is_connected(self, value):
        if value != self._is_connected:
            if value:
                self.send_message("Connected to I2C device at address {} with a bitrate of {} kHz through port {}".format(self._i2c_address_var.get(), self._clk_var.get(), self._port_var.get()))
            else:
                self.send_message("Disconnected from I2C device at address {} with a bitrate of {} kHz through port {}".format(self._i2c_address_var.get(), self._clk_var.get(), self._port_var.get()))
            self._is_connected = value
            self._parent.broadcast_connection_status(value)

    def invalid_i2c_address(self, address: str):
        self.send_message("{} is an invalid I2C device address".format(address))

    def read_register(self, memory_address, byte_count = 1):
        if __no_connect__:
            retVal = []
            for i in range(byte_count):
                retVal += [i]
            if byte_count == 1:
                retVal[0] = 0x42
            return retVal

        if not self.is_connected:
            raise RuntimeError("You must first connect to a device before trying to read registers from it")

        if __swap_endian__:
            memory_address = self.swap_endian(memory_address)

        return self._iss.i2c.read_ad2(self._connected_i2c_address, memory_address, byte_count)

    def write_register(self, memory_address, data):
        if __no_connect__:
            return

        if not self.is_connected:
            raise RuntimeError("You must first connect to a device before trying to write registers to it")

        if __swap_endian__:
            memory_address = self.swap_endian(memory_address)

        self._iss.i2c.write_ad2(self._connected_i2c_address, memory_address, data)

    def swap_endian(self, address):
        tmp = hex(address)
        low_byte = tmp[-2:]
        high_byte = tmp[-4:-2]
        return int("0x" + low_byte + high_byte, 16)

class ETROC_I2C_GUI(ETROC_I2C_Helper):
    def __init__(self, root: tk.Tk, logger: logging.Logger):
        self._parent = None
        self._logger = logger
        self._root = root

        self._platform = root.tk.call('tk', 'windowingsystem')
        if self._platform not in ["x11", "win32", "aqua"]:
            raise RuntimeError("Unknown platform: {}".format(self._platform))
        self._root.protocol('WM_DELETE_WINDOW', self.close_window)  # In order that we can control shutdown and safely close anything if needed

        root.title("ETROC I2C GUI")

        self._frame = ttk.Frame(root, padding="5 5 5 5")
        self._frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self._frame.columnconfigure(0, weight=1)
        self._frame.rowconfigure(1, weight=1)

        self._connection = ETROC_I2C_Connection_Display(self, 0, 0, logger)
        self._registers = ETROC_I2C_Register_Notebook(self, 0, 1, logger)  # Notebook will try to use an additional row to show global controls
        self._status = ETROC_I2C_Status(self, 0, 3, logger)

        # Configure Menu
        root.option_add('*tearOff', tk.FALSE)

        menubar = tk.Menu(root)

        if self._platform == "aqua":
            # MacOS Guidelines: https://developer.apple.com/design/human-interface-guidelines/platforms/designing-for-macos/#//apple_ref/doc/uid/20000957-CH23-SW1
            # https://developer.apple.com/design/human-interface-guidelines/components/system-experiences/the-menu-bar
            appmenu = tk.Menu(menubar, name='apple')
            menubar.add_cascade(menu=appmenu)
            appmenu.add_command(label='About ETROC I2C GUI', command=self.show_about)
            appmenu.add_separator()
            # If a preferences window exists:
            # root.createcommand('tk::mac::ShowPreferences', showMyPreferencesDialog)

            windowmenu = tk.Menu(menubar, name='window')
            menubar.add_cascade(menu=windowmenu, label='Window')

            helpmenu = tk.Menu(menubar, name='help')
            menubar.add_cascade(menu=helpmenu, label='Help')
            root.createcommand('tk::mac::ShowHelp', self.show_about)  # For now, we will use the about menu for help since the program is simple
        elif self._platform == "win32":
            sysmenu = tk.Menu(menubar, name='system')
            menubar.add_cascade(menu=sysmenu)
            # TODO: Do we need to add any options here or will it be auto-populated?
            # https://tkdocs.com/tutorial/menus.html

        # elif self._platform == "x11":  # Linux will handle the help menu specially and place it at the end
        if self._platform != "aqua":
            helpmenu = tk.Menu(menubar, name='help')
            menubar.add_cascade(menu=helpmenu, label='Help')
            helpmenu.add_command(label='About ETROC I2C GUI', command=self.show_about)

        root.config(menu=menubar)

    def show_about(self):
        if hasattr(self, "_about_win"):
            self._logger.info("About window already open")
            return

        self._about_win = tk.Toplevel(self._root)
        self._about_win.protocol('WM_DELETE_WINDOW', self.close_about)

        self._about_win.title("About ETROC I2C GUI")
        self._about_win.geometry("500x500")
        self._about_win.resizable(0, 0)
        self._about_win.grid_columnconfigure(0, weight=1)
        self._about_win.rowconfigure(0, weight=1)

        self._about_frame = ttk.Frame(self._about_win, padding="5 5 5 5")
        self._about_frame.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self._about_frame.columnconfigure(0, weight=1)

        #self._about_img_frame = ttk.Frame(self._about_frame)
        #self._about_img_frame.grid(column=0, row=0)#, sticky=(tk.N, tk.W, tk.E, tk.S))
        #self._about_img_frame.columnconfigure(0, weight=1)
        #self._about_img_frame.columnconfigure(2, weight=1)

        self._about_img = ImageTk.PhotoImage(Image.open(__base_path__ + "/About.png"))
        self._about_img_label = tk.Label(self._about_frame, image = self._about_img)
        self._about_img_label.grid(column=0, row=0, sticky='')

        self._about_info_label = tk.Label(self._about_frame, text="ETROC I2C GUI - v{}".format(__version__))
        self._about_info_label.grid(column=0, row=1, sticky='')

        self._about_info_label = tk.Label(self._about_frame, justify=tk.LEFT, wraplength=450, text="The ETROC I2C GUI was developed to read and write I2C registers from a connected ETROC device using a USB-ISS serial adapter. The code was developed and tested using the ETROC2 Emulator")
        self._about_info_label.grid(column=0, row=2, sticky='')

        self._about_copy_label = tk.Label(self._about_frame, justify=tk.LEFT, wraplength=490, text="Tool written and developed by Cristóvão Beirão da Cruz e Silva - © 2022")
        self._about_copy_label.grid(column=0, row=3, sticky=tk.S)
        self._about_frame.rowconfigure(3, weight=1)

    def close_about(self):
        if not hasattr(self, "_about_win"):
            self._logger.info("About window does not exist")
            return

        self._about_win.destroy()
        del self._about_win

    def close_window(self):
        self._connection.disconnect()
        if not hasattr(self, "_root"):
            self._logger.info("Root window does not exist")
            return

        self._root.destroy()
        del self._root

    def send_message(self, message: str):
        self._status.send_message(message=message)

    def modified(self):
        if hasattr(self, "_status"):
            self.set_local_status("Modified")

    @property
    def is_connected(self):
        return self._connection.is_connected

    def set_connection_status(self, status: str):
        self._status.connection_status = status

    def set_local_status(self, status: str):
        self._status.local_status = status

    def broadcast_connection_status(self, value: bool):
        #self._status.broadcast_connection_status(value)
        #self._connection.broadcast_connection_status(value)
        self._registers.broadcast_connection_status(value)

    def read_register(self, memory_address, byte_count = 1):
        return self._connection.read_register(memory_address=memory_address, byte_count=byte_count)

    def write_register(self, memory_address, data):
        self._connection.write_register(memory_address=memory_address, data=data)

def main():
    root = tk.Tk()
    global __platform__
    __platform__ = root.tk.call('tk', 'windowingsystem')

    import os
    global __base_path__
    __base_path__ = os.path.realpath(os.path.dirname(__file__))

    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s:%(message)s')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')
    logger = logging.getLogger("GUI_Logger")

    GUI = ETROC_I2C_GUI(root, logger)

    root.update()
    root.minsize(root.winfo_width(), root.winfo_height())

    root.mainloop()

if __name__ == "__main__":
    main()