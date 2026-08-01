"""
    Machine Template
    Basic CPU with full 16-bit bus addressing (via SYS LD16/ST16 extensions)
"""

import ctypes
from typing import List, Optional, Tuple, Dict, Any
from enum import IntEnum
from dataclasses import dataclass, field
from binding import Machine


class ALUOp(IntEnum):
    """16 ALU operations matching C's encoding"""
    ADD = 0x0
    SUB = 0x1
    AND = 0x2
    OR = 0x3
    XOR = 0x4
    NAND = 0x5
    NOR = 0x6
    NOT_A = 0x7
    PASS_A = 0x8
    PASS_B = 0x9
    SHL = 0xA
    SHR = 0xB
    ROL = 0xC
    ROR = 0xD
    CMP = 0xE
    SYS = 0xF


class SysExt(IntEnum):
    """SYS instruction subtypes (extended operations)"""
    HALT = 0x0      # Halt execution
    LD16 = 0x1      # Load from 16-bit address
    ST16 = 0x2      # Store to 16-bit address
    LDI16 = 0x3     # Load 16-bit immediate
    JMP16 = 0x4     # Jump to 16-bit address
    CALL16 = 0x5    # Call subroutine at 16-bit address
    RET = 0x6       # Return from subroutine
    PUSH = 0x7      # Push to stack
    POP = 0x8       # Pop from stack


class Mode(IntEnum):
    """ALU execution modes"""
    NORMAL = 0
    SATURATE = 1
    SIGNED = 2
    ROUND = 3
    POLARITY_INVERT = 4


@dataclass
class Instruction:
    """Decoded instruction representation"""
    opcode: int
    dest: int
    src1: int
    src2: int
    address: Optional[int] = None      # For LD16/ST16
    immediate: Optional[int] = None    # For LDI16
    subtype: Optional[int] = None      # For SYS operations
    is_extended: bool = False
    words: int = 1                     # Number of 16-bit words

    def __repr__(self) -> str:
        if self.is_extended:
            if self.address is not None:
                return f"<SYS.{SysExt(self.subtype).name} addr=0x{self.address:04X}, dest={self.dest}>"
            if self.immediate is not None:
                return f"<SYS.{SysExt(self.subtype).name} dest={self.dest} imm=0x{self.immediate:04X}>"
            return f"<SYS.{SysExt(self.subtype).name}>"
        return f"<{ALUOp(self.opcode).name} dest={self.dest} src1={self.src1} src2={self.src2}>"


@dataclass
class CPUState:
    """Snapshot of CPU state"""
    pc: int
    cycles: int
    halted: bool
    registers: List[int]
    flags: Tuple[bool, bool, bool]
    mode: int
    stack_pointer: int

    def __repr__(self) -> str:
        return f"SP=0x{self.stack_pointer:04X}, halted={self.halted}, cycles={self.cycles}, flags=Z:{self.flags[0]} C:{self.flags[1]} O:{self.flags[2]}"


