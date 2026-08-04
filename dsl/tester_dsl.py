from machine_dsl import CPU
from asm import Program, R0, R1, R2, R3, R4, R5, R6, R7

def test_alu_operations():
    cpu = CPU()
    prog = Program(cpu)

    (prog
        .allocate("start")
            .let(R0, 0x1234)
            .let(R1, 0x0F0F)
            .let(R2, 0x0000)
            .let(R3, 0x0001)


        # 1. ARITHMETIC OPERATIONS


        .allocate("test_add")
            .add(R2, R0, R1)
            .write(0x2000, R2)

        .allocate("test_sub")
            .sub(R2, R0, R1)
            .write(0x2001, R2)

        .allocate("test_sub_borrow")
            .sub(R2, R1, R0)
            .write(0x2002, R2)


        # 2. LOGICAL OPERATIONS


        .allocate("test_and")
            .andb(R2, R0, R1)
            .write(0x2003, R2)

        .allocate("test_or")
            .orb(R2, R0, R1)
            .write(0x2004, R2)

        .allocate("test_xor")
            .xorb(R2, R0, R1)
            .write(0x2005, R2)


        # 3. COMPARE OPERATION


        .allocate("test_compare")
            # Store R0 BEFORE compare (not after)
            .let(R0, 0x0010)
            .let(R1, 0x0005)
            .write(0x2010, R0)         # Store R0 immediately
            .compare(R0, R1)

            # Compare equal
            .let(R0, 0x1234)
            .let(R1, 0x1234)
            .compare(R0, R1)

            .let(R2, 0x0000)
            .ifz("flag_zero_set")
            .jmp("flag_zero_clear")

        .allocate("flag_zero_set")
            .let(R2, 0x5555)
            .jmp("continue_compare")

        .allocate("flag_zero_clear")
            .let(R2, 0xAAAA)

        .allocate("continue_compare")
            .write(0x2011, R2)


        # 4. DATA MOVEMENT


        .allocate("test_ldi16")
            .let(R2, 0xDEAD)
            .write(0x2012, R2)

        .allocate("test_pass_b")
            .let(R2, 0x0000)           # Clear R2 first
            .let(R2, R1)               # Copy R1 to R2
            .write(0x2013, R2)


        # 5. INDIRECT ADDRESSING


        .allocate("test_indirect")
            .let(R0, 0x4000)
            .let(R1, 0xCAFE)
            .seti(R0, R1)
            .geti(R2, R0)
            .write(0x2014, R2)


        # 6. INCREMENT/DECREMENT


        .allocate("test_inc_dec")
            .let(R0, 0x0000)
            .inc(R0)
            .write(0x2015, R0)
            .inc(R0)
            .write(0x2016, R0)

            .let(R0, 0x0001)
            .dec(R0)
            .write(0x2017, R0)
            .dec(R0)
            .write(0x2018, R0)


        # 7. BIT OPERATIONS


        .allocate("test_bit_ops")
            .let(R0, 0x0000)
            .setbit(R0, 3)
            .write(0x2019, R0)
            .setbit(R0, 7)
            .write(0x201A, R0)
            .clrbit(R0, 3)
            .write(0x201B, R0)

            # testbit sets zero flag to 1 if bit is 0, 0 if bit is 1
            .testbit(R0, 7)            # bit 7 is set → zero flag = 0
            .let(R2, 0x0000)
            .ifz("bit_was_zero")       # Branch if zero flag = 1
            .jmp("bit_was_one")        # Fall through if zero flag = 0

        .allocate("bit_was_zero")
            .let(R2, 0x2222)
            .jmp("continue_bit")

        .allocate("bit_was_one")
            .let(R2, 0x1111)

        .allocate("continue_bit")
            .write(0x201C, R2)


        # 8. EXCHANGE AND SWAP


        .allocate("test_xchg")
            .let(R0, 0x1234)
            .let(R1, 0xABCD)
            .xchg(R0, R1)
            .write(0x201D, R0)
            .write(0x201E, R1)

        .allocate("test_swap")
            .let(R0, 0x1234)
            .swap(R0)
            .write(0x201F, R0)


        # 9. COMPLEX EXPRESSION


        .allocate("test_complex")
            .let(R0, 0x1234)
            .let(R1, 0x0F0F)
            .let(R2, 0x5678)
            .let(R3, 0x89AB)

            .add(R4, R0, R1)
            .orb(R5, R2, R3)
            .andb(R6, R4, R5)
            .write(0x2020, R6)


        # 10. OVERFLOW TEST - FIXED


        .allocate("test_overflow")
            # 0x7FFF + 1 = 0x8000 (overflow occurs in signed arithmetic)
            .let(R0, 0x7FFF)
            .let(R1, 0x0001)
            .add(R2, R0, R1)
            .write(0x2021, R2)

            .let(R2, 0x0000)
            .ifo("overflow_happened")
            .jmp("no_overflow")

        .allocate("overflow_happened")
            .let(R2, 0xFFFF)
            .jmp("continue_overflow")

        .allocate("no_overflow")
            .let(R2, 0x0000)

        .allocate("continue_overflow")
            .write(0x2022, R2)


        # 11. NEGATION


        .allocate("test_neg")
            .let(R0, 0x1234)
            .neg(R0)
            .write(0x2023, R0)
            .neg(R0)
            .write(0x2024, R0)


        # 12. TEST OPERATION


        .allocate("test_test")
            .let(R0, 0x1234)
            .let(R1, 0x0F0F)
            .test(R0, R1)              # 0x1234 & 0x0F0F = 0x0204 (nonzero)
            .write(0x2025, R0)         # R0 unchanged

            .let(R2, 0x0000)
            .ifz("test_zero")
            .jmp("test_nonzero")

        .allocate("test_zero")
            .let(R2, 0xAAAA)
            .jmp("continue_test")

        .allocate("test_nonzero")
            .let(R2, 0x5555)

        .allocate("continue_test")
            .write(0x2026, R2)


        # 13. SEQUENTIAL OPERATIONS


        .allocate("test_sequential")
            .let(R0, 0x1234)
            .let(R1, 0x5678)
            .let(R2, 0x9ABC)
            .let(R3, 0xDEF0)

            .add(R4, R0, R1)
            .andb(R5, R2, R3)
            .sub(R6, R4, R5)
            .write(0x2027, R6)


        # 14. CONDITIONAL EXECUTION

        .allocate("test_conditional")
            .let(R0, 0x0005)
            .let(R1, 0x0005)
            .compare(R0, R1)
            .let(R2, 0x1111)

            .ifz("equal_case")
            .jmp("not_equal_case")

        .allocate("equal_case")
            .let(R2, 0xFFFF)
            .jmp("end_conditional")

        .allocate("not_equal_case")
            .let(R2, 0x0000)

        .allocate("end_conditional")
            .write(0x2028, R2)

        .allocate("halt")
            .halt()
    )

    cpu.pc = prog.load()
    cycles = cpu.run(max_cycles=2000)
    print(f"Executed {cycles} cycles")

    # Read and verify results
    results = {}
    for addr in range(0x2000, 0x2029):
        results[addr] = cpu[addr]

    print(f"\nInstruction trace ({len(cpu.get_history())}):")
    for i, instr in enumerate(cpu.get_history()):
        print(f"  {i:2d}: {instr}")

    return cpu, results

