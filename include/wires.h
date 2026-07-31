/* wires.h
 * Named indices into machine.alu_wires[64] */

#define WIRE_RESULT_BASE   0   /* [0..15]  final result[i], post-mux */
#define WIRE_CARRY_BASE   16   /* [16..31] carry_out of full_adder at stage i (ripple) */
#define WIRE_CONTROL_BASE 32   /* [32..35] c0..c3 */
#define WIRE_ZERO         36
#define WIRE_CARRY_FLAG   37
#define WIRE_OVERFLOW     38

/* [39..63] reserved for now*/
