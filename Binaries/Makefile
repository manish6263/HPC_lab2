CC = gcc
OPTIONS = -static -static-libgcc -O2
LDFLAGS = -lm

# Executables
TARGETS = mm branchy_test fft.1

all: $(TARGETS)

# Rules to build each workload
mm.1: mm.c
	$(CC) -o $@ $^ $(OPTIONS) $(LDFLAGS)

branchy_test.1: branchy_test.c
	$(CC) -o $@ $^ $(OPTIONS)

fft.1: fft.c
	$(CC) -o $@ $^ $(OPTIONS) $(LDFLAGS)

clean:
	rm -rf fft.1 mm branchy_test
