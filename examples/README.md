# Current CPU Template Model (Testing Phase)

```
 +-------------------------------------------------------------------+
 |                      PYTHON CONTROL ENGINE                        |
 |                                                                   |
 |  +-------------------+  +-------------------+  +---------------+  |
 |  |    CPU Class      |  | Instruction       |  | Program       |  |
 |  | (PC, SP, Decoder) |->|   Decoder         |->| Counter (PC)  |  |
 |  +-------------------+  +-------------------+  +---------------+  |
 |            |                                           |          |
 |            +-------------------+-----------------------+          |
 |                                |                                  |
 +================================v==================================+
 [ BOUNDARY LAYER ]           ctypes FFI Binding                     
 +==================================================================+
 |                                ^                                  |
 |                                | (State & Bus Reads/Writes)       |
 |                        +-------v-------+                          |
 |                        |    MACHINE    |                          |
 |                        |  (C-Runtime)  |                          |
 |                        +---------------+                          |
 |                                                                   |
 |  C-RUNTIME HARDWARE LAYERS (Datapath & Execution Engine)          |
 |  +-------------------------------------------------------------+  |
 |  |  Registers (R0-R7) & 64K Unified Memory Space               |  |
 |  +-------------------------------------------------------------+  |
 |  |  16-Bit Bus Data Path (Read / Write / Load)                 |  |
 |  +-------------------------------------------------------------+  |
 |  |  ALU Execution Units (ADD, SUB, AND, OR, XOR, SHL, etc.)    |  |
 |  +-------------------------------------------------------------+  |
 |  |  Flags Unit (Zero, Carry, Overflow)                         |  |
 |  +-------------------------------------------------------------+  |
 |  |  SYS Hatch / Mode Switcher                                  |  |
 |  +-------------------------------------------------------------+  |
 +-------------------------------------------------------------------+

```

# Opcode scheme

| Opcode / Mnemonic | Group | Parameters / Encoding | Description |
| --- | --- | --- | --- |
| **ADD**, **SUB**, **CMP** | C-Runtime | `dest, src1, src2` (3 operands) | Core arithmetic operations; updates ALU flags (Z, C, O). |
| **AND**, **OR**, **XOR**, **NAND**, **NOR**, **NOT_A** | C-Runtime | `dest, src1, src2` (or `src1` for NOT) | Bitwise logic execution units. |
| **PASS_A**, **PASS_B** | C-Runtime | `dest, src1, src2` | Pass-through operations to route register values through the ALU. |
| **SHL**, **SHR**, **ROL**, **ROR** | C-Runtime | `dest, src1, src2` | Bit shift and rotation operations. |
| **SYS** (Base) | C-Runtime / Python Escape | `subtype, src1, src2` | Control hatch opcode used to trigger Python-managed extended instruction subtypes. |
| **LD16** | Python (Extended) | `dest, address` (2 words) | Loads a 16-bit word from any absolute address (0–65535) into a register. |
| **ST16** | Python (Extended) | `address, src1` (2 words) | Stores a register's value into a 16-bit absolute memory address. |
| **LDI16** | Python (Extended) | `dest, immediate` (2 words) | Loads a 16-bit immediate constant value directly into a register. |
| **JMP16** | Python (Extended) | `address` (2 words) | Unconditional jump, updates the Python-managed Program Counter (PC). |
| **CALL16** | Python (Extended) | `address` (2 words) | Calls a subroutine, pushing the return address onto the Python call stack. |
| **RET** | Python (Extended) | *None* (1 word) | Returns from a subroutine by popping the return address into the PC. |
| **PUSH** | Python (Extended) | `src1` (1 word) | Pushes a register value onto the Python-managed software stack. |
| **POP** | Python (Extended) | `src1` (1 word) | Pops a value from the software stack into a register. |
| **HALT** | Python (Extended) | *None* (1 word) | Signals the Python CPU execution loop to terminate. |
