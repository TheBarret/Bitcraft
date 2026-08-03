"""
asm.py - DSL assembler

Language Model:
express "what happens" rather than raw mnemonics,
and let the builder itself track word-offsets so labels resolve automatically
(no more manually computing loop_addr = 0x0200 + init_size by hand).

    prog = Program(cpu)
    prog.allocate("program") \\
        .let(R6, 0).let(R1, 8).let(R2, 0x3002).let(R3, 0).let(R4, 1) \\
        .write(0x3000, R3).write(0x3001, R4) \\
    .allocate("loop") \\
        .add(R5, R3, R4) \\
        .seti(R2, R5) \\
        .let(R3, R4).let(R4, R5) \\
        .inc(R2).dec(R1) \\
        .ifnz("loop") \\
    .relinquish(0)

    cpu.pc = prog.load()   # assembles, loads into cpu memory, sets PC
    cpu.run(max_cycles=500)

Reference (Verb):
    allocate(name)          mark a label at the current word offset
    let(dest, value)        dest = value  (int -> LDI16, Register -> PASS_B copy)
    write(addr, src)        memory[addr] = src   (direct, ST16)
    seti(addr_reg, val_reg) memory[addr_reg] = val_reg   (indirect, STIND)
    geti(dest, addr_reg)    dest = memory[addr_reg]      (indirect, LDIND)
    add/sub/andb/orb/xorb(dest, a, b)   3-register ALU ops
    compare(a, b)           sets flags only (a - b), dest is a hardware-ignored placeholder
    inc/dec/neg/swap(reg)   in-place register ops (EXT2)
    test(a, b)              flags-only AND (EXT2)
    setbit/clrbit/testbit(reg, bit)   bit ops, bit is 0-15 (EXT2)
    xchg(a, b)               swap two registers, no temp needed (EXT2)
    nop()                    no-op (EXT2)
    jmp/call(label)          unconditional jump / call
    ifz/ifnz/ifc(label)      conditional jump on zero/not-zero/carry
    ifnc/ifo/ifno(label)     conditional jump on not-carry/overflow/not-overflow (EXT2)
    ret() / push(reg) / pop(reg) / halt()
    relinquish(code=0)       let(R0, code) then halt() - "exit code" convention, not real hardware

Known limitation:
This CPU variant (DSL) is strictly sequential (one instruction issued per step).
There's no multi-issue/parallel execution, so there's no DSL surface here promising simultaneity,
every verb lowers to exactly one instruction in order.
"""

from typing import List, Union, Optional, Dict
from machine import CPU


class Register:
    """Symbolic register reference. Use R0..R7 below rather than constructing directly."""
    __slots__ = ("index",)

    def __init__(self, index: int):
        self.index = index

    def __repr__(self) -> str:
        return f"R{self.index}"

    def __eq__(self, other) -> bool:
        return isinstance(other, Register) and self.index == other.index

    def __hash__(self) -> int:
        return hash(("Register", self.index))


R0, R1, R2, R3, R4, R5, R6, R7 = (Register(i) for i in range(8))
REGISTERS = [R0, R1, R2, R3, R4, R5, R6, R7]

Operand = Union[int, Register]


