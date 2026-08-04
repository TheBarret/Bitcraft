# BITCRAFT-DSL Concept Language

Using the Bitcraft CPU framework, the DSL version illustrates how to build an assembler.  
This CPU variant (DSL) is strictly sequential (one instruction issued per step).  
There's no multi-issue/parallel execution, so there's no DSL surface here promising simultaneity,  
every verb lowers to exactly one instruction in order.  

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

Reference (Verb):  
-    `allocate(name)`          mark a label at the current word offset
-    `let(dest, value)`        dest = value  (int -> LDI16, Register -> PASS_B copy)
-    `write(addr, src)`        memory[addr] = src   (direct, ST16)
-    `seti(addr_reg, val_reg)` memory[addr_reg] = val_reg   (indirect, STIND)
-    `geti(dest, addr_reg)`    dest = memory[addr_reg]      (indirect, LDIND)
-    `add/sub/andb/orb/xorb(dest, a, b)`   3-register ALU ops
-    `compare(a, b)`           sets flags only (a - b), dest is a hardware-ignored placeholder
-    `inc/dec/neg/swap(reg)`   in-place register ops (EXT2)
-    `test(a, b)`              flags-only AND (EXT2)
-    `setbit/clrbit/testbit(reg, bit)`   bit ops, bit is 0-15 (EXT2)
-    `xchg(a, b)`               swap two registers, no temp needed (EXT2)
-    `nop()`                    no-op (EXT2)
-    `jmp/call(label)`          unconditional jump / call
-    `ifz/ifnz/ifc(label)`      conditional jump on zero/not-zero/carry
-    `ifnc/ifo/ifno(label)`     conditional jump on not-carry/overflow/not-overflow (EXT2)
-    `ret() / push(reg) / pop(reg) / halt()`
-    `relinquish(code=0)`       let(R0, code) then halt() - "exit code" convention, not real hardware


