# BITCRAFT-DSL

The DSL version demonstrates how to build a functional assembler for a Bitcraft CPU model.  
It provides a more readable syntax for writing small programs, compatibility with the underlying CPU architecture.  

**Changes:**  
- **Assembler**: Added `asm.py` frontend
- **Custom Opcodes**: Extended instructions with second-level escape mechanism (`CPUOp.CUSTOM = 0xE`)
- **Strictly Sequential**: One instruction issued per step
- **No Parallelism**: No multi-issue or parallel execution support
- **Deterministic**: Every DSL verb lowers to exactly one instruction in order

**Custom Opcodes:**  
- **Two-Word Encoding**: Uses a second 16-bit word to carry a 4-bit sub-opcode plus operands
- **Cost Model**: 
  - 2 words minimum for most operations
  - 3 words for conditional jumps (`JNC`, `JO`, `JNO`) that require a full 16-bit address
  - More efficient than `LDI16+ADD` sequences for simple operations like `INC`

**Flag Handling:**  
All flag-setting operations (`INC`, `DEC`, `NEG`, `TEST`, `BIT`) write directly to the existing `AluFlags` ctypes struct,  
maintaining compatibility with the C ALU's flag population mechanism.  

## Known Issues & Behavior Notes

- **Direct Access (`ST16`, `LD16`)**: Bypasses STDIO interception, reads/writes raw memory
- **Indirect Access (`STIND`, `LDIND`)**: Routes through Python's `__setitem__`/`__getitem__`, triggering STDIO at addresses `0xFFFD`/`0xFFFE`
- **Unused Opcodes**: `CPUOp.0xF` is unused and will raise `InvalidInstructionError` if decoded
- **Reserved Custom Subops**: `COps` values `0xD-0xF` are reserved and raise `InvalidInstructionError`

#### Data Movement
| DSL Verb | Description | Example |
|----------|-------------|---------|
| `let(dest, value)` | Load immediate or copy register | `let(R1, 8)` or `let(R3, R4)` |
| `write(addr, src)` | Direct memory store (ST16) | `write(0x3000, R3)` |
| `seti(addr_reg, val_reg)` | Indirect memory store (STIND) | `seti(R2, R5)` |
| `geti(dest, addr_reg)` | Indirect memory load (LDIND) | `geti(R0, R1)` |

#### Arithmetic & Logic (3-Register ALU)
| DSL Verb | Operation | Example |
|----------|-----------|---------|
| `add(dest, a, b)` | `dest = a + b` | `add(R5, R3, R4)` |
| `sub(dest, a, b)` | `dest = a - b` | |
| `andb(dest, a, b)` | `dest = a & b` | |
| `orb(dest, a, b)` | `dest = a \| b` | |
| `xorb(dest, a, b)` | `dest = a ^ b` | |
| `compare(a, b)` | Set flags only (`a - b`) | `compare(R0, R1)` |

#### In-Place Operations
| DSL Verb | Description | Example |
|----------|-------------|---------|
| `inc(reg)` | Increment register | `inc(R2)` |
| `dec(reg)` | Decrement register | `dec(R1)` |
| `neg(reg)` | Two's complement negation | `neg(R0)` |
| `swap(reg)` | Swap high/low bytes | `swap(R0)` |
| `xchg(a, b)` | Exchange two registers | `xchg(R0, R1)` |

#### Bit Operations
| DSL Verb | Description | Example |
|----------|-------------|---------|
| `test(a, b)` | AND without storing (flags only) | `test(R0, R1)` |
| `testbit(reg, bit)` | Test specific bit (0-15) | `testbit(R0, 3)` |
| `setbit(reg, bit)` | Set specific bit | `setbit(R1, 7)` |
| `clrbit(reg, bit)` | Clear specific bit | `clrbit(R2, 15)` |

#### Control Flow
| DSL Verb | Description | Example |
|----------|-------------|---------|
| `jmp(label)` | Unconditional jump | `jmp("loop")` |
| `call(label)` | Subroutine call | `call("func")` |
| `ret()` | Return from subroutine | `ret()` |
| `ifz(label)` | Jump if zero flag set | `ifz("done")` |
| `ifnz(label)` | Jump if zero flag clear | `ifnz("loop")` |
| `ifc(label)` | Jump if carry flag set | `ifc("error")` |
| `ifnc(label)` | Jump if carry flag clear | `ifnc("continue")` |
| `ifo(label)` | Jump if overflow flag set | `ifo("overflow")` |
| `ifno(label)` | Jump if overflow flag clear | `ifno("ok")` |

#### Stack Operations
| DSL Verb | Description | Example |
|----------|-------------|---------|
| `push(reg)` | Push register to stack | `push(R0)` |
| `pop(reg)` | Pop register from stack | `pop(R0)` |

#### System
| DSL Verb | Description | Example |
|----------|-------------|---------|
| `nop()` | No operation | `nop()` |
| `halt()` | Halt execution | `halt()` |
| `relinquish(code)` | Set R0=code, then halt | `relinquish(0)` |

