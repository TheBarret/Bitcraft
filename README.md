# Bitcraft (Slow Hobby Project)

A Python-Controlled Gate-Level Arithmetic Engine  

## Concept
A Python library that exposes a complete 16-bit CPU data paths (ALU, memory, bus) implemented in C,  
but controlled entirely from Python.   

## Assembly Language Concept (DSL)

See example at [DSL readme](dsl/).  

# Opcode scheme (Cheat Sheet)

### C-Runtime Operations (ALU & Logic)
*All 1-word instructions. Executed directly in C.  
Format: `[15:12]=opcode, [11:8]=dest, [7:4]=src1, [3:0]=src2`*

| Mnemonic | Parameters | Description | Notes |
|---|---|---|---|
| **ADD** | `dest, src1, src2` | `dest = src1 + src2` | Updates Z, C, O flags |
| **SUB** | `dest, src1, src2` | `dest = src1 - src2` | Updates Z, C, O flags |
| **CMP** | `dest, src1, src2` | `dest = src1 - src2` (result discarded) | Updates Z, C, O flags only |
| **AND** | `dest, src1, src2` | `dest = src1 & src2` | Updates Z flag |
| **OR** | `dest, src1, src2` | `dest = src1 \| src2` | Updates Z flag |
| **XOR** | `dest, src1, src2` | `dest = src1 ^ src2` | Updates Z flag |
| **NAND** | `dest, src1, src2` | `dest = ~(src1 & src2)` | Updates Z flag |
| **NOR** | `dest, src1, src2` | `dest = ~(src1 \| src2)` | Updates Z flag |
| **NOT_A** | `dest, src1, src2` | `dest = ~src1` | src2 ignored; updates Z flag |
| **PASS_A** | `dest, src1, src2` | `dest = src1` | src2 ignored |
| **PASS_B** | `dest, src1, src2` | `dest = src2` | src1 ignored |
| **SHL** | `dest, src1, src2` | `dest = src1 << src2` | Updates Z flag |
| **SHR** | `dest, src1, src2` | `dest = src1 >> src2` (logical) | Updates Z flag |
| **ROL** | `dest, src1, src2` | `dest = src1 rotate-left src2` | Updates Z flag |
| **ROR** | `dest, src1, src2` | `dest = src1 rotate-right src2` | Updates Z flag |

### Python Extended Operations (SYS Subtypes)
*All use opcode `0xF` (SYS). Format: `[15:12]=0xF, [11:8]=subtype, [7:4]=src1, [3:0]=src2`*

#### Memory Access
| Mnemonic | Subtype | Words | Parameters | Description | Notes |
|---|---|---|---|---|---|
| **LD16** | `0x1` | 2 | `dest, address` | `R[dest] = mem[address]` | address is 16-bit immediate in word 2 |
| **ST16** | `0x2` | 2 | `address, src1` | `mem[address] = R[src1]` | Bypasses STDIO ports |
| **LDI16** | `0x3` | 2 | `dest, immediate` | `R[dest] = immediate` | immediate is 16-bit in word 2 |
| **STIND** | `0x9` | 1 | `src1, dest` | `mem[R[dest]] = R[src1]` | Routes through STDIO at 0xFFFE |
| **LDIND** | `0xA` | 1 | `dest, src1` | `R[dest] = mem[R[src1]]` | Routes through STDIO at 0xFFFD |

#### Control Flow
| Mnemonic | Subtype | Words | Parameters | Description | Notes |
|---|---|---|---|---|---|
| **JMP16** | `0x4` | 2 | `address` | `PC = address` | Unconditional jump |
| **CALL16** | `0x5` | 2 | `address` | Push `(PC+2)`, then `PC = address` | Raises `CallStackOverflowError` if depth > 256 |
| **RET** | `0x6` | 1 | *None* | `PC = pop()` | Raises `CallStackUnderflowError` if stack empty |
| **JZ** | `0xB` | 2 | `address` | `if (Z) PC = address` | Jump if zero flag set |
| **JNZ** | `0xC` | 2 | `address` | `if (!Z) PC = address` | Jump if zero flag not set |
| **JC** | `0xD` | 2 | `address` | `if (C) PC = address` | Jump if carry flag set |

#### Stack Operations
| Mnemonic | Subtype | Words | Parameters | Description | Notes |
|---|---|---|---|---|---|
| **PUSH** | `0x7` | 1 | `src1` | `SP--; mem[SP] = R[src1]` | Raises `StackOverflowError` if SP ≤ 0x1000 |
| **POP** | `0x8` | 1 | `src1` | `R[src1] = mem[SP]; SP++` | Raises `StackUnderflowError` if SP = 0xFF00 |

#### System Control
| Mnemonic | Subtype | Words | Parameters | Description | Notes |
|---|---|---|---|---|---|
| **HALT** | `0x0` | 1 | *None* | Stop execution | Sets `halted` flag |

