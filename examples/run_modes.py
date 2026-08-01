#!/usr/bin/env python3
"""
    Examples
"""
import ctypes # for cpu._machine.lib.* functions

from machine import CPU, ALUOp, SysExt, Mode

def test_ALU_operations():
    cpu = CPU()

    # Pythonic memory access
    cpu[0] = 42    # R0 = 42
    cpu[1] = 16    # R1 = 16

    # Direct-access ALU operation via the C library
    cpu._machine.lib.machine_alu_op(
        ctypes.byref(cpu._machine.state),
        0, 1, 2,
        int(ALUOp.ADD)
    )

    print(f"R2 = {cpu[2]} (expecting=58)")
    print(f"Flags: {cpu.flags}")
    print(f"Registers: {cpu.registers}")

def test_extended_addressing():
    """Demonstrate LD16/ST16 operations"""
    cpu = CPU()

    # Write data to memory at 0x1000
    cpu[0x1000] = 0x1234
    cpu[0x1001] = 0x5678

    # LD16: Load from 16-bit address into register
    value = cpu[0x1000]  # Python handles this
    cpu.set_reg(2, value)

    # LDI16: Load 16-bit immediate
    cpu[3] = 0xABCD

    # ST16: Store register to 16-bit address
    cpu[0x2000] = cpu.get_reg(3)

    print(f"Memory[0x1000] = 0x{cpu[0x1000]:04X}")
    print(f"R2 = 0x{cpu.get_reg(2):04X}")
    print(f"Memory[0x2000] = 0x{cpu[0x2000]:04X}")

def test_program_execution():
    """Execute a program with both normal and extended instructions"""
    cpu = CPU()

    # Assemble program using Python helpers
    program = cpu.assemble_program([
        ("LDI16", 0, 0x0200),      # R0 = 0x0200 (program start)
        ("LDI16", 1, 0x1000),      # R1 = 0x1000
        ("ADD", 2, 0, 1),          # R2 = R0 + R1
        ("ST16", 0x2000, 2),       # Store R2 to 0x2000
        ("HALT",)
    ])

    # Load and run
    cpu.load_program(program, start=0x0200)
    cpu.pc = 0x0200
    cycles = cpu.run(max_cycles=10)

    print(f"Executed {cycles} cycles")
    print(f"R0 = 0x{cpu.get_reg(0):04X}")
    print(f"R1 = 0x{cpu.get_reg(1):04X}")
    print(f"R2 = 0x{cpu.get_reg(2):04X}")
    print(f"Memory[0x2000] = 0x{cpu[0x2000]:04X}")

    # Show history
    for i, instr in enumerate(cpu.get_history()):
        print(f"  {i:2d}: {instr}")


if __name__ == "__main__":
    test_ALU_operations()
    test_extended_addressing()
    test_program_execution()
    print("Finished!")
