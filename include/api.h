// api.h

/*
 * Concept API for Pythonic control
 *

 * Pseudo models:

    # binding.py
    import ctypes

    # 1. Load the compiled C library
    lib = ctypes.CDLL('./bc.so')

    # 2. Mirror the C 'bit' type (assuming it's 1 byte in C)
    class Bit(ctypes.c_uint8):
        pass

    # 3. Mirror the C Struct exactly
    class Machine(ctypes.Structure):
        _fields_ = [
            ("pc", ctypes.c_uint16),
            ("registers", ctypes.c_uint16 * 8),
            ("alu_wires", Bit * 64),
            ("bus_lines", Bit * 16),
            ("memory", Bit * (65536 * 16)),
            ("cycle_count", ctypes.c_uint64),
            ("halted", ctypes.c_uint8),
        ]

    # 4. Tell Python the exact C function signatures (Argument types and Return types)
    lib.machine_init.argtypes = [ctypes.POINTER(Machine)]
    lib.machine_run.argtypes = [ctypes.POINTER(Machine), ctypes.c_int]
    # ...if more wanted...

    # ----

    #  machine.py
    from binding import lib, Machine

    class CPU:
        def __init__(self):
            # Python allocates the memory for the C struct
            self._state = Machine()
            # Pass a pointer to C to initialize it
            lib.machine_init(ctypes.byref(self._state))

        def load(self, program_hex_list):
            # Convert Python list of ints to a C array of uint16_t
            c_array = (ctypes.c_uint16 * len(program_hex_list))(*program_hex_list)
            lib.machine_load(ctypes.byref(self._state), c_array, len(program_hex_list))

        def run(self, max_cycles=1000):
            # Tell C to run the engine. C mutates self._state directly in memory.
            lib.machine_run(ctypes.byref(self._state), max_cycles)

            # Return a snapshot/result object for inspection
            return Snapshot(self._state)

        # --- Todo: Inspection tools ---

        @property
        def pc(self):
            return self._state.pc

        @property
        def registers(self):
            # Convert C array to Python list for easy reading
            return list(self._state.registers)

        def peek_wire(self, wire_name):
            # Example of gate-level inspection
            if wire_name == "ALU_CARRY_OUT":
                return bool(self._state.alu_wires[12]) # 12 is just an example index
            # ... map other wire names to array indices ...


    class Snapshot:
        """A frozen view of the CPU state after a run()"""
        def __init__(self, c_state):
            self.cycles = c_state.cycle_count
            self.halted = bool(c_state.halted)
            self.pc = c_state.pc
            self.registers = list(c_state.registers)

        def __repr__(self):
            return f"<Snapshot cycles={self.cycles} pc=0x{self.pc:04X}>"

*/

// 1. State Struct ("Dashboard")
// Python needs to know the exact byte-size of this.
typedef struct {
    uint16_t pc;
    uint16_t registers[8];

    // Because you want gate-level fidelity, you expose the raw wires.
    // Assuming 'bit' is a 1-byte type (like uint8_t) in your C code:
    bit alu_wires[64];
    bit bus_lines[16];
    bit memory[65536 * 16]; // 64k words of 16 bits

    uint64_t cycle_count;
    uint8_t halted;
} Machine;

// 2. API Functions
// We pass POINTERS to the state. We do not copy the struct.
void machine_init(Machine* state);
void machine_load(Machine* state, uint16_t* program, int length);
void machine_run(Machine* state, int max_cycles);
void machine_reset(Machine* state);
