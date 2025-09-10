#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define N 100000000

int main() {
    int count = 0;
    srand(42); // fixed seed for reproducibility

    for (int i = 0; i < N; i++) {
        int x = rand() % 100;
        if (x < 50) {
            count++;
        } else {
            count--;
        }
    }

    printf("Final count = %d\n", count);
    return 0;
}
