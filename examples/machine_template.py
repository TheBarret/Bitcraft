"""
    Machine Template
    Basic CPU with full 16-bit bus addressing (via SYS LD16/ST16 extensions)
"""

import ctypes # for cpu._machine.lib.* functions
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
        sf_value = f"SP=0x{self.stack_pointer:04X}, halted={self.halted}, cycles={self.cycles}, flags=Z:{self.flags[0]} C:{self.flags[1]} O:{self.flags[2]}"
        return sf_value


class CPU:
    """
    Core Model:
    - Python is the CPU (decoder, PC, control), CPU.step()/CPU.run() are canonical.
    - C is the datapath (ALU, memory, registers), called via direct field/function access.
    - machine_step()/machine_run() on the underlying Machine (C) are LEGACY/UNSAFE for
      any program containing SYS-prefixed (extended) instructions:
      the C decoder has no concept of 2-word instructions and will misread the second word as a fresh opcode desyncing PC silently.
      Do not call self._machine.step()/.run() directly once a program contains LD16/ST16/LDI16/JMP16/CALL16/RET/PUSH/POP.
    """

    # Memory constants
    MEMORY_SIZE = 65536
    NUM_REGISTERS = 8
    PROGRAM_START = 0x0200
    STACK_BASE = 0xFF00
    SCRATCH_1 = 0xFFFE
    SCRATCH_2 = 0xFFFF

    def __init__(self, lib_path: Optional[str] = None):
        """Initialize CPU with optional library path"""
        self._machine = Machine(lib_path)
        self._stack_pointer = self.STACK_BASE
        self._reset_state()

        # Convenience aliases
        self.ADD = ALUOp.ADD
        self.SUB = ALUOp.SUB
        self.AND = ALUOp.AND
        self.OR = ALUOp.OR
        self.XOR = ALUOp.XOR
        self.SHL = ALUOp.SHL
        self.SHR = ALUOp.SHR
        self.SYS = ALUOp.SYS

    def _reset_state(self) -> None:
        """Reset internal Python-side state"""
        self._stack_pointer = self.STACK_BASE
        self._branch_taken = False
        self._call_stack: List[int] = []
        self._instruction_history: List[Instruction] = []

    # Core Operations

    def reset(self) -> None:
        """Reset entire machine"""
        self._machine.reset()
        self._reset_state()

    def load_program(self, program: List[int], start: int = PROGRAM_START) -> bool:
        """Load program at specified address (default 0x0200)"""
        for i, word in enumerate(program):
            if not self._machine.write_mem(start + i, word):
                return False
        return True

    def step(self) -> bool:
        """
        Execute one instruction cycle.
        Decoder is entirely in Python - this is the heart of the CPU.
        """
        if self.halted:
            return False

        # Fetch instruction
        instruction_word = self._machine.read_mem(self.pc)
        decoded = self._decode(instruction_word)

        # Execute based on opcode
        if decoded.is_extended:
            self._execute_extended(decoded)
        else:
            self._execute_alu(decoded)

        # Update PC based on branch status
        if not self._branch_taken:
            self.pc += decoded.words
        self._branch_taken = False
        # added 0.2: python also adds cycles
        self._machine.state.cycle_count += 1

        return True

    def run(self, max_cycles: int = 1000) -> int:
        """Run for specified cycles or until halted"""
        start = self.cycles
        while (self.cycles - start) < max_cycles and not self.halted:
            if not self.step():
                break
        return self.cycles - start

    def halt(self) -> None:
        """Halt CPU execution"""
        self._machine.halt()

    # Decoder

    def _decode(self, word: int) -> Instruction:
        """Decode a 16-bit instruction word"""
        opcode = (word >> 12) & 0x0F
        dest = (word >> 8) & 0x0F
        src1 = (word >> 4) & 0x0F
        src2 = word & 0x0F

        # Check for SYS prefix (extended instruction)
        if opcode == ALUOp.SYS:
            subtype = dest  # Lower 4 bits of SYS word
            extended = self._decode_extended(subtype, src1, src2)
            extended.opcode = opcode
            extended.is_extended = True
            return extended

        return Instruction(
            opcode=opcode,
            dest=dest,
            src1=src1,
            src2=src2,
            is_extended=False,
            words=1
        )

    def _decode_extended(self, subtype: int, src1: int, src2: int) -> Instruction:
        """Decode SYS extended instruction"""
        instr = Instruction(
            opcode=ALUOp.SYS,
            dest=0,
            src1=src1,
            src2=src2,
            subtype=subtype,
            is_extended=True,
            words=2
        )

        # Fetch the second word (address/immediate)
        second_word = self._machine.read_mem(self.pc + 1)

        if subtype == SysExt.LD16:
            instr.dest = src1
            instr.address = second_word
        elif subtype == SysExt.ST16:
            instr.address = second_word
            instr.src1 = src1  # Source register
        elif subtype == SysExt.LDI16:
            instr.dest = src1
            instr.immediate = second_word
        elif subtype == SysExt.JMP16:
            instr.address = second_word
            instr.words = 2
        elif subtype == SysExt.CALL16:
            instr.address = second_word
            instr.words = 2
        elif subtype == SysExt.RET:
            instr.words = 1  # RET is only 1 word
        elif subtype == SysExt.PUSH:
            instr.src1 = src1
            instr.words = 1
        elif subtype == SysExt.POP:
            instr.src1 = src1
            instr.words = 1
        elif subtype == SysExt.HALT:
            instr.words = 1  # HALT is only 1 word
        else:
            instr.words = 1  # Unknown subtype, treat as 1 word

        return instr

    # Execute ALU Operations

    def _execute_alu(self, instr: Instruction) -> None:
        """Execute standard ALU operation"""
        opcode = ALUOp(instr.opcode)

        # Special case: SYS without extended decoding
        if opcode == ALUOp.SYS:
            self._execute_sys(instr)
            return

        # Execute ALU operation via the C library
        # The binding's Machine class exposes the C function through its lib
        self._machine.lib.machine_alu_op(
            ctypes.byref(self._machine.state),
            instr.src1,
            instr.src2,
            instr.dest,
            instr.opcode
        )

        # Track instruction
        self._instruction_history.append(instr)

    def _execute_sys(self, instr: Instruction) -> None:
        """Execute SYS instruction (handled by Python)"""
        # SYS without subtype is a no-op
        # Actual SYS operations are handled via extended decode
        pass

    # Execute Extended Operations

    def _execute_extended(self, instr: Instruction) -> None:
        """Execute extended (SYS) instruction"""
        subtype = SysExt(instr.subtype)

        if subtype == SysExt.HALT:
            self.halt()

        elif subtype == SysExt.LD16:
            # Load from 16-bit address
            value = self._machine.read_mem(instr.address)
            self._machine.set_register(instr.dest, value)

        elif subtype == SysExt.ST16:
            # Store to 16-bit address
            value = self._machine.get_register(instr.src1)
            self._machine.write_mem(instr.address, value)

        elif subtype == SysExt.LDI16:
            # Load 16-bit immediate
            self._machine.set_register(instr.dest, instr.immediate)

        elif subtype == SysExt.JMP16:
            # Jump to 16-bit address
            self.pc = instr.address
            self._branch_taken = True

        elif subtype == SysExt.CALL16:
            # Call subroutine
            self._call_stack.append(self.pc + 2)  # Return address after CALL
            self.pc = instr.address
            self._branch_taken = True

        elif subtype == SysExt.RET:
            # Return from subroutine
            if self._call_stack:
                self.pc = self._call_stack.pop()
                self._branch_taken = True

        elif subtype == SysExt.PUSH:
            # Push register to stack
            value = self._machine.get_register(instr.src1)
            self._stack_pointer -= 1
            self._machine.write_mem(self._stack_pointer, value)

        elif subtype == SysExt.POP:
            # Pop from stack to register
            value = self._machine.read_mem(self._stack_pointer)
            self._machine.set_register(instr.src1, value)
            self._stack_pointer += 1

        self._instruction_history.append(instr)

    # Memory Access (Pythonic)

    def __getitem__(self, addr: int) -> int:
        """Pythonic memory access: cpu[addr]"""
        if not (0 <= addr < self.MEMORY_SIZE):
            raise IndexError(f"Address {addr} out of range")
        return self._machine.read_mem(addr)

    def __setitem__(self, addr: int, value: int) -> None:
        """Pythonic memory access: cpu[addr] = value"""
        if not (0 <= addr < self.MEMORY_SIZE):
            raise IndexError(f"Address {addr} out of range")
        if not (0 <= value <= 0xFFFF):
            raise ValueError(f"Value {value} out of 16-bit range")
        self._machine.write_mem(addr, value)

    # Register Access

    def get_reg(self, reg: int) -> int:
        """Get register value"""
        return self._machine.get_register(reg)

    def set_reg(self, reg: int, value: int) -> None:
        """Set register value"""
        self._machine.set_register(reg, value)

    @property
    def registers(self) -> List[int]:
        """Get all registers as list"""
        return [self.get_reg(i) for i in range(self.NUM_REGISTERS)]

    # Program Counter

    @property
    def pc(self) -> int:
        """Get program counter"""
        return self._machine.state.pc

    @pc.setter
    def pc(self, value: int) -> None:
        """Set program counter"""
        self._machine.state.pc = value & 0xFFFF

    # Flags

    @property
    def flags(self) -> Tuple[bool, bool, bool]:
        """Get (zero, carry, overflow) flags"""
        z, c, o = self._machine.flgs
        return (bool(z), bool(c), bool(o))

    @property
    def zero(self) -> bool:
        return bool(self._machine.flgs[0])

    @property
    def carry(self) -> bool:
        return bool(self._machine.flgs[1])

    @property
    def overflow(self) -> bool:
        return bool(self._machine.flgs[2])

    # Mode Management

    def set_mode(self, mode: Mode) -> None:
        """Set ALU execution mode"""
        self._machine.set_mode(int(mode))

    def get_mode(self) -> Mode:
        """Get current ALU mode"""
        return Mode(self._machine.get_mode())

    # State

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

    # Assembly Helpers

    def assemble(self, op: str, *args) -> List[int]:
        """
        Assemble a single instruction (for program generation)

        Examples:
            cpu.assemble("ADD", 3, 1, 2)  -> 0x0312
            cpu.assemble("LD16", 3, 0x1234) -> [0xF001, 0x1234]
        """
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
            elif op == "JMP16" and len(args) == 1:
                addr = args[0]
                return [(ALUOp.SYS << 12) | (subtype << 8), addr & 0xFFFF]
            elif op == "CALL16" and len(args) == 1:
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
        """Assemble a list of instructions into a program"""
        program = []
        for instr in instructions:
            program.extend(self.assemble(*instr))
        return program

    # Debug

    def dump(self, start: int = 0, end: int = 0x20) -> None:
        """Dump memory and CPU state"""
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
        """Get full CPU state snapshot"""
        return CPUState(
            pc=self.pc,
            cycles=self.cycles,
            halted=self.halted,
            registers=self.registers,
            flags=self.flags,
            mode=int(self.get_mode()),
            stack_pointer=self.stack_pointer
        )

    def get_history(self) -> List[Instruction]:
        """Get instruction execution history"""
        return self._instruction_history.copy()

    def clear_history(self) -> None:
        """Clear instruction history"""
        self._instruction_history.clear()

    def __repr__(self) -> str:
        return (f"CPU(pc=0x{self.pc:04X}, sp=0x{self.stack_pointer:04X}, "
                f"cycles={self.cycles}, halted={self.halted})")
