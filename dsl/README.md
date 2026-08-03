# BITCRAFT-DSL Concept Language

Using the Bitcraft CPU framework, the DSL version illustrates how to build an assembler.  
This CPU variant (DSL) is strictly sequential (one instruction issued per step).  
There's no multi-issue/parallel execution, so there's no DSL surface here promising simultaneity,  
every verb lowers to exactly one instruction in order.  

Pseudo grammar example:  
```
 prog = Program(cpu)
    prog.allocate("program")
        .let(R6, 0).let(R1, 8).let(R2, 0x3002).let(R3, 0).let(R4, 1)
        .write(0x3000, R3).write(0x3001, R4)
    .allocate("loop")
        .add(R5, R3, R4)
        .seti(R2, R5)
        .let(R3, R4).let(R4, R5)
        .inc(R2).dec(R1)
        .ifnz("loop")
    .relinquish(0)
```

Express "what happens" rather than raw mnemonics,  
and let the builder itself track word-offsets so labels resolve automatically.  

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


