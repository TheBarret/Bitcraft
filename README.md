# Bitcraft

A Python-Controlled Gate-Level Arithmetic Engine  

## Concept
A Python library that exposes a complete 16-bit CPU data paths (ALU, memory, bus) implemented in C,  
but controlled entirely from Python.   

## Working parts

**Binding interface:**  

This library will provide the communication between Python and C-runtime.  
```py
  from binding import Machine
```

**Loading the module:**  

Loading the library (always reset/re-initialize for clearing old/unpredictable memory).  
```py
  def run():
      try:
          machine = Machine()
          machine.reset()
      except FileNotFoundError as e:
          print(f"error: {e}")
          sys.exit(1)
```

**Run a basic sum:**  

The sum `42 + 16`, prepare three registers `r3 = r1 + r2  (0x002A + 0x0010 = 0x003A / 58 [decimal])`  


```py
  program = [
          0x0312,  # R3 = R1 + R2
          0xF000   # Halt placeholder for now *todo*
      ]
  
  machine.set_register(1, 42)
  machine.set_register(2, 16)
```

**Commit:**  

We load the byte array into the bus, and invoke the `run()`.  

```py
  load_success = machine.load_program(program)
  if load_success:
    cycles = machine.run(max_cycles=5)
```

**Inspecting results:**  

You can access registers directly from the snapshot data.  
```py
  r3_result = machine.get_register(3) # r3
  z, c, o = machine.flgs # ALU flags
```

<img width="1004" height="392" alt="testing" src="https://github.com/user-attachments/assets/57c05df4-3762-43e7-bde9-ba844452f036" />


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
