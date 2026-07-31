# CPU Template Model

```
Scope      ║ Modules    | ACCESS
-----------║------------|-----------
           ║ BIT        |  yes
           ║ GATES      |  yes
           ║ ADDER      |  yes
           ║ ALU        |  yes
C-RUNTIME  ║ BUS        |  yes
═══════════[Binding]═>[MEMORY/SYS]
PYTHON     ║ [CPU]      |  yes

```

# Todo

**State Duplication / Sync:**  
Python tracks self._stack_pointer on its own side, while other states like pc, halted, and cycles pull directly from `self._machine.state`.  
Ensure C-runtime doesn't alter values behind Python's back to prevent desynchronization (e.g., if a C-side operation or reset changes the stack pointer).  

**Performance Hotspots:**  
Because step() runs entirely in Python—fetching via `_machine.read_mem()`,  
decoding via bitwise shifts, and dispatching—the overhead per cycle will be noticeable if try to run programs with millions of instructions.  
