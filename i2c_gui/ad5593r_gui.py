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
import tkinter.ttk as ttk
import logging

import i2c_gui

def main():
    root = tk.Tk()
    i2c_gui.__no_connect__ = False
    i2c_gui.set_swap_endian()
    i2c_gui.set_platform(root.tk.call('tk', 'windowingsystem'))

    # Only for development purposes, uncomment to have a preview of the window in windows while running on macOS
    style = ttk.Style(root)
    #style.theme_use('classic')

    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)s:%(message)s')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s:%(name)s:%(message)s')
    logger = logging.getLogger("GUI_Logger")

    GUI = i2c_gui.AD5593R_GUI(root, logger)

    root.update()
    root.minsize(root.winfo_width(), root.winfo_height())

    root.mainloop()

if __name__ == "__main__":
    main()