def verify_results(results):
    expected = {
        0x2000: 0x2143,
        0x2001: 0x0325,
        0x2002: 0xFCDB,
        0x2003: 0x0204,
        0x2004: 0x1F3F,
        0x2005: 0x1D3B,
        0x2010: 0x0010,
        0x2011: 0x5555,
        0x2012: 0xDEAD,
        0x2013: 0x1234, # (0x0F0F wrong)
        0x2014: 0xCAFE,
        0x2015: 0x0001,
        0x2016: 0x0002,
        0x2017: 0x0000,
        0x2018: 0xFFFF,
        0x2019: 0x0008,
        0x201A: 0x0088,
        0x201B: 0x0080,
        0x201C: 0x1111,
        0x201D: 0xABCD,
        0x201E: 0x1234,
        0x201F: 0x3412,
        0x2020: 0x0143,
        0x2021: 0x8000,
        0x2022: 0xFFFF,
        0x2023: 0xEDCC,
        0x2024: 0x1234,
        0x2025: 0x1234,
        0x2026: 0x5555,
        0x2027: 0xCDFC,
        0x2028: 0xFFFF,
    }

    print("\nVerification:")
    print("=" * 60)
    all_passed = True

    for addr, expected_value in expected.items():
        actual = results.get(addr)
        if actual is None:
            print(f"? Result[0x{addr:04X}]: Not found")
            all_passed = False
        else:
            status = "OK!" if actual == expected_value else "*FAILED*"
            if actual != expected_value:
                all_passed = False
            print(f"{status} Result[0x{addr:04X}]: 0x{actual:04X} (expected 0x{expected_value:04X})")

    if all_passed:
        print("\nPassed!")
    else:
        print("\nFailed!")

    return all_passed

if __name__ == "__main__":
    cpu, results = test_alu_operations()
    verify_results(results)
