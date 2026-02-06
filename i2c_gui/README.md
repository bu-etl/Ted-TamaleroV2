# I2C GUI

This tool is a Graphical User Interface to control and interact with a device over an I2C connection.

Individual registers available through the I2C connection can be read and/or written through the GUI.

## Installation

This GUI only requires Python 3 to be installed on your computer as well as a couple of python libraries which are dependencies. The tool is not offered in a Python 2 compatible version.

### Python installation

Follow the instructions for your operating system. This is generally very straightforward, but for completeness sake a streamlined set of instructions is shown below. Keep in mind that these instructions may become outdated as the installation methods may change over time.

#### macOS

macOS already comes with a python version installed. However, this version is often outdated with respect to the newest Python available.
Consequently, it is desirable to run a more up to date version of Python, thus requiring installation.
It is recommended to use [homebrew](https://brew.sh/) to install python, follow the instruction on the homebrew webpage to install homebrew.
Then, from the command line, run the following command to install python: `brew install python`

#### Windows

Download the latest python installer from the python [homepage](https://www.python.org/).
Then proceed to run the installer in order to install python.
Remember to enable the option to add python to the PATH and consider enabling the option to allow filenames longer than 256 characters.

#### Linux

Most linux distributions come with a version of python already installed.
Just like with macOS, this pre-installed version can be outdated.
As a result, it is recommended to update the python version if possible.

Instructions vary depending on the linux distribution, but you will typically want to use the package manager of the distribution you have to search for the latest python and then install it.
Two common package managers are `yum` and `apt`, the corresponding commands would be:
```
yum search python
yum install [python package]
apt search python
apt install [python package]
```

### Dependency Installation

This tool depends on the usb-iss python library to provide communication with the I2C bus over a USB connection with the associated hardware adaptor. The pillow library is also used in order to open and display images.

To install libraries in python, it is traditional to use the PIP tool, which by default installs libraries from the Python Package Index ([PyPI](https://pypi.org/)).
This is the recommended method here as well, so just follow the commands below from a command line (independent of the operating system being used):
```
python -m pip install usb-iss
python -m pip install pillow
python -m pip install matplotlib
python -m pip install pandas
```


It may be desirable to install the dependencies and run the GUI inside a `venv` to isolate it from the python packages locally installed on the system and thus avoid library conflicts. You must do this before installing the dependencies above. To get a venv, simply run the command `python -m venv venv` (this will create a venv named venv, the name is the last parameter). Then, to activate the venv before running the GUI, use the following command:
* Windows:
    * CMD: `venv\Scripts\activate.bat`
    * Power Shell: `venv\Scripts\Activate.ps1`
* Linux/macOS:
    * bash/zsh: `source venv/bin/activate`

On windows Power Shell you may also need to run the following command first: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`. See the official venv documentation for any questions: [link](https://docs.python.org/3/library/venv.html)

### After installation

You can now run the GUI tool. There are a couple different versions to choose from, at the moment the etroc2_gui.py and the etroc1_gui.py (placeholder). From the command line simply run `python [gui script you want to run]` in order to run the GUI. On some operating systems it is also possible to double click on the python file from the file explorer instead.

## Development information

Each chip must have a class implemented which supports its unique features, a single chip can have more than one I2C address. Each I2C address has an associated address space. The address space is split into logical blocks. The logical blocks can be unique or they can be a repeating block, in which case the object is called a "block array". If using a block array, an indexer function must be defined in order to index the base address of each individual block in the block array. A register is considered to be an indexable 8-bit value within this address space. It is common for subset of bits of a register, or combinations of bits from separate register to represent a logical value. This feature is also supported and such values are called "decoded values" since they are decoded from the registers.
