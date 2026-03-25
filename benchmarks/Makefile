CC      = gcc
CFLAGS  = -O1 -march=x86-64 -g -std=c11
BIN_DIR = bin

.PHONY: all dirs clean \
        matrix_mul \
        ptr_chase_seq ptr_chase_shuffle

all: dirs \
     $(BIN_DIR)/matrix_mul \
     $(BIN_DIR)/ptr_chase_seq \
     $(BIN_DIR)/ptr_chase_shuffle

dirs:
	mkdir -p $(BIN_DIR)

$(BIN_DIR)/matrix_mul: matrix_mul.c
	$(CC) $(CFLAGS) -o $@ matrix_mul.c -lm

$(BIN_DIR)/ptr_chase_seq: ptr_chase.c common.h
	$(CC) $(CFLAGS) -DCHAIN_MODE=0 -o $@ ptr_chase.c

$(BIN_DIR)/ptr_chase_shuffle: ptr_chase.c common.h
	$(CC) $(CFLAGS) -DCHAIN_MODE=1 -o $@ ptr_chase.c

matrix_mul:        dirs $(BIN_DIR)/matrix_mul
ptr_chase_seq:     dirs $(BIN_DIR)/ptr_chase_seq
ptr_chase_shuffle: dirs $(BIN_DIR)/ptr_chase_shuffle

clean:
	rm -rf $(BIN_DIR)