### Reserved Subtypes
| Subtype | Status |
|---|---|
| `0xE`, `0xF` | Reserved; raises `InvalidInstructionError` if decoded |

### STDIO Memory-Mapped Ports
| Address | Direction | Description |
|---|---|---|
| `0xFFFD` | Input | Read returns character from stdin (blocking, line-buffered) |
| `0xFFFE` | Output | Write prints character to stdout |

*Note: STDIO ports are only accessible via indirect operations (`STIND`/`LDIND`) or direct Python `cpu[addr]` access. Direct `ST16`/`LD16` bypass STDIO interception.*

## Runs the Essentials

*Example of a sum `r2 = 42 + 16`:*  
```py
import ctypes # for cpu._machine.lib.* functions

from machine import CPU, ALUOp, SysExt, Mode

def test_ALU_operations():
    cpu = CPU()

    # Pythonic memory access
    cpu[0] = 42    # R0 = 42
    cpu[1] = 16    # R1 = 16

    # Direct-access ALU operation via the C library
    # ADD: r2 = r0 + r1
    cpu._machine.lib.machine_alu_op(
        ctypes.byref(cpu._machine.state),
        0, 1, 2,
        int(ALUOp.ADD)
    )

    print(f"R2 = {cpu[2]}")
    print(f"Flags: {cpu.flags}")
    print(f"Registers: {cpu.registers}")

```

*Hello, World!:*  
```py
from machine import CPU

def hello_world():
    cpu = CPU()

    # Register allocation
    # R0 = string pointer (advances through the string)
    # R1 = output port address (constant 0xFFFE)
    # R2 = current character (loaded via LDIND)
    # R3 = increment constant (value 1)
    # R6 = zero constant (for CMP against null terminator)

    # Allocation & Configuration
    PROGRAM_BASE = 0x0200
    STRING_ADDR  = 0x4000       # string address
    OUTPUT_PORT  = 0xFFFE       # Memory-mapped output (stdout port)

    # Load string data into memory using
    # CPU.load_string(addr: int, text: str, null_terminate: bool) -> int:
    cpu.load_string(STRING_ADDR, "Hello, World!\n")

    init = cpu.assemble_program([
        ("LDI16", 0, STRING_ADDR),    # R0 = string pointer
        ("LDI16", 1, OUTPUT_PORT),    # R1 = output port address
        ("LDI16", 3, 1),              # R3 = 1 (for pointer increment)
        ("LDI16", 6, 0),              # R6 = 0 (zero constant for CMP)
    ])

    # Logic
    # LDIND(1) + CMP(1) + JZ(2) + STIND(1) + ADD(1) + JMP16(2) + HALT(1) = 9 words
    start = PROGRAM_BASE + len(init) # Calculate addresses for branch targets
    halt  = start + 8       # HALT sits at the end of the loop

    loop = cpu.assemble_program([
        ("LDIND", 2, 0),              # R2 = mem[R0]  (load next char)
        ("CMP",   6, 2, 6),           # Compare R2 with 0 → sets Z if null
        ("JZ",    halt),                # If null terminator, jump to HALT
        ("STIND", 2, 1),              # mem[R1] = R2  (write char to 0xFFFE)
        ("ADD",   0, 0, 3),           # R0 = R0 + 1   (advance pointer)
        ("JMP16", start),               # Loop back to start
        ("HALT",),                    # End of program (JZ target)
    ])

    # Assemble and load
    program = init + loop
    cpu.load_program(program, start=PROGRAM_BASE)
    cpu.pc = PROGRAM_BASE

    # Run
    cycles = cpu.run(max_cycles=1000)

if __name__ == "__main__":
    hello_world()
```

