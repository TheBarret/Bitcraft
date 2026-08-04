#!/usr/bin/env python3
"""
    Fibonacci- DSL version
"""
from machine_dsl import CPU
from asm import Program, R0, R1, R2, R3, R4, R5, R6


def fibonacci():
    print("Loading CPU...")
    cpu = CPU()

    print("Assembling program...")
    prog = Program(cpu)
    (prog
        .allocate("program")
            .let(R6, 0)              # zero constant for life of program
            .let(R1, 8)              # 8 iterations
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
    cycles = cpu.run(max_cycles=100)

    print(f"Finished, executed {cycles} cycles")
    print(f"\nFibonacci Sequence:")
    for i in range(10):
        val = cpu[0x3000 + i]
        print(f"  F({i:2d}) = {val:5d}")


    #def dump(self, start: int = 0, end: int = 0x20) -> None:
    cpu.dump(0, 0x0010)

    #print(f"\nRegisters: {cpu.registers}")
    #print(f"Zero flag: {cpu.zero}")
    #print(f"\nInstruction trace ({len(cpu.get_history())} instructions):")
    #for i, instr in enumerate(cpu.get_history()):
    #    print(f"  {i:2d}: {instr}")


if __name__ == "__main__":
    fibonacci()