**Fibonacci in DSL assembly:**  
```py
from machine_dsl import CPU
from asm import Program, R0, R1, R2, R3, R4, R5, R6


def fibonacci():
    print("Loading CPU...")
    cpu = CPU()

    prog = Program(cpu)
    (prog
        .allocate("program")
            .let(R6, 0)              # zero constant for life of program
            .let(R1, 8)              # 8 more iterations
            .let(R2, 0x3002)         # output pointer
            .let(R3, 0)              # F(0) = 0
            .let(R4, 1)              # F(1) = 1
            .write(0x3000, R3)       # mem[0x3000] = 0
            .write(0x3001, R4)       # mem[0x3001] = 1
        .allocate("loop")
            .add(R5, R3, R4)         # F(k) = F(k-2) + F(k-1)
            .seti(R2, R5)            # mem[R2] = R5   (indirect store)
            .let(R3, R4)             # shift: R3 = R4
            .let(R4, R5)             #        R4 = R5
            .inc(R2)                 # advance output pointer
            .dec(R1)                 # decrement counter
            .ifnz("loop")            # loop while R1 != 0
        .relinquish(0)
    )

    cpu.pc = prog.load()
    cycles = cpu.run(max_cycles=500)
```

**Fibonacci DSL Sequencer Test:**  
```
Loading CPU...
Executed 97 cycles
Loop address: 0x020E

Fibonacci:
  F( 0) =     0
  F( 1) =     1
  F( 2) =     1
  F( 3) =     2
  F( 4) =     3
  F( 5) =     5
  F( 6) =     8
  F( 7) =    13
  F( 8) =    21
  F( 9) =    34

Registers: [0, 0, 12298, 21, 34, 34, 0, 0]
Zero flag: True
```

**Program Tracing:**  
```
Instruction trace (65 instructions):
   0: <CPU.LDI16 dest=6 imm=0x0000>
   1: <CPU.LDI16 dest=1 imm=0x0008>
   2: <CPU.LDI16 dest=2 imm=0x3002>
   3: <CPU.LDI16 dest=3 imm=0x0000>
   4: <CPU.LDI16 dest=4 imm=0x0001>
   5: <CPU.ST16 addr=0x3000, dest=0>
   6: <CPU.ST16 addr=0x3001, dest=0>
   7: <ALU.ADD dest=5 src1=3 src2=4>
   8: <CPU.STIND>
   9: <ALU.PASS_B dest=3 src1=0 src2=4>
  10: <ALU.PASS_B dest=4 src1=0 src2=5>
  11: <CPU.INC reg=2>
  12: <CPU.DEC reg=1>
  13: <CPU.JNZ addr=0x020E, dest=0>
  14: <ALU.ADD dest=5 src1=3 src2=4>
  15: <CPU.STIND>
  16: <ALU.PASS_B dest=3 src1=0 src2=4>
  17: <ALU.PASS_B dest=4 src1=0 src2=5>
  18: <CPU.INC reg=2>
  19: <CPU.DEC reg=1>
  20: <CPU.JNZ addr=0x020E, dest=0>
  21: <ALU.ADD dest=5 src1=3 src2=4>
  22: <CPU.STIND>
  23: <ALU.PASS_B dest=3 src1=0 src2=4>
  24: <ALU.PASS_B dest=4 src1=0 src2=5>
  25: <CPU.INC reg=2>
  26: <CPU.DEC reg=1>
  27: <CPU.JNZ addr=0x020E, dest=0>
  28: <ALU.ADD dest=5 src1=3 src2=4>
  29: <CPU.STIND>
  30: <ALU.PASS_B dest=3 src1=0 src2=4>
  31: <ALU.PASS_B dest=4 src1=0 src2=5>
  32: <CPU.INC reg=2>
  33: <CPU.DEC reg=1>
  34: <CPU.JNZ addr=0x020E, dest=0>
  35: <ALU.ADD dest=5 src1=3 src2=4>
  36: <CPU.STIND>
  37: <ALU.PASS_B dest=3 src1=0 src2=4>
  38: <ALU.PASS_B dest=4 src1=0 src2=5>
  39: <CPU.INC reg=2>
  40: <CPU.DEC reg=1>
  41: <CPU.JNZ addr=0x020E, dest=0>
  42: <ALU.ADD dest=5 src1=3 src2=4>
  43: <CPU.STIND>
  44: <ALU.PASS_B dest=3 src1=0 src2=4>
  45: <ALU.PASS_B dest=4 src1=0 src2=5>
  46: <CPU.INC reg=2>
  47: <CPU.DEC reg=1>
  48: <CPU.JNZ addr=0x020E, dest=0>
  49: <ALU.ADD dest=5 src1=3 src2=4>
  50: <CPU.STIND>
  51: <ALU.PASS_B dest=3 src1=0 src2=4>
  52: <ALU.PASS_B dest=4 src1=0 src2=5>
  53: <CPU.INC reg=2>
  54: <CPU.DEC reg=1>
  55: <CPU.JNZ addr=0x020E, dest=0>
  56: <ALU.ADD dest=5 src1=3 src2=4>
  57: <CPU.STIND>
  58: <ALU.PASS_B dest=3 src1=0 src2=4>
  59: <ALU.PASS_B dest=4 src1=0 src2=5>
  60: <CPU.INC reg=2>
  61: <CPU.DEC reg=1>
  62: <CPU.JNZ addr=0x020E, dest=0>
  63: <CPU.LDI16 dest=0 imm=0x0000>
  64: <CPU.HALT>
```

