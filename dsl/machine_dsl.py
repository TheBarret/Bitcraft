"""
CPU Machine Template - With DSL Assembler (Domain-Specific Language Grammar)
Basic CPU with full 16-bit bus addressing

changelog 0.1: initial release
changelog 0.2: added extended operations (HALT, LD16, ST16, LDI16, JMP16, CALL16, RET, PUSH, POP)
changelog 0.3: added indirect addressing (STIND, LDIND) and conditional jumps (JZ, JNZ, JC)
changelog 0.4: added stdio ports, input=0xFFFD, output=0xFFFE, caught before memory __setitem__, __getitem__
changelog 0.5: patch list:
    - opcode/subtype validation (InvalidInstructionError, raised at decode time not execute time)
    - register index validation on all decode paths + assemble() (InvalidRegisterError)
    - call stack depth cap on CALL16 (CallStackOverflowError), RET underflow now a typed error
    - bounds-checked PUSH/POP stack (StackOverflowError/StackUnderflowError) instead of silent 0xFFFF wrap
    - STIND/LDIND now route through __getitem__/__setitem__ so STDIO ports (0xFFFD/0xFFFE) and
      memory bounds checks apply to indirect access too, matching direct access behavior
    - assemble() now gives explicit arg-count/range errors instead of falling through
changelog 0.6: added opcodes:
    - JNC (Jump if No Carry)
    - JO / JNO (Jump if Overflow / No Overflow)
    - NOP (No Operation)
    - INC / DEC (Increment / Decrement)
    - NEG (Negate)
    - TEST (Bitwise AND without storing, just sets flags)
    - BIT / SET / CLR (Test/Set/Clear specific bits)
    - XCHG (Exchange registers)
    - SWAP (Swap bytes within a register)

changelog 0.7: added load_string(addr: int, text: str, null_terminate: bool), QoL function.

changelog 0.8-DSL:
    - added Domain-Specific Language assembler (asm.py).
    - implemented the EXT2 second-level opcode escape (SysExt.EXT2 = 0xE) queued in 0.6.
    The original 16-slot SysExt space only had 2 free entries (0xE, 0xF),
    not enough room for the 13 ops listed above.
    EXT2 uses a second word to carry a 4-bit sub-op + operands (like SYS itself extends ALUOp),
    leaving 0xF and 3 more EXT2 subop slots free for later.
    Costs 2 words minimum (3 for JNC/JO/JNO, since they carry a full 16-bit address),
    still cheaper than LDI16+ADD for things like INC.
    No C changes: flag-setting ops (INC/DEC/NEG/TEST/BIT) write directly into the existing AluFlags ctypes struct,
    the same struct the C ALU already populates.

Known Issues & Behavior:
    - Direct access (ST16, LD16): Bypasses STDIO interception, writes/reads raw memory.
    - Indirect access (STIND, LDIND): Routes through __setitem__/__getitem__, triggers STDIO at 0xFFFD/0xFFFE.
    - SysExt 0xF is unused, will raise InvalidInstructionError if decoded.
    - EXT2 subops 0xD-0xF are reserved/unused, will raise InvalidInstructionError if decoded.
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
    EXT2  = 0xE     # Second-level escape - see Ext2Op for the real instruction
    # 0xF unused


class Ext2Op(IntEnum):
    """Sub-opcodes reached via SysExt.EXT2 (second word carries this + operands)"""
    NOP  = 0x0
    INC  = 0x1
    DEC  = 0x2
    NEG  = 0x3
    TEST = 0x4
    BIT  = 0x5
    SET  = 0x6
    CLR  = 0x7
    XCHG = 0x8
    SWAP = 0x9
    JNC  = 0xA
    JO   = 0xB
    JNO  = 0xC
    # 0xD, 0xE, 0xF reserved


class Mode(IntEnum):
    """ALU execution modes"""
    NORMAL = 0
    SATURATE = 1
    SIGNED = 2
    ROUND = 3
    POLARITY_INVERT = 4


# Typed errors
class MachineError(Exception):
    """Base class for all CPU-level runtime errors"""


class InvalidInstructionError(MachineError):
    """Raised when a decoded opcode/subtype/subop is not a recognized instruction"""


class InvalidRegisterError(MachineError):
    """Raised when an instruction references a register index outside 0-7"""


class CallStackOverflowError(MachineError):
    """Raised when CALL16 nesting exceeds CPU.MAX_CALL_DEPTH"""


class CallStackUnderflowError(MachineError, RuntimeError):
    """Raised when RET is executed with no matching CALL16 (kept RuntimeError-compatible)"""


class StackOverflowError(MachineError):
    """Raised when PUSH would drive the stack pointer below the reserved low boundary"""


class StackUnderflowError(MachineError):
    """Raised when POP is executed with nothing pushed (SP already at STACK_BASE)"""


@dataclass
class Instruction:
    """Decoded instruction representation"""
    opcode: int
    dest: int
    src1: int
    src2: int
    address: Optional[int] = None      # For LD16/ST16/JMP16/.../JNC/JO/JNO
    immediate: Optional[int] = None    # For LDI16
    subtype: Optional[int] = None      # For SYS operations
    ext2: Optional[int] = None         # For SYS.EXT2 sub-operations
    is_extended: bool = False
    words: int = 1                     # Number of 16-bit words

    def __repr__(self) -> str:
        if self.is_extended:
            if self.subtype == SysExt.EXT2:
                name = Ext2Op(self.ext2).name if self.ext2 is not None else "?"
                if self.address is not None:
                    return f"<EXT2.{name} addr=0x{self.address:04X}>"
                if name in ("INC", "DEC", "NEG", "SWAP"):
                    return f"<EXT2.{name} reg={self.dest}>"
                if name == "TEST":
                    return f"<EXT2.{name} r1={self.src1} r2={self.src2}>"
                if name in ("BIT", "SET", "CLR"):
                    return f"<EXT2.{name} reg={self.dest} bit={self.src2}>"
                if name == "XCHG":
                    return f"<EXT2.{name} r1={self.dest} r2={self.src1}>"
                return f"<EXT2.{name}>"
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

    # Reserved low boundary the stack may not cross,
    # prevents PUSH from wrapping 0x0000 -> 0xFFFF
    # Adjust upward if your programs/data live higher in memory.
    STACK_LIMIT_LOW = 0x1000

    # Max nested CALL16 depth before we treat it as a runaway/bug rather than
    # quietly growing an unbounded Python list.
    MAX_CALL_DEPTH = 256

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
        Handles 1-word ALU ops, 2-word SYS extended ops, and 2/3-word EXT2 ops.
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

        # Cycle count; 1/2/3-word instructions
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

    # Validation helpers
    def _check_reg(self, idx: int, label: str = "register") -> int:
        """Validate a decoded/assembled register index is within 0-NUM_REGISTERS-1"""
        if not (0 <= idx < self.NUM_REGISTERS):
            raise InvalidRegisterError(
                f"Invalid {label} index {idx} (0x{idx:X}): must be 0-{self.NUM_REGISTERS - 1}"
            )
        return idx

    @staticmethod
    def _check_u16(value: int, label: str = "value") -> int:
        """Validate an immediate/address fits in 16 bits"""
        if not (0 <= value <= 0xFFFF):
            raise ValueError(f"{label} {value} out of 16-bit range (0-65535)")
        return value

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

        if opcode == ALUOp.SYS:
            subtype = dest
            if subtype == SysExt.EXT2:
                extended = self._decode_ext2()
            else:
                extended = self._decode_extended(subtype, src1, src2)
            extended.opcode = opcode
            extended.is_extended = True
            return extended

        # ALU ops always reference real registers on all three fields
        self._check_reg(dest, "ALU dest")
        self._check_reg(src1, "ALU src1")
        self._check_reg(src2, "ALU src2")

        return Instruction(opcode=opcode, dest=dest, src1=src1, src2=src2, is_extended=False, words=1)

    def _decode_extended(self, subtype: int, src1: int, src2: int) -> Instruction:
        """
        Decode SYS extended instructions.
        Many SYS ops require a second 16-bit word (address or immediate).
        """
        if subtype not in SysExt._value2member_map_:
            raise InvalidInstructionError(
                f"Unrecognized SYS subtype 0x{subtype:X} at PC=0x{self.pc:04X}"
            )

        instr = Instruction(opcode=ALUOp.SYS, dest=0, src1=src1, src2=src2,
                            subtype=subtype, is_extended=True, words=2)

        second_word = self._machine.read_mem((self.pc + 1) & 0xFFFF)

        if subtype == SysExt.LD16:
            instr.dest = self._check_reg(src1, "LD16 dest")
            instr.address = second_word
        elif subtype == SysExt.ST16:
            instr.address = second_word
            instr.src1 = self._check_reg(src1, "ST16 src")
        elif subtype == SysExt.LDI16:
            instr.dest = self._check_reg(src1, "LDI16 dest")
            instr.immediate = second_word
        elif subtype in (SysExt.JMP16, SysExt.CALL16,
                         SysExt.JZ, SysExt.JNZ, SysExt.JC):
            instr.address = second_word
        elif subtype in (SysExt.STIND, SysExt.LDIND):
            # Indirect ops are 1 word: first nybble=src1, second=src2
            instr.words = 1
            if subtype == SysExt.STIND:
                instr.src1 = self._check_reg(src1, "STIND value reg")   # value register
                instr.dest = self._check_reg(src2, "STIND addr reg")    # address register
            else:  # LDIND
                instr.dest = self._check_reg(src1, "LDIND dest reg")    # destination register
                instr.src1 = self._check_reg(src2, "LDIND addr reg")    # address register
        elif subtype in (SysExt.PUSH, SysExt.POP):
            instr.src1 = self._check_reg(src1, f"{SysExt(subtype).name} reg")
            instr.words = 1
        elif subtype in (SysExt.RET, SysExt.HALT):
            instr.src1 = 0
            instr.words = 1

        return instr

    def _decode_ext2(self) -> Instruction:
        """Decode a SysExt.EXT2 instruction - word 2 carries the real sub-op + operands."""
        word2 = self._machine.read_mem((self.pc + 1) & 0xFFFF)
        subop_raw = (word2 >> 12) & 0xF
        if subop_raw not in Ext2Op._value2member_map_:
            raise InvalidInstructionError(
                f"Unrecognized EXT2 subop 0x{subop_raw:X} at PC=0x{self.pc:04X}"
            )
        subop = Ext2Op(subop_raw)
        a = (word2 >> 8) & 0xF
        b = (word2 >> 4) & 0xF

        instr = Instruction(opcode=ALUOp.SYS, dest=0, src1=0, src2=0,
                            subtype=SysExt.EXT2, is_extended=True, words=2)
        instr.ext2 = subop

        if subop in (Ext2Op.JNC, Ext2Op.JO, Ext2Op.JNO):
            instr.address = self._machine.read_mem((self.pc + 2) & 0xFFFF)
            instr.words = 3
        elif subop == Ext2Op.NOP:
            pass
        elif subop in (Ext2Op.INC, Ext2Op.DEC, Ext2Op.NEG, Ext2Op.SWAP):
            instr.dest = self._check_reg(a, f"{subop.name} reg")
        elif subop == Ext2Op.TEST:
            instr.src1 = self._check_reg(a, "TEST reg1")
            instr.src2 = self._check_reg(b, "TEST reg2")
        elif subop in (Ext2Op.BIT, Ext2Op.SET, Ext2Op.CLR):
            instr.dest = self._check_reg(a, f"{subop.name} reg")
            instr.src2 = b  # bit position 0-15, already range-safe (nibble)
        elif subop == Ext2Op.XCHG:
            instr.dest = self._check_reg(a, "XCHG reg1")
            instr.src1 = self._check_reg(b, "XCHG reg2")

        return instr

    def _execute_alu(self, instr: Instruction) -> None:
        """Execute a standard ALU operation - simple, fast, direct C call"""
        self._machine.lib.machine_alu_op(
            ctypes.byref(self._machine.state),
            instr.src1, instr.src2, instr.dest, instr.opcode
        )
        self._instruction_history.append(instr)

    def _set_flags(self, zero: Optional[bool] = None, carry: Optional[bool] = None,
                   overflow: Optional[bool] = None) -> None:
        """
        Directly write ALU flag bits for Python-implemented EXT2 ops.
        Writes into the same AluFlags ctypes struct the C ALU already populates -
        no new C functions needed, just direct field access per this file's Core Model.
        """
        if zero is not None:
            self._machine.state.bus.flags.zero.v = 1 if zero else 0
        if carry is not None:
            self._machine.state.bus.flags.carry.v = 1 if carry else 0
        if overflow is not None:
            self._machine.state.bus.flags.overflow.v = 1 if overflow else 0

    def _execute_ext2(self, instr: Instruction) -> None:
        """Execute a SysExt.EXT2 sub-operation. subop validity guaranteed by _decode_ext2."""
        op = Ext2Op(instr.ext2)
        if op == Ext2Op.NOP:
            pass
        elif op == Ext2Op.INC:
            r = self._machine.get_register(instr.dest)
            new = (r + 1) & 0xFFFF
            self._machine.set_register(instr.dest, new)
            self._set_flags(zero=(new == 0), carry=(r == 0xFFFF), overflow=(r == 0x7FFF))
        elif op == Ext2Op.DEC:
            r = self._machine.get_register(instr.dest)
            new = (r - 1) & 0xFFFF
            self._machine.set_register(instr.dest, new)
            self._set_flags(zero=(new == 0), carry=(r == 0), overflow=(r == 0x8000))
        elif op == Ext2Op.NEG:
            r = self._machine.get_register(instr.dest)
            new = ((~r) + 1) & 0xFFFF
            self._machine.set_register(instr.dest, new)
            self._set_flags(zero=(new == 0), carry=(r != 0), overflow=(r == 0x8000))
        elif op == Ext2Op.TEST:
            a = self._machine.get_register(instr.src1)
            b = self._machine.get_register(instr.src2)
            self._set_flags(zero=((a & b) == 0), carry=False, overflow=False)
        elif op == Ext2Op.BIT:
            r = self._machine.get_register(instr.dest)
            bit = instr.src2
            self._set_flags(zero=(((r >> bit) & 1) == 0))
        elif op == Ext2Op.SET:
            r = self._machine.get_register(instr.dest)
            bit = instr.src2
            self._machine.set_register(instr.dest, r | (1 << bit))
        elif op == Ext2Op.CLR:
            r = self._machine.get_register(instr.dest)
            bit = instr.src2
            self._machine.set_register(instr.dest, r & ~(1 << bit) & 0xFFFF)
        elif op == Ext2Op.XCHG:
            a = self._machine.get_register(instr.dest)
            b = self._machine.get_register(instr.src1)
            self._machine.set_register(instr.dest, b)
            self._machine.set_register(instr.src1, a)
        elif op == Ext2Op.SWAP:
            r = self._machine.get_register(instr.dest)
            new = ((r & 0xFF) << 8) | ((r >> 8) & 0xFF)
            self._machine.set_register(instr.dest, new)
        elif op == Ext2Op.JNC:
            if not self.carry:
                self.pc = instr.address
                self._branch_taken = True
        elif op == Ext2Op.JO:
            if self.overflow:
                self.pc = instr.address
                self._branch_taken = True
        elif op == Ext2Op.JNO:
            if not self.overflow:
                self.pc = instr.address
                self._branch_taken = True

        self._instruction_history.append(instr)

    def _execute_extended(self, instr: Instruction) -> None:
        """
        Execute SYS extended instructions.
        This is the complex part - handles memory ops, branches, stack, and control flow.
        Each subtype has different operand requirements and side effects.
        subtype validity is already guaranteed by _decode_extended.
        """
        subtype = SysExt(instr.subtype)
        if subtype == SysExt.EXT2:
            self._execute_ext2(instr)
            return
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
            if len(self._call_stack) >= self.MAX_CALL_DEPTH:
                raise CallStackOverflowError(
                    f"CALL16 nesting exceeded MAX_CALL_DEPTH={self.MAX_CALL_DEPTH} "
                    f"at PC=0x{self.pc:04X} -> target 0x{instr.address:04X}"
                )
            self._call_stack.append((self.pc + 2) & 0xFFFF)
            self.pc = instr.address
            self._branch_taken = True
        elif subtype == SysExt.STIND:
            # Indirect store: R[src1] -> memory[R[dest]]
            # Routed through __setitem__ so STDIO output port (0xFFFE) and bounds
            # checks apply the same way they do for direct ST16.
            value = self._machine.get_register(instr.src1)
            addr = self._machine.get_register(instr.dest)
            self[addr] = value
        elif subtype == SysExt.LDIND:
            # Indirect load: memory[R[src1]] -> R[dest]
            addr = self._machine.get_register(instr.src1)
            value = self[addr]
            self._machine.set_register(instr.dest, value)
        elif subtype == SysExt.JZ:
            # Jump if zero flag set
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
            if not self._call_stack:
                raise CallStackUnderflowError(
                    f"RET executed on empty call stack at PC=0x{self.pc:04X}"
                )
            self.pc = self._call_stack.pop()
            self._branch_taken = True
        elif subtype == SysExt.PUSH:
            # Decrement SP, then store. Guarded against wrapping into low memory.
            new_sp = (self._stack_pointer - 1) & 0xFFFF
            if self._stack_pointer <= self.STACK_LIMIT_LOW:
                raise StackOverflowError(
                    f"PUSH would drive SP below STACK_LIMIT_LOW=0x{self.STACK_LIMIT_LOW:04X} "
                    f"(current SP=0x{self._stack_pointer:04X}) at PC=0x{self.pc:04X}"
                )
            value = self._machine.get_register(instr.src1)
            self._stack_pointer = new_sp
            self._machine.write_mem(self._stack_pointer, value)
        elif subtype == SysExt.POP:
            if self._stack_pointer >= self.STACK_BASE:
                raise StackUnderflowError(
                    f"POP with nothing pushed (SP=0x{self._stack_pointer:04X} == STACK_BASE) "
                    f"at PC=0x{self.pc:04X}"
                )
            value = self._machine.read_mem(self._stack_pointer)
            self._machine.set_register(instr.src1, value)
            self._stack_pointer = (self._stack_pointer + 1) & 0xFFFF

        self._instruction_history.append(instr)

    # Memory and Register Access
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
        self._check_reg(reg)
        return self._machine.get_register(reg)

    def set_reg(self, reg: int, value: int) -> None:
        """Set register value"""
        self._check_reg(reg)
        self._check_u16(value, "register value")
        self._machine.set_register(reg, value)

    def load_string(self, addr: int, text: str, null_terminate: bool = True) -> int:
        """
        Load a string into memory starting at address
        Returns the number of bytes written (including null terminator if enabled).
        """
        bytes_written = 0
        for i, char in enumerate(text):
            self[addr + i] = ord(char) & 0xFF  # 8-bit char in 16-bit word
            bytes_written += 1

        if null_terminate:
            self[addr + bytes_written] = 0
            bytes_written += 1

        return bytes_written

    # Properties
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

    # Assembler Helper
    def assemble(self, op: str, *args) -> List[int]:
        """
        Assemble a single instruction into 16-bit words.
        Returns a list of 1, 2, or 3 words depending on instruction type.
        Validates register indices (0-7) and immediate/address ranges.
        """
        op = op.upper()
        if op in ALUOp.__members__:
            opcode = ALUOp[op]
            if len(args) != 3:
                raise ValueError(f"{op} expects 3 register args (dest, src1, src2), got {len(args)}: {args}")
            dest, src1, src2 = args
            self._check_reg(dest, f"{op} dest")
            self._check_reg(src1, f"{op} src1")
            self._check_reg(src2, f"{op} src2")
            return [(opcode << 12) | (dest << 8) | (src1 << 4) | src2]

        elif op in SysExt.__members__ and op != "EXT2":
            subtype = SysExt[op]
            if op == "LD16":
                if len(args) != 2:
                    raise ValueError(f"LD16 expects (dest, addr), got {len(args)}: {args}")
                dest, addr = args
                self._check_reg(dest, "LD16 dest")
                self._check_u16(addr, "LD16 addr")
                return [(ALUOp.SYS << 12) | (subtype << 8) | (dest << 4), addr]
            elif op == "ST16":
                if len(args) != 2:
                    raise ValueError(f"ST16 expects (addr, src), got {len(args)}: {args}")
                addr, src = args
                self._check_u16(addr, "ST16 addr")
                self._check_reg(src, "ST16 src")
                return [(ALUOp.SYS << 12) | (subtype << 8) | (src << 4), addr]
            elif op == "LDI16":
                if len(args) != 2:
                    raise ValueError(f"LDI16 expects (dest, imm), got {len(args)}: {args}")
                dest, imm = args
                self._check_reg(dest, "LDI16 dest")
                self._check_u16(imm, "LDI16 imm")
                return [(ALUOp.SYS << 12) | (subtype << 8) | (dest << 4), imm]
            elif op in ("JMP16", "CALL16", "JZ", "JNZ", "JC"):
                if len(args) != 1:
                    raise ValueError(f"{op} expects (addr,), got {len(args)}: {args}")
                addr = args[0]
                self._check_u16(addr, f"{op} addr")
                return [(ALUOp.SYS << 12) | (subtype << 8), addr]
            elif op == "HALT":
                if len(args) != 0:
                    raise ValueError(f"HALT expects no args, got {len(args)}: {args}")
                return [(ALUOp.SYS << 12) | (subtype << 8)]
            elif op in ("PUSH", "POP"):
                if len(args) != 1:
                    raise ValueError(f"{op} expects (reg,), got {len(args)}: {args}")
                src = args[0]
                self._check_reg(src, f"{op} reg")
                return [(ALUOp.SYS << 12) | (subtype << 8) | (src << 4)]
            elif op == "RET":
                if len(args) != 0:
                    raise ValueError(f"RET expects no args, got {len(args)}: {args}")
                return [(ALUOp.SYS << 12) | (subtype << 8)]
            elif op in ("STIND", "LDIND"):
                if len(args) != 2:
                    raise ValueError(f"{op} expects (reg1, reg2), got {len(args)}: {args}")
                r1, r2 = args
                self._check_reg(r1, f"{op} reg1")
                self._check_reg(r2, f"{op} reg2")
                return [(ALUOp.SYS << 12) | (subtype << 8) | (r1 << 4) | r2]

        elif op in Ext2Op.__members__:
            subop = Ext2Op[op]
            word1 = (ALUOp.SYS << 12) | (SysExt.EXT2 << 8)
            if op == "NOP":
                if len(args) != 0:
                    raise ValueError(f"NOP expects no args, got {len(args)}: {args}")
                return [word1, (subop << 12)]
            elif op in ("INC", "DEC", "NEG", "SWAP"):
                if len(args) != 1:
                    raise ValueError(f"{op} expects (reg,), got {len(args)}: {args}")
                reg = args[0]
                self._check_reg(reg, f"{op} reg")
                return [word1, (subop << 12) | (reg << 8)]
            elif op == "TEST":
                if len(args) != 2:
                    raise ValueError(f"TEST expects (reg1, reg2), got {len(args)}: {args}")
                a, b = args
                self._check_reg(a, "TEST reg1")
                self._check_reg(b, "TEST reg2")
                return [word1, (subop << 12) | (a << 8) | (b << 4)]
            elif op in ("BIT", "SET", "CLR"):
                if len(args) != 2:
                    raise ValueError(f"{op} expects (reg, bit), got {len(args)}: {args}")
                reg, bit = args
                self._check_reg(reg, f"{op} reg")
                if not (0 <= bit <= 15):
                    raise ValueError(f"{op} bit position {bit} out of range (0-15)")
                return [word1, (subop << 12) | (reg << 8) | (bit << 4)]
            elif op == "XCHG":
                if len(args) != 2:
                    raise ValueError(f"XCHG expects (reg1, reg2), got {len(args)}: {args}")
                a, b = args
                self._check_reg(a, "XCHG reg1")
                self._check_reg(b, "XCHG reg2")
                return [word1, (subop << 12) | (a << 8) | (b << 4)]
            elif op in ("JNC", "JO", "JNO"):
                if len(args) != 1:
                    raise ValueError(f"{op} expects (addr,), got {len(args)}: {args}")
                addr = args[0]
                self._check_u16(addr, f"{op} addr")
                return [word1, (subop << 12), addr]

        raise ValueError(f"Unknown instruction: {op} {args}")

    def assemble_program(self, instructions: List[tuple]) -> List[int]:
        """Assemble a sequence of instructions into machine code"""
        program = []
        for instr in instructions:
            program.extend(self.assemble(*instr))
        return program

    # Debugging
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
