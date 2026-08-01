# Bitcraft (Slow project)

A Python-Controlled Gate-Level Arithmetic Engine  

## Concept
A Python library that exposes a complete 16-bit CPU data paths (ALU, memory, bus) implemented in C,  
but controlled entirely from Python.   

## Working parts & bits
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

    print(f"R2 = {cpu[2]} (expecting=58)")
    print(f"Flags: {cpu.flags}")
    print(f"Registers: {cpu.registers}")

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
