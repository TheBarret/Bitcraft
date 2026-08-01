#ifndef BUS_H
#define BUS_H

#include <stdint.h>
#include <stddef.h>
#include "alu.h"

/*
 Memory array (65536 words / 128 KB)
     │
     ├─ addr_a  ──→ uint16_to_bits() ──→ bit[] A ──┐
     ├─ addr_b  ──→ uint16_to_bits() ──→ bit[] B ──┤
     │                                         alu_forward() ──→ bit[] result ──→ bits_to_uint16() ──→ memory[addr_dest]
     └─ addr_dest ←────────────────────────────────────────────────────────────────────────────────────────────────┘

     changelog: 0.1 - initial prototype
     changelog: 0.2 - changed from uint8_t to uint16_t on all interfaces
     changelog: 0.3 - added bus_load_program() function
 */

#define MEMORY_SIZE 65536    // *hardcoded* 64K mempry
#define NUM_REGISTERS 8      // *hardcoded* R0-R7; addresses 0-7
#define PROGRAM_START 512    // *hardcoded* Magic number; all programs start at 0x0200

typedef struct {
    bit zero;
    bit carry;
    bit overflow;
} bus_flags;

typedef struct {
    uint16_t memory[MEMORY_SIZE];
    uint16_t  addr_a;
    uint16_t  addr_b;
    uint16_t  addr_dest;
    bus_flags flags;
} Bus;

void bus_init(Bus* bus);
int bus_write(Bus* bus, uint16_t addr, uint16_t value);
uint16_t bus_read(const Bus* bus, uint16_t addr);
int bus_execute(Bus* bus, const bit control[4]);
int bus_alu_op(Bus* bus, uint16_t addr_a, uint16_t addr_b, uint16_t addr_dest, const bit control[4]);
int bus_load_immediate(Bus* bus, uint16_t addr, uint16_t value);
void bus_dump(const Bus* bus, uint16_t start, uint16_t end);
int bus_load_program(Bus* bus, const uint16_t* words, size_t count);

#endif