class Program:
    """
    Every verb appends one instruction and returns self,
    so calls chain. .allocate() is a marker only,
    it costs no words, it just records the current address under a name for later jump/call targets.

    Word counts per mnemonic are fixed (don't depend on operand values),
    so the builder can track addresses immediately as it goes.
    Label *values* are only needed when a jump instruction is finally assembled into words,
    which happens in .build(), after the whole chain has run,
    so forward references to labels defined later in the chain work with no special handling.
    """

    # word-size per mnemonic (LET dispatches to LDI16 or PASS_B itself, see let())
    _WORDS: Dict[str, int] = {
        'ADD': 1, 'SUB': 1, 'AND': 1, 'OR': 1, 'XOR': 1, 'NAND': 1, 'NOR': 1,
        'NOT_A': 1, 'PASS_A': 1, 'PASS_B': 1, 'SHL': 1, 'SHR': 1, 'ROL': 1,
        'ROR': 1, 'CMP': 1,
        'ST16': 2, 'LDI16': 2, 'JMP16': 2, 'CALL16': 2, 'JZ': 2, 'JNZ': 2, 'JC': 2,
        'STIND': 1, 'LDIND': 1, 'RET': 1, 'PUSH': 1, 'POP': 1, 'HALT': 1,
        'INC': 2, 'DEC': 2, 'NEG': 2, 'SWAP': 2, 'TEST': 2,
        'BIT': 2, 'SET': 2, 'CLR': 2, 'XCHG': 2, 'NOP': 2,
        'JNC': 3, 'JO': 3, 'JNO': 3,
    }

    def __init__(self, cpu: CPU, start: Optional[int] = None):
        self.cpu = cpu
        self.start = start if start is not None else cpu.PROGRAM_START
        self._pc = self.start
        self.ops: List[tuple] = []       # (mnemonic, args) - args may contain label names (str)
        self.labels: Dict[str, int] = {}

    # internals
    def _emit(self, mnemonic: str, *args) -> "Program":
        if mnemonic not in self._WORDS:
            raise ValueError(f"Unknown mnemonic '{mnemonic}' - not in word-size table")
        self.ops.append((mnemonic, args))
        self._pc += self._WORDS[mnemonic]
        return self

    @staticmethod
    def _reg(r: Operand) -> int:
        if isinstance(r, Register):
            return r.index
        return r  # allow raw ints for anyone who prefers them

    # structure
    def allocate(self, name: str) -> "Program":
        """Mark a label at the current word offset. Costs no words."""
        if name in self.labels:
            raise ValueError(f"label '{name}' already allocated at 0x{self.labels[name]:04X}")
        self.labels[name] = self._pc
        return self

    # data movement
    def let(self, dest: Operand, value: Operand) -> "Program":
        """dest = value. int -> LDI16 (2 words). Register -> PASS_B copy (1 word, no ADD-with-1 hack)."""
        d = self._reg(dest)
        if isinstance(value, Register):
            return self._emit('PASS_B', d, 0, value.index)
        return self._emit('LDI16', d, value)

    def write(self, addr: int, src: Operand) -> "Program":
        """memory[addr] = src  (direct, ST16)"""
        return self._emit('ST16', addr, self._reg(src))

    def seti(self, addr_reg: Operand, val_reg: Operand) -> "Program":
        """memory[addr_reg] = val_reg  (indirect store, STIND)"""
        return self._emit('STIND', self._reg(val_reg), self._reg(addr_reg))

    def geti(self, dest: Operand, addr_reg: Operand) -> "Program":
        """dest = memory[addr_reg]  (indirect load, LDIND)"""
        return self._emit('LDIND', self._reg(dest), self._reg(addr_reg))

    # arithmetic / logic (base ALU, 3-register)
    def add(self, dest: Operand, a: Operand, b: Operand) -> "Program":
        return self._emit('ADD', self._reg(dest), self._reg(a), self._reg(b))

    def sub(self, dest: Operand, a: Operand, b: Operand) -> "Program":
        return self._emit('SUB', self._reg(dest), self._reg(a), self._reg(b))

    def andb(self, dest: Operand, a: Operand, b: Operand) -> "Program":
        return self._emit('AND', self._reg(dest), self._reg(a), self._reg(b))

    def orb(self, dest: Operand, a: Operand, b: Operand) -> "Program":
        return self._emit('OR', self._reg(dest), self._reg(a), self._reg(b))

    def xorb(self, dest: Operand, a: Operand, b: Operand) -> "Program":
        return self._emit('XOR', self._reg(dest), self._reg(a), self._reg(b))

    def compare(self, a: Operand, b: Operand) -> "Program":
        """Sets flags from (a - b). dest is a hardware-ignored placeholder (0)."""
        return self._emit('CMP', 0, self._reg(a), self._reg(b))

    # EXT2: arithmetic shortcuts / bit manipulation / data movement
    def inc(self, reg: Operand) -> "Program":
        return self._emit('INC', self._reg(reg))

    def dec(self, reg: Operand) -> "Program":
        return self._emit('DEC', self._reg(reg))

    def neg(self, reg: Operand) -> "Program":
        return self._emit('NEG', self._reg(reg))

    def swap(self, reg: Operand) -> "Program":
        return self._emit('SWAP', self._reg(reg))

    def test(self, a: Operand, b: Operand) -> "Program":
        """Flags-only AND - like compare(), but bitwise."""
        return self._emit('TEST', self._reg(a), self._reg(b))

    def setbit(self, reg: Operand, bit: int) -> "Program":
        return self._emit('SET', self._reg(reg), bit)

    def clrbit(self, reg: Operand, bit: int) -> "Program":
        return self._emit('CLR', self._reg(reg), bit)

    def testbit(self, reg: Operand, bit: int) -> "Program":
        """Sets zero flag from the given bit of reg."""
        return self._emit('BIT', self._reg(reg), bit)

    def xchg(self, a: Operand, b: Operand) -> "Program":
        return self._emit('XCHG', self._reg(a), self._reg(b))

    def nop(self) -> "Program":
        return self._emit('NOP')

    # control flow
    def jmp(self, label: str) -> "Program":
        return self._emit('JMP16', label)

    def call(self, label: str) -> "Program":
        return self._emit('CALL16', label)

    def ret(self) -> "Program":
        return self._emit('RET')

    def ifz(self, label: str) -> "Program":
        return self._emit('JZ', label)

    def ifnz(self, label: str) -> "Program":
        return self._emit('JNZ', label)

    def ifc(self, label: str) -> "Program":
        return self._emit('JC', label)

    def ifnc(self, label: str) -> "Program":
        return self._emit('JNC', label)

    def ifo(self, label: str) -> "Program":
        return self._emit('JO', label)

    def ifno(self, label: str) -> "Program":
        return self._emit('JNO', label)

    # stack
    def push(self, reg: Operand) -> "Program":
        return self._emit('PUSH', self._reg(reg))

    def pop(self, reg: Operand) -> "Program":
        return self._emit('POP', self._reg(reg))

    # termination
    def halt(self) -> "Program":
        return self._emit('HALT')

    def relinquish(self, code: int = 0) -> "Program":
        """
        let(R0, code) then halt(). Establishes 'R0 holds the exit code' as a
        software convention you can check after cpu.run() returns - there's no
        hardware exit-code concept, this is sugar over LDI16 + HALT.
        """
        self.let(R0, code)
        return self.halt()

    # assembly
    def build(self) -> List[int]:
        """Resolve labels and assemble the full op list into 16-bit words."""
        words: List[int] = []
        for mnemonic, args in self.ops:
            resolved = []
            for a in args:
                if isinstance(a, str):
                    if a not in self.labels:
                        raise ValueError(f"undefined label '{a}' referenced by {mnemonic}")
                    resolved.append(self.labels[a])
                else:
                    resolved.append(a)
            words.extend(self.cpu.assemble(mnemonic, *resolved))
        return words

    def load(self) -> int:
        """Assemble, load into cpu memory at self.start, and return that start address."""
        words = self.build()
        if not self.cpu.load_program(words, start=self.start):
            raise RuntimeError("load_program failed - program may exceed memory bounds")
        return self.start

    def __repr__(self) -> str:
        return f"Program(start=0x{self.start:04X}, ops={len(self.ops)}, labels={list(self.labels)})"
