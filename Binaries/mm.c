#include <stdio.h>
#include <stdlib.h>

#define N 512   // matrix size (adjust as needed)

double A[N][N], B[N][N], C[N][N];

int main() {
    // Initialize matrices
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            A[i][j] = (i + j) % 100;
            B[i][j] = (i - j) % 100;
            C[i][j] = 0.0;
        }
    }

    // Simple matrix multiplication: C = A * B
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            double sum = 0.0;
            for (int k = 0; k < N; k++) {
                sum += A[i][k] * B[k][j];
            }
            C[i][j] = sum;
        }
    }

    // Print one element to avoid optimization
    printf("C[0][0] = %f\n", C[0][0]);
    return 0;
}
