#include <stdio.h>

int main () {
  int n, f;
  scanf("%i", &n);
  for (int i=1; i<n; i++) {
    f *= i;
  }
  printf("%i\n", f);
}
