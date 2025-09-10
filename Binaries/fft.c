#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define N 1024   // FFT size (must be power of 2)
#define PI 3.14159265358979323846

typedef struct {
    double re, im;
} complex_t;

void fft(complex_t *a, int n) {
    if (n <= 1) return;

    // Divide
    complex_t *even = malloc(n/2 * sizeof(complex_t));
    complex_t *odd  = malloc(n/2 * sizeof(complex_t));
    for (int i = 0; i < n/2; i++) {
        even[i] = a[i*2];
        odd[i]  = a[i*2 + 1];
    }

    // Conquer
    fft(even, n/2);
    fft(odd, n/2);

    // Combine
    for (int k = 0; k < n/2; k++) {
        double t = -2 * PI * k / n;
        complex_t wk = {cos(t), sin(t)};
        complex_t oddk = {wk.re * odd[k].re - wk.im * odd[k].im,
                          wk.re * odd[k].im + wk.im * odd[k].re};
        a[k].re       = even[k].re + oddk.re;
        a[k].im       = even[k].im + oddk.im;
        a[k + n/2].re = even[k].re - oddk.re;
        a[k + n/2].im = even[k].im - oddk.im;
    }

    free(even);
    free(odd);
}

int main() {
    complex_t *a = malloc(N * sizeof(complex_t));

    // Initialize input
    for (int i = 0; i < N; i++) {
        a[i].re = cos(2 * PI * i / N);
        a[i].im = sin(2 * PI * i / N);
    }

    // Run FFT
    fft(a, N);

    // Print one value
    printf("FFT[0] = %f + %fi\n", a[0].re, a[0].im);

    free(a);
    return 0;
}