class CPU:
    """
    Core Model:
    - Python is the CPU (decoder, PC, control), CPU.step()/CPU.run() are canonical.
    - C is the datapath (ALU, memory, registers), called via direct field/function access.
    - machine_step()/machine_run() on the underlying Machine (C) are LEGACY/UNSAFE for
      any program containing SYS-prefixed (extended) instructions.
    """

    MEMORY_SIZE = 65536
    NUM_REGISTERS = 8
    PROGRAM_START = 0x0200
    STACK_BASE = 0xFF00

    def __init__(self, lib_path: Optional[str] = None):
        self._machine = Machine(lib_path)
        self._stack_pointer = self.STACK_BASE
        self._reset_state()

        # Reference aliases
        self.ADD = ALUOp.ADD
        self.SUB = ALUOp.SUB
        self.AND = ALUOp.AND
        self.OR = ALUOp.OR
        self.XOR = ALUOp.XOR
        self.SHL = ALUOp.SHL
        self.SHR = ALUOp.SHR
        self.SYS = ALUOp.SYS

    def _reset_state(self) -> None:
        self._stack_pointer = self.STACK_BASE
        self._branch_taken = False
        self._call_stack: List[int] = []
        self._instruction_history: List[Instruction] = []

    def reset(self) -> None:
        self._machine.reset()
        self._reset_state()

    def load_program(self, program: List[int], start: int = PROGRAM_START) -> bool:
        if start + len(program) > self.MEMORY_SIZE:
            raise ValueError("Program exceeds memory bounds")
        for i, word in enumerate(program):
            if not self._machine.write_mem(start + i, word):
                return False
        return True

    def step(self) -> bool:
        if self.halted:
            return False

        instruction_word = self._machine.read_mem(self.pc)
        decoded = self._decode(instruction_word)

        if decoded.is_extended:
            self._execute_extended(decoded)
        else:
            self._execute_alu(decoded)

        if not self._branch_taken:
            self.pc += decoded.words
        self._branch_taken = False

        # Cycle count; 1-word or 2-word instructions
        self._machine.state.cycle_count += decoded.words

        return True

    def run(self, max_cycles: int = 1000) -> int:
        start = self.cycles
        while (self.cycles - start) < max_cycles and not self.halted:
            if not self.step():
                break
        return self.cycles - start

    def halt(self) -> None:
        self._machine.halt()

    def _decode(self, word: int) -> Instruction:
        opcode = (word >> 12) & 0x0F
        dest = (word >> 8) & 0x0F
        src1 = (word >> 4) & 0x0F
        src2 = word & 0x0F

        if opcode == ALUOp.SYS:
            subtype = dest
            extended = self._decode_extended(subtype, src1, src2)
            extended.opcode = opcode
            extended.is_extended = True
            return extended

        return Instruction(opcode=opcode, dest=dest, src1=src1, src2=src2, is_extended=False, words=1)

    def _decode_extended(self, subtype: int, src1: int, src2: int) -> Instruction:
        instr = Instruction(opcode=ALUOp.SYS, dest=0, src1=src1, src2=src2, subtype=subtype, is_extended=True, words=2)

        # wrap PC + 1 to prevent out-of-bounds read at 0xFFFF
        second_word = self._machine.read_mem((self.pc + 1) & 0xFFFF)

        if subtype == SysExt.LD16:
            instr.dest = src1
            instr.address = second_word
        elif subtype == SysExt.ST16:
            instr.address = second_word
            instr.src1 = src1
        elif subtype == SysExt.LDI16:
            instr.dest = src1
            instr.immediate = second_word
        elif subtype in (SysExt.JMP16, SysExt.CALL16):
            instr.address = second_word
            instr.words = 2
        elif subtype in (SysExt.RET, SysExt.PUSH, SysExt.POP, SysExt.HALT):
            instr.src1 = src1 if subtype in (SysExt.PUSH, SysExt.POP) else 0
            instr.words = 1
        else:
            instr.words = 1

        return instr

    def _execute_alu(self, instr: Instruction) -> None:
        self._machine.lib.machine_alu_op(
            ctypes.byref(self._machine.state),
            instr.src1, instr.src2, instr.dest, instr.opcode
        )
        self._instruction_history.append(instr)

    def _execute_extended(self, instr: Instruction) -> None:
        subtype = SysExt(instr.subtype)

        if subtype == SysExt.HALT:
            self.halt()
        elif subtype == SysExt.LD16:
            value = self._machine.read_mem(instr.address)
            self._machine.set_register(instr.dest, value)
        elif subtype == SysExt.ST16:
            value = self._machine.get_register(instr.src1)
            self._machine.write_mem(instr.address, value)
        elif subtype == SysExt.LDI16:
            self._machine.set_register(instr.dest, instr.immediate)
        elif subtype == SysExt.JMP16:
            self.pc = instr.address
            self._branch_taken = True
        elif subtype == SysExt.CALL16:
            self._call_stack.append((self.pc + 2) & 0xFFFF)
            self.pc = instr.address
            self._branch_taken = True
        elif subtype == SysExt.RET:
            if not self._call_stack:
                raise RuntimeError("RET executed on empty call stack")
            self.pc = self._call_stack.pop()
            self._branch_taken = True
        elif subtype == SysExt.PUSH:
            value = self._machine.get_register(instr.src1)
            self._stack_pointer = (self._stack_pointer - 1) & 0xFFFF
            self._machine.write_mem(self._stack_pointer, value)
        elif subtype == SysExt.POP:
            value = self._machine.read_mem(self._stack_pointer)
            self._machine.set_register(instr.src1, value)
            self._stack_pointer = (self._stack_pointer + 1) & 0xFFFF

        self._instruction_history.append(instr)

    def __getitem__(self, addr: int) -> int:
        if not (0 <= addr < self.MEMORY_SIZE):
            raise IndexError(f"Address {addr} out of range")
        return self._machine.read_mem(addr)

    def __setitem__(self, addr: int, value: int) -> None:
        if not (0 <= addr < self.MEMORY_SIZE):
            raise IndexError(f"Address {addr} out of range")
        if not (0 <= value <= 0xFFFF):
            raise ValueError(f"Value {value} out of 16-bit range")
        self._machine.write_mem(addr, value)

    def get_reg(self, reg: int) -> int:
        return self._machine.get_register(reg)

    def set_reg(self, reg: int, value: int) -> None:
        self._machine.set_register(reg, value)

    @property
    def registers(self) -> List[int]:
        return [self.get_reg(i) for i in range(self.NUM_REGISTERS)]

    @property
    def pc(self) -> int:
        return self._machine.state.pc

    @pc.setter
    def pc(self, value: int) -> None:
        self._machine.state.pc = value & 0xFFFF

    @property
    def flags(self) -> Tuple[bool, bool, bool]:
        z, c, o = self._machine.flgs
        return (bool(z), bool(c), bool(o))

    @property
    def zero(self) -> bool: return bool(self._machine.flgs[0])
    @property
    def carry(self) -> bool: return bool(self._machine.flgs[1])
    @property
    def overflow(self) -> bool: return bool(self._machine.flgs[2])

    def set_mode(self, mode: Mode) -> None:
        self._machine.set_mode(int(mode))

    def get_mode(self) -> Mode:
        return Mode(self._machine.get_mode())

    @property
    def halted(self) -> bool:
        return bool(self._machine.state.halted)

    @property
    def cycles(self) -> int:
        return self._machine.state.cycle_count

    @property
    def stack_pointer(self) -> int:
        return self._stack_pointer

    @stack_pointer.setter
    def stack_pointer(self, value: int) -> None:
        self._stack_pointer = value & 0xFFFF

    def assemble(self, op: str, *args) -> List[int]:
        op = op.upper()
        if op in ALUOp.__members__:
            opcode = ALUOp[op]
            if len(args) == 3:
                dest, src1, src2 = args
                return [(opcode << 12) | (dest << 8) | (src1 << 4) | src2]
        elif op in SysExt.__members__:
            subtype = SysExt[op]
            if op == "LD16" and len(args) == 2:
                dest, addr = args
                return [(ALUOp.SYS << 12) | (subtype << 8) | (dest << 4), addr & 0xFFFF]
            elif op == "ST16" and len(args) == 2:
                addr, src = args
                return [(ALUOp.SYS << 12) | (subtype << 8) | (src << 4), addr & 0xFFFF]
            elif op == "LDI16" and len(args) == 2:
                dest, imm = args
                return [(ALUOp.SYS << 12) | (subtype << 8) | (dest << 4), imm & 0xFFFF]
            elif op in ("JMP16", "CALL16") and len(args) == 1:
                addr = args[0]
                return [(ALUOp.SYS << 12) | (subtype << 8), addr & 0xFFFF]
            elif op == "HALT" and len(args) == 0:
                return [(ALUOp.SYS << 12) | (subtype << 8)]
            elif op in ("PUSH", "POP") and len(args) == 1:
                src = args[0]
                return [(ALUOp.SYS << 12) | (subtype << 8) | (src << 4)]
            elif op == "RET" and len(args) == 0:
                return [(ALUOp.SYS << 12) | (subtype << 8)]
        raise ValueError(f"Unknown instruction: {op} {args}")

    def assemble_program(self, instructions: List[tuple]) -> List[int]:
        program = []
        for instr in instructions:
            program.extend(self.assemble(*instr))
        return program

    def dump(self, start: int = 0, end: int = 0x20) -> None:
        self._machine.dump(start, end)
        print(f"\nCPU State:")
        print(f"  PC: 0x{self.pc:04X}")
        print(f"  SP: 0x{self.stack_pointer:04X}")
        print(f"  Cycles: {self.cycles}")
        print(f"  Halted: {self.halted}")
        print(f"  Mode: {self.get_mode().name}")
        print(f"  Flags: Z={self.zero} C={self.carry} O={self.overflow}")
        print(f"  Registers: {self.registers}")

    def get_state(self) -> CPUState:
        return CPUState(
            pc=self.pc, cycles=self.cycles, halted=self.halted,
            registers=self.registers, flags=self.flags,
            mode=int(self.get_mode()), stack_pointer=self.stack_pointer
        )

    def get_history(self) -> List[Instruction]:
        return self._instruction_history.copy()

    def clear_history(self) -> None:
        self._instruction_history.clear()

    def __repr__(self) -> str:
        return f"CPU(pc=0x{self.pc:04X}, sp=0x{self.stack_pointer:04X}, cycles={self.cycles}, halted={self.halted})"
