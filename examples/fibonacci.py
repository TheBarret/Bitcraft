#!/usr/bin/env python3
"""
Fibonacci Program
Using STIND, JNZ, computes Fib(n) for n=10, stores sequence at 0x3000.
"""

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
    print("Fibonacci (max=10):")
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
