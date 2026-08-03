#!/usr/bin/env python3
"""
    Print 'Hello, World'
"""

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
