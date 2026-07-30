#!/bin/bash
set -e

SRC_DIR="."
BUILD_DIR="./build"
mkdir -p "$BUILD_DIR"
rm -rf "$BUILD_DIR/*"

# switch: -DNDEBUG
CFLAGS="-O3 -march=native -Wall -Wextra -std=c11"
LDFLAGS="-lm"

echo "Building framework..."
gcc $CFLAGS -c "$SRC_DIR/bit.c" -o "$BUILD_DIR/bit.o"
gcc $CFLAGS -c "$SRC_DIR/gates.c" -o "$BUILD_DIR/gates.o"
gcc $CFLAGS -c "$SRC_DIR/adder.c" -o "$BUILD_DIR/adder.o"
gcc $CFLAGS -c "$SRC_DIR/mux.c" -o "$BUILD_DIR/mux.o"
gcc $CFLAGS -c "$SRC_DIR/alu.c" -o "$BUILD_DIR/alu.o"
gcc $CFLAGS -c "$SRC_DIR/bus.c" -o "$BUILD_DIR/bus.o"

echo "Finalizing..."
gcc $CFLAGS -c "$SRC_DIR/main.c" -o "$BUILD_DIR/main.o"
gcc $CFLAGS "$BUILD_DIR/bit.o" "$BUILD_DIR/gates.o" "$BUILD_DIR/adder.o" "$BUILD_DIR/mux.o" "$BUILD_DIR/alu.o" "$BUILD_DIR/bus.o" "$BUILD_DIR/main.o" -o "$BUILD_DIR/bc" $LDFLAGS

echo "Finished! ($BUILD_DIR/bc)"
