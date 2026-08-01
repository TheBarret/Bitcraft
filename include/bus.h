#ifndef BUS_H
#define BUS_H

#include <stdint.h>
#include <stddef.h>
#include "alu.h"

/*
 Memory array (256 words)
     │
     ├─ addr_a  ──→ uint16_to_bits() ──→ bit[] A ──┐
     ├─ addr_b  ──→ uint16_to_bits() ──→ bit[] B ──┤
     │                                         alu_forward() ──→ bit[] result ──→ bits_to_uint16() ──→ memory[addr_dest]
     └─ addr_dest ←────────────────────────────────────────────────────────────────────────────────────────────────┘

     changelog: 0,1
     - initial prototype

     changelog: 0.2
     - changed from uint8_t to uint16_t on all interfaces

     changelog: 0.3
     - added bus_load_program() function
 */

#define MEMORY_SIZE 65536    // 16bit
#define NUM_REGISTERS 8      // R0-R7 occupy addresses 0-7
#define PROGRAM_START 512    // General RAM

/*
 * Bus control flags set by the controller,
 * read back to determine conditional branching.
 */
typedef struct {
    bit zero;
    bit carry;
    bit overflow;
} bus_flags;

/*
 * The system bus.
 * memory[0..7] are R0-R7.
 * memory[8..255] are general-purpose RAM.
 * The ALU reads from addr_a and addr_b,
 * writes result to addr_dest,
 * and updates flags after each operation.
 */
typedef struct {
    uint16_t memory[MEMORY_SIZE];
    uint16_t  addr_a;
    uint16_t  addr_b;
    uint16_t  addr_dest;
    bus_flags flags;
} Bus;

/*
 * Initialize the bus.
 * Zeros all memory and flags.
  */
void bus_init(Bus* bus);

/*
 * Write an immediate value directly to a memory address.
 * Returns 1 on success, 0 if address is out of range.
 */
int bus_write(Bus* bus, uint16_t addr, uint16_t value);

/*
 * Read a value from a memory address.
 * Returns the value (0 if address out of range).
 */
uint16_t bus_read(const Bus* bus, uint16_t addr);

/*
 * Execute an ALU operation:
 *   memory[addr_dest] = memory[addr_a] OP memory[addr_b]
 * where OP is selected by the 4-bit control word.
 *
 * The caller must set bus->addr_a, bus->addr_b, bus->addr_dest,
 * and pass the control bits before calling.
 *
 * Flags are updated to reflect the result.
 *
 * Returns 1 on success, 0 on error
 * (bad address, bad control word decode, internal ALU error).
 */
int bus_execute(Bus* bus, const bit control[4]);

/*
 * Convenience: set addr_a, addr_b, addr_dest in one call,
 * then immediately execute.
 */
int bus_alu_op(Bus* bus, uint16_t addr_a, uint16_t addr_b, uint16_t addr_dest, const bit control[4]);

/*
 * Load a 16-bit immediate into a memory address.
 * This is NOT an ALU operation—no flags are modified.
 * Equivalent to bus_write().
 */
int bus_load_immediate(Bus* bus, uint16_t addr, uint16_t value);

/*
 * Dump a range of memory for debugging.
 * Prints addresses and values in hex.
 */
void bus_dump(const Bus* bus, uint16_t start, uint16_t end);

/*
 * Load a program (array of pre-assembled 16-bit words) starting at PROGRAM_START.
 * Does not touch registers 0-7 or any reserved range.
 * Returns 1 on success, 0 if the program doesn't fit in memory
 * (count > MEMORY_SIZE - PROGRAM_START), or on any out-of-range write.
 */
int bus_load_program(Bus* bus, const uint16_t* words, size_t count);

#endif
