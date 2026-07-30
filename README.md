# Bitcraft

A Python-Controlled Gate-Level Arithmetic Engine  

## Concept
A Python library that exposes a complete 16-bit CPU data paths (ALU, memory, bus) implemented in C, but controlled entirely from Python.   
The C engine provides the "hardware" primitives; Python acts as the control unit, instruction decoder, and microcode ROM.  


## Downsides

**It's slow!**  
- Python control adds overhead
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

*API concept:  [readme](include/api.h)*  

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

### **1. Unified Addressing**
- Registers (R0-R7) at addresses 0-7
- RAM starting at address 8
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

---

## API

### **Core Operations**
```python
cpu = CPU()                    # Create CPU instance
cpu.memory[addr] = value       # Direct memory access (Pythonic)
cpu.bus_read(addr)             # Read from bus
cpu.bus_write(addr, value)     # Write to bus
cpu.alu_op(src1, src2, dest, op) # Execute ALU operation
```

### **Control Operations**
```python
cpu.pc = address               # Program counter (Python-managed)
cpu.step()                     # Execute one instruction
cpu.run(cycles)                # Run for N cycles
cpu.halt()                     # Stop execution
```

### **Mode Management**
```python
cpu.set_mode(mode)             # Change ALU behavior via SYS
cpu.saturation(enable)         # Toggle saturation arithmetic
cpu.signed_mode(enable)        # Toggle signed operations
```

### **Inspection**
```python
cpu.registers                  # Python list of current register values
cpu.flags                      # Zero, Carry, Overflow booleans
cpu.wires                      # Gate-level wire inspection
cpu.snapshot()                 # Freeze current state
```
