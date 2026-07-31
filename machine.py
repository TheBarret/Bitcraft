import sys
import struct
from binding import Machine

def run_tests():
    try:
        machine = Machine()
    except FileNotFoundError as e:
        print(f"[!] Error: {e}")
        sys.exit(1)

    # reset machine
    machine.reset()

    # assign registers
    machine.set_register(1, 42)
    machine.set_register(2, 16)

    # load program
    program = [
        0x0312,  # R3 = R1 + R2  (0x002A + 0x0010 = 0x003A / 58 decimal)
        0xF000   # Halt placeholder *Todo*
    ]
    bin = bytearray(struct.pack(f">{len(program)}H", *program))
    print(f"executing {bin.hex()}...")
    load_success = machine.load_program(program)

    # execute
    cycles = machine.run(max_cycles=5)

    # test results
    r3_result = machine.get_register(3)
    z, c, o = machine.flgs

    print(f"Finished ({cycles} cycles, flags: zero={z}, carry={c}, overflow={o})")
    print(f"-> 42 + 16: expected=58, r3={r3_result}, is_valid={r3_result==58}")
    #machine.dump(0, 5)

if __name__ == "__main__":
    run_tests()
