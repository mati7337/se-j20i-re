# Different configurations for emulated phones
from abc import ABC, abstractmethod
import EMPProto
import os

# Emulates the erom variable memory
class EromVariableStore():
    variables = {}

    def get(self, unita, unitb):
        # Phone seems to ignore unita
        return self.variables.get(unitb, b"")

    def load_from_dir(self, dir_name):
        # Load variables dumped by client.py
        # The variables filenames are in a "var_UNITB.bin" format, where UNITB is in hex
        if not os.path.isdir(dir_name):
            raise ValueError(f"{dir_name} is not a directory!")

        for var_filename in os.listdir(dir_name):
            if not var_filename.startswith("var_") or not var_filename.endswith(".bin"):
                raise ValueError(f"Invalid variable filename {var_filename}")

            unitb = int(var_filename[len("var_"):-len(".bin")], 16)

            with open(f"{dir_name}/{var_filename}", "rb") as fl:
                self.variables[unitb] = fl.read()

class SonyEricssonConfig(ABC):
    @property
    @abstractmethod
    def erom_color(self): pass

    @property
    @abstractmethod
    def chip_id(self): pass

    @property
    @abstractmethod
    def erom(self): pass

    @property
    @abstractmethod
    def semcboot_ver(self): pass

    @property
    @abstractmethod
    def cid_otp(self): pass

    @property
    def cid_erom(self):
        return self.cid_otp

    @property
    @abstractmethod
    def hello_message(self): pass

    @property
    @abstractmethod
    def imei(self): pass

class SonyEricssonJ20iRed(SonyEricssonConfig):
    erom_color = EMPProto.EROM_COLOR_RED
    chip_id = EMPProto.CHIP_NAMES["DB3350"]
    erom = EromVariableStore()
    semcboot_ver = b'1200-4341 SEMCBOOT R6A033'
    cid_otp = 0x51
    hello_message = EMPProto.HELLO_RESP
    imei = b"0"*14

    def __init__(self):
        self.erom.load_from_dir("./j20i_erom_vars")

class SonyEricssonTest(SonyEricssonJ20iRed):
    erom_color = EMPProto.EROM_COLOR_RED
    chip_id = EMPProto.CHIP_NAMES["DB3210"]
    cid_otp = 49
