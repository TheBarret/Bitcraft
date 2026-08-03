"""
Machine Template
Basic CPU with full 16-bit bus addressing

changelog 0.1: initial release
changelog 0.2: added extended operations (HALT, LD16, ST16, LDI16, JMP16, CALL16, RET, PUSH, POP)
changelog 0.3: added indirect addressing (STIND, LDIND) and conditional jumps (JZ, JNZ, JC)
changelog 0.4: added stdio ports, input=0xFFFD, output=0xFFFE, caught before memory __setitem__, __getitem__
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
    STIND = 0x9     # Store R[src1] to memory at address in R[dest] (store-indirect)
    LDIND = 0xA     # Load into R[dest] from memory at address in R[src1] (load-indirect)
    JZ    = 0xB     # Jump to 16-bit address if zero flag is set
    JNZ   = 0xC     # Jump to 16-bit address if zero flag is not set
    JC    = 0xD     # Jump to 16-bit address if carry flag is set


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
        # Reference aliases for convenience
        self.ADD = ALUOp.ADD
        self.SUB = ALUOp.SUB
        self.AND = ALUOp.AND
        self.OR = ALUOp.OR
        self.XOR = ALUOp.XOR
        self.SHL = ALUOp.SHL
        self.SHR = ALUOp.SHR
        self.SYS = ALUOp.SYS

    def _reset_state(self) -> None:
        """Reset Python-side state (stack, branch tracking, history)"""
        self._stack_pointer = self.STACK_BASE
        self._branch_taken = False
        self._call_stack: List[int] = []
        self._instruction_history: List[Instruction] = []

    def reset(self) -> None:
        """Full system reset - C state + Python state"""
        self._machine.reset()
        self._reset_state()

    def load_program(self, program: List[int], start: int = PROGRAM_START) -> bool:
        """Load a program into memory at the specified start address"""
        if start + len(program) > self.MEMORY_SIZE:
            raise ValueError("Program exceeds memory bounds")
        for i, word in enumerate(program):
            if not self._machine.write_mem(start + i, word):
                return False
        return True

    def step(self) -> bool:
        """
        Execute one instruction.
        Returns False if halted, True otherwise.
        Handles both 1-word ALU ops and 2-word SYS extended ops.
        """
        if self.halted:
            return False

        instruction_word = self._machine.read_mem(self.pc)
        decoded = self._decode(instruction_word)

        if decoded.is_extended:
            self._execute_extended(decoded)
        else:
            self._execute_alu(decoded)

        # Branch instructions set _branch_taken to avoid PC increment
        if not self._branch_taken:
            self.pc += decoded.words
        self._branch_taken = False

        # Cycle count; 1-word or 2-word instructions
        # Todo: Check cycle counting, for inaccuracy
        self._machine.state.cycle_count += decoded.words

        return True

    def run(self, max_cycles: int = 1000) -> int:
        """Run up to max_cycles instructions. Returns number executed."""
        start = self.cycles
        while (self.cycles - start) < max_cycles and not self.halted:
            if not self.step():
                break
        return self.cycles - start

    def halt(self) -> None:
        """Stop execution"""
        self._machine.halt()

    def _decode(self, word: int) -> Instruction:
        """
        Decode a 16-bit instruction word.
        ALU ops: bits 15-12=op, 11-8=dest, 7-4=src1, 3-0=src2
        SYS ops: bits 15-12=0xF, 11-8=subtype, 7-4=src1, 3-0=src2
        """
        opcode = (word >> 12) & 0x0F
        dest = (word >> 8) & 0x0F
        src1 = (word >> 4) & 0x0F
        src2 = word & 0x0F

        # Todo: Validate opcode and subtype ranges, raise InvalidInstructionError for invalid values
        if opcode == ALUOp.SYS:
            subtype = dest
            extended = self._decode_extended(subtype, src1, src2)
            extended.opcode = opcode
            extended.is_extended = True
            return extended

        return Instruction(opcode=opcode, dest=dest, src1=src1, src2=src2, is_extended=False, words=1)

    def _decode_extended(self, subtype: int, src1: int, src2: int) -> Instruction:
        """
        Decode SYS extended instructions.
        Many SYS ops require a second 16-bit word (address or immediate).
        """
        instr = Instruction(opcode=ALUOp.SYS, dest=0, src1=src1, src2=src2,
                            subtype=subtype, is_extended=True, words=2)

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
        elif subtype in (SysExt.JMP16, SysExt.CALL16,
                         SysExt.JZ, SysExt.JNZ, SysExt.JC):
            instr.address = second_word
        elif subtype in (SysExt.STIND, SysExt.LDIND):
            # Indirect ops are 1 word: first nybble=src1, second=src2
            instr.words = 1
            if subtype == SysExt.STIND:
                instr.src1 = src1   # value register
                instr.dest = src2   # address register
            else:  # LDIND
                instr.dest = src1   # destination register
                instr.src1 = src2   # address register
        elif subtype in (SysExt.RET, SysExt.PUSH, SysExt.POP, SysExt.HALT):
            instr.src1 = src1 if subtype in (SysExt.PUSH, SysExt.POP) else 0
            instr.words = 1
        else:
            instr.words = 1

        return instr

    def _execute_alu(self, instr: Instruction) -> None:
        """Execute a standard ALU operation - simple, fast, direct C call"""
        self._machine.lib.machine_alu_op(
            ctypes.byref(self._machine.state),
            instr.src1, instr.src2, instr.dest, instr.opcode
        )
        self._instruction_history.append(instr)

    def _execute_extended(self, instr: Instruction) -> None:
        """
        Execute SYS extended instructions.
        This is the complex part - handles memory ops, branches, stack, and control flow.
        Each subtype has different operand requirements and side effects.
        """
        subtype = SysExt(instr.subtype)
        if subtype == SysExt.HALT:
            self.halt()
        elif subtype == SysExt.LD16:
            # Load from absolute 16-bit address into register
            value = self._machine.read_mem(instr.address)
            self._machine.set_register(instr.dest, value)
        elif subtype == SysExt.ST16:
            # Store register to absolute 16-bit address
            value = self._machine.get_register(instr.src1)
            self._machine.write_mem(instr.address, value)
        elif subtype == SysExt.LDI16:
            # Load 16-bit immediate into register
            self._machine.set_register(instr.dest, instr.immediate)
        elif subtype == SysExt.JMP16:
            # Unconditional jump - update PC and mark branch taken
            self.pc = instr.address
            self._branch_taken = True
        elif subtype == SysExt.CALL16:
            # Push return address (current PC + 2) then jump
            # Todo: Call Stack Can Overflow/Underflow Silently
            self._call_stack.append((self.pc + 2) & 0xFFFF)
            self.pc = instr.address
            self._branch_taken = True
            # Todo:
        elif subtype == SysExt.STIND:
            # Indirect store: R[src1] -> memory[R[dest]]
            # Todo: Bounds Checking on Indirect Memory Access
            value = self._machine.get_register(instr.src1)
            addr = self._machine.get_register(instr.dest)
            self._machine.write_mem(addr, value)
        elif subtype == SysExt.LDIND:
            # Indirect load: memory[R[src1]] -> R[dest]
            addr = self._machine.get_register(instr.src1)
            value = self._machine.read_mem(addr)
            self._machine.set_register(instr.dest, value)
        elif subtype == SysExt.JZ:
            # Jump if zero flag set
            # Todo: Branch Target Validation
            if self.zero:
                self.pc = instr.address
                self._branch_taken = True
        elif subtype == SysExt.JNZ:
            # Jump if zero flag not set
            if not self.zero:
                self.pc = instr.address
                self._branch_taken = True
        elif subtype == SysExt.JC:
            # Jump if carry flag set
            if self.carry:
                self.pc = instr.address
                self._branch_taken = True
        elif subtype == SysExt.RET:
            # Pop return address and jump
            # Todo: Prevent recursive runaways, add a max call depth (e.g., 256) and raise an error if n>max
            if not self._call_stack:
                raise RuntimeError("RET executed on empty call stack")
            self.pc = self._call_stack.pop()
            self._branch_taken = True
        elif subtype == SysExt.PUSH:
            # Decrement SP, then store
            # Todo: Bounds Checking (auto wrap could overwrite low memory)
            value = self._machine.get_register(instr.src1)
            self._stack_pointer = (self._stack_pointer - 1) & 0xFFFF
            self._machine.write_mem(self._stack_pointer, value)
        elif subtype == SysExt.POP:
            # Load from SP, then increment
            value = self._machine.read_mem(self._stack_pointer)
            self._machine.set_register(instr.src1, value)
            self._stack_pointer = (self._stack_pointer + 1) & 0xFFFF

        self._instruction_history.append(instr)

    # ---- Memory and Register Access ----
    def __getitem__(self, addr: int) -> int:
        """Memory read with bounds checking"""
        if not (0 <= addr < self.MEMORY_SIZE):
            raise IndexError(f"Address {addr} out of range")
        if addr == 0xFFFD:  # Std input port
                return ord(input()[:1])  # blocking read
        return self._machine.read_mem(addr)

    def __setitem__(self, addr: int, value: int) -> None:
        """Memory write with bounds checking"""
        if not (0 <= addr < self.MEMORY_SIZE):
            raise IndexError(f"Address {addr} out of range")
        if not (0 <= value <= 0xFFFF):
            raise ValueError(f"Value {value} out of 16-bit range")
        if addr == 0xFFFE:  # Std output port
            print(chr(value & 0xFF), end='', flush=True)
        else:
            self._machine.write_mem(addr, value)

    def get_reg(self, reg: int) -> int:
        """Get register value"""
        return self._machine.get_register(reg)

    def set_reg(self, reg: int, value: int) -> None:
        """Set register value"""
        self._machine.set_register(reg, value)

    # ---- Properties ----
    @property
    def registers(self) -> List[int]:
        """Snapshot of all 8 registers"""
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

    # ---- Assembler Helper ----
    # Todo: Validate Register Numbers
    def assemble(self, op: str, *args) -> List[int]:
        """
        Assemble a single instruction into 16-bit words.
        Returns a list of 1 or 2 words depending on instruction type.
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
            elif op in ("JZ", "JNZ", "JC") and len(args) == 1:
                addr = args[0]
                return [(ALUOp.SYS << 12) | (subtype << 8), addr & 0xFFFF]
            elif op in ("STIND", "LDIND") and len(args) == 2:
                r1, r2 = args
                return [(ALUOp.SYS << 12) | (subtype << 8) | (r1 << 4) | r2]

        raise ValueError(f"Unknown instruction: {op} {args}")

    def assemble_program(self, instructions: List[tuple]) -> List[int]:
        """Assemble a sequence of instructions into machine code"""
        program = []
        for instr in instructions:
            program.extend(self.assemble(*instr))
        return program

    # ---- Debugging ----
    def dump(self, start: int = 0, end: int = 0x20) -> None:
        """Dump memory range and CPU state for debugging"""
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
        """Capture current CPU state as a dataclass snapshot"""
        return CPUState(
            pc=self.pc, cycles=self.cycles, halted=self.halted,
            registers=self.registers, flags=self.flags,
            mode=int(self.get_mode()), stack_pointer=self.stack_pointer
        )

    def get_history(self) -> List[Instruction]:
        """Return executed instruction history"""
        return self._instruction_history.copy()

    def clear_history(self) -> None:
        """Clear instruction history"""
        self._instruction_history.clear()

    def __repr__(self) -> str:
        return f"CPU(pc=0x{self.pc:04X}, sp=0x{self.stack_pointer:04X}, cycles={self.cycles}, halted={self.halted})"
