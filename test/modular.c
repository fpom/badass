#include <stdio.h>

unsigned int fact (int n) {
  if (n <= 1) {
    return 1;
  } else {
    return n * fact(n-1);
  }
}

int max (int a, int b) {
  if (a < b) {
    return b;
  } else {
    return a;
  }
}

char c[4] = {0, 0, 0, 0};

int min (int a, int b) {
  if (a > b) {
    return b;
  } else {
    return a;
  }
}

int main () {
  printf("fact(5) = %i\n", fact(5));
  printf("max(4, 2) = %i\n", max(4, 2));
  printf("min(4, 2) = %i\n", min(4, 2));
}