*Fibonacci Sequencer:*  
```py
from machine import CPU

def fibonacci():
    print(f"Loading CPU...")
    cpu = CPU()

    # Registers:
    #   R6 = 0 (zero constant)
    #   R0 = scratch
    #   R1 = loop counter (remaining iterations)
    #   R2 = output pointer
    #   R3 = F(k-2)
    #   R4 = F(k-1)
    #   R5 = F(k)

    # Block 1
    init = cpu.assemble_program([
        ("LDI16", 6, 0),          # R6 = 0 (zero constant for life of program)
        ("LDI16", 1, 8),          # R1 = 8 more iterations
        ("LDI16", 2, 0x3002),     # R2 = output pointer
        ("LDI16", 3, 0),          # R3 = F(0) = 0
        ("LDI16", 4, 1),          # R4 = F(1) = 1
        ("ST16", 0x3000, 3),      # mem[0x3000] = 0
        ("ST16", 0x3001, 4),      # mem[0x3001] = 1
    ])
    # Segment init + offset
    init_size = len(init)
    loop_addr = 0x0200 + init_size  # :loop_body
    loop = cpu.assemble_program([
        # Loop next number
        ("ADD", 5, 3, 4),          # R5 = F(k) = F(k-2) + F(k-1)
        ("STIND", 5, 2),           # mem[R2] = R5  (indirect store)

        # Shift: R3 = R4, R4 = R5  (using R6 as zero)
        ("ADD", 3, 4, 6),          # R3 = R4 + 0 = R4
        ("ADD", 4, 5, 6),          # R4 = R5 + 0 = R5

        # Advance pointer: R2++
        ("LDI16", 0, 1),           # R0 = 1
        ("ADD", 2, 2, 0),          # R2 = R2 + 1

        # Decrement counter
        ("LDI16", 0, 1),           # R0 = 1
        ("SUB", 1, 1, 0),          # R1--

        # Compare and loop
        ("CMP", 6, 1, 6),          # R1 - 0  (sets zero flag if R1==0)
        ("JNZ", loop_addr),         # If not zero, jump back to loop start
        ("HALT",)
    ])

    # prep start vectors
    program = init + loop
    cpu.load_program(program, start=0x0200)
    cpu.pc = 0x0200

    # commit
    cycles = cpu.run(max_cycles=500)

    # Results
    print(f"Executed {cycles} cycles")
    print(f"Loop address: 0x{loop_addr:04X}")
    print()
    print("Fibonacci:")
    for i in range(10):
        val = cpu[0x3000 + i]
        print(f"  F({i:2d}) = {val:5d}")

    print(f"\nRegisters: {cpu.registers}")
    print(f"Zero flag: {cpu.zero}")

    # Show instruction trace
    print(f"\nInstruction trace ({len(cpu.get_history())} instructions):")
    for i, instr in enumerate(cpu.get_history()):
        print(f"  {i:2d}: {instr}")


if __name__ == "__main__":
    fibonacci()

```

## Downsides

**It's slow!**  
```
Measured Speed        : ~0.079 MOPS/s
Raw C ALU Baseline    : ~1.20 MOPS/s
Python Control Cost   : ~15.2x
```
- Python control adds 11.82 µs added per cycle overhead
- Each Python instruction can execute multiple C operations
- Not suitable for high-performance computing

**Is it Managed?**  
- Python manages memory safety (no buffer overflows)
- Python handles instruction decoding
- Python orchestrates C operations
- C provides (owns) the chassis and basic functions

**Basic ALU Functions**  
- **Arithmetic**: ADD, SUB, CMP  
- **Logic**: AND, OR, XOR, NAND, NOR, NOT  
- **Pass**: PASS_A, PASS_B  
- **Shift**: SHL, SHR, ROL, ROR  
- **Control**: SYS (control hatch, mode switching)
- **Addressing**: Any address (0-65535) for `src1, src2, dest`

**Flags**  
- Z: Result is zero
- C: Carry/borrow occurrence
- O: Two's complement overflow

---

## Core Model

Python doesn't simulate the CPU, Python IS the CPU

- C provides the **execution units** (arithmetic, logic, shifts, memory)
- Python provides the **control logic** (instruction fetch, decode, sequencing)
- The separation mimics real CPU design (datapath vs. control unit)

---

## Architecture

### **C Layer (ALU+MEMORY)**

| Component | Description |
|-----------|-------------|
| **Memory** | 64K x 16-bit unified address space (registers + RAM) |
| **ALU** | 16 operations: ADD, SUB, AND, OR, XOR, NAND, NOR, NOT, PASS_A, PASS_B, SHL, SHR, ROL, ROR, CMP, SYS |
| **Bus** | 16-bit data path with read/write operations |
| **Flags** | Zero, Carry, Overflow (automatically maintained) |
| **SYS** | Control hatch, Mode-switching instruction (reconfigures ALU behavior) |

### **Python Layer (CPU)**
| Component | Description |
|-----------|-------------|
| **CPU Class** | Wraps the C state machine |
| **Instruction Decoder** | Python interprets opcodes from memory |
| **Program Counter** | Python-managed PC (not in C) |
| **Custom ISA** | Instruction set defined entirely in Python |
| **Mode Manager** | Uses SYS to reconfigure C ALU behavior |

---

## API

### **1. Unified Addressing**
- Registers (R0-R7) at addresses 0-7
- RAM starting at address `0x0200` (512) marker
- No distinction between register and memory operations

### **2. Three-Operand Instructions**
- All ALU ops: `dest = src1 OP src2`
- Sources and destinations can be any address (registers or RAM)

### **3. Python as Microcode**
- Each Python "instruction" can execute multiple C operations
- Complex instructions decomposed into bus transactions
- Python can implement operations not present in C

### **4. Runtime Reconfiguration**
- `SYS` opcode changes ALU behavior without recompilation
- Modes: saturation, signed arithmetic, rounding, polarity changes

Reference *API.H:  [readme](include/api.h)*  
Reference *ALU.H:  [readme](include/alu.h)*  
Reference *BUS.H:  [readme](include/bus.h)*  
Reference *BINDING.PY:  [readme](binding.py)*  
