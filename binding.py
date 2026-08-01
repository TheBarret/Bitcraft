import ctypes
import os
from pathlib import Path
from typing import List, Optional, Tuple

class Bit(ctypes.Structure):
    _fields_ = [("v", ctypes.c_ubyte)]

class AluFlags(ctypes.Structure):
    _fields_ = [
        ("zero", Bit),
        ("carry", Bit),
        ("overflow", Bit),
    ]

MEMORY_SIZE = 65536
NUM_REGISTERS = 8

class Bus(ctypes.Structure):
    _fields_ = [
        ("memory", ctypes.c_uint16 * MEMORY_SIZE),
        ("addr_a", ctypes.c_uint16),
        ("addr_b", ctypes.c_uint16),
        ("addr_dest", ctypes.c_uint16),
        ("flags", AluFlags),
    ]

class _MachineState(ctypes.Structure):
    _fields_ = [
        ("bus", Bus),
        ("pc", ctypes.c_uint16),
        ("cycle_count", ctypes.c_uint64),
        ("halted", ctypes.c_ubyte),
        ("alu_wires", Bit * 64),
        ("bus_lines", Bit * 16),
        ("mode", ctypes.c_ubyte),
        ("saturation_enabled", ctypes.c_ubyte),
        ("signed_mode", ctypes.c_ubyte),
    ]

class Machine:
    def __init__(self, lib_path: Optional[str] = None):
        if lib_path is None:
            lib_path = str(Path(__file__).parent / "build" / "bc.so")
        if not os.path.exists(lib_path):
            raise FileNotFoundError(f"Could not find library at {lib_path}.")

        self.lib = ctypes.CDLL(lib_path)
        self._setup_signatures()
        self.state = _MachineState()
        self.init()

    def _setup_signatures(self):
        self.lib.machine_init.argtypes = [ctypes.POINTER(_MachineState)]
        self.lib.machine_init.restype = None
        self.lib.machine_reset.argtypes = [ctypes.POINTER(_MachineState)]
        self.lib.machine_reset.restype = None
        self.lib.machine_load_program.argtypes = [ctypes.POINTER(_MachineState), ctypes.POINTER(ctypes.c_uint16), ctypes.c_size_t]
        self.lib.machine_load_program.restype = ctypes.c_int
        self.lib.machine_step.argtypes = [ctypes.POINTER(_MachineState)]
        self.lib.machine_step.restype = ctypes.c_int
        self.lib.machine_run.argtypes = [ctypes.POINTER(_MachineState), ctypes.c_uint64]
        self.lib.machine_run.restype = ctypes.c_uint64
        self.lib.machine_halt.argtypes = [ctypes.POINTER(_MachineState)]
        self.lib.machine_halt.restype = None
        self.lib.machine_alu_op.argtypes = [ctypes.POINTER(_MachineState), ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_int]
        self.lib.machine_alu_op.restype = ctypes.c_int
        self.lib.machine_write.argtypes = [ctypes.POINTER(_MachineState), ctypes.c_uint16, ctypes.c_uint16]
        self.lib.machine_write.restype = ctypes.c_int
        self.lib.machine_read.argtypes = [ctypes.POINTER(_MachineState), ctypes.c_uint16]
        self.lib.machine_read.restype = ctypes.c_uint16
        self.lib.machine_get_register.argtypes = [ctypes.POINTER(_MachineState), ctypes.c_ubyte]
        self.lib.machine_get_register.restype = ctypes.c_uint16
        self.lib.machine_set_register.argtypes = [ctypes.POINTER(_MachineState), ctypes.c_ubyte, ctypes.c_uint16]
        self.lib.machine_set_register.restype = ctypes.c_int
        self.lib.machine_get_zero_flag.argtypes = [ctypes.POINTER(_MachineState)]
        self.lib.machine_get_zero_flag.restype = ctypes.c_ubyte
        self.lib.machine_get_carry_flag.argtypes = [ctypes.POINTER(_MachineState)]
        self.lib.machine_get_carry_flag.restype = ctypes.c_ubyte
        self.lib.machine_get_overflow_flag.argtypes = [ctypes.POINTER(_MachineState)]
        self.lib.machine_get_overflow_flag.restype = ctypes.c_ubyte
        self.lib.machine_get_wire.argtypes = [ctypes.POINTER(_MachineState), ctypes.c_ubyte]
        self.lib.machine_get_wire.restype = ctypes.c_ubyte
        self.lib.machine_set_mode.argtypes = [ctypes.POINTER(_MachineState), ctypes.c_int]
        self.lib.machine_set_mode.restype = None
        self.lib.machine_get_mode.argtypes = [ctypes.POINTER(_MachineState)]
        self.lib.machine_get_mode.restype = ctypes.c_int
        self.lib.machine_dump.argtypes = [ctypes.POINTER(_MachineState), ctypes.c_uint16, ctypes.c_uint16]
        self.lib.machine_dump.restype = None

    def init(self):
        self.lib.machine_init(ctypes.byref(self.state))

    def reset(self):
        self.lib.machine_reset(ctypes.byref(self.state))

    def load_program(self, program: List[int]) -> int:
        # SAFETY FIX: Keep a reference to prevent premature garbage collection
        self._program_buffer = (ctypes.c_uint16 * len(program))(*program)
        return self.lib.machine_load_program(ctypes.byref(self.state), self._program_buffer, len(program))

    def step(self) -> int:
        return self.lib.machine_step(ctypes.byref(self.state))

    def run(self, max_cycles: int = 1000) -> int:
        return self.lib.machine_run(ctypes.byref(self.state), max_cycles)

    def halt(self):
        self.lib.machine_halt(ctypes.byref(self.state))

    def write_mem(self, addr: int, val: int) -> int:
        return self.lib.machine_write(ctypes.byref(self.state), addr, val)

    def read_mem(self, addr: int) -> int:
        return self.lib.machine_read(ctypes.byref(self.state), addr)

    def get_register(self, reg: int) -> int:
        return self.lib.machine_get_register(ctypes.byref(self.state), reg)

    def set_register(self, reg: int, val: int) -> int:
        return self.lib.machine_set_register(ctypes.byref(self.state), reg, val)

    @property
    def flgs(self) -> Tuple[int, int, int]:
        z = self.lib.machine_get_zero_flag(ctypes.byref(self.state))
        c = self.lib.machine_get_carry_flag(ctypes.byref(self.state))
        o = self.lib.machine_get_overflow_flag(ctypes.byref(self.state))
        return (z, c, o)

    def get_wire(self, index: int) -> int:
        return self.lib.machine_get_wire(ctypes.byref(self.state), index)

    def dump(self, start: int = 0, end: int = 16):
        self.lib.machine_dump(ctypes.byref(self.state), start, end)
