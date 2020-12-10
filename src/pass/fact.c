#include <stdio.h>
#include <stdlib.h>

unsigned int fact (unsigned int n) {
  int i;
  int f = 1;
  for (i=2; i<=n; i++) {
    f *= i;
  }
  return f;
}

int main () {
  int n;
  printf("? ");
  scanf("%i", &n);
  printf("%i\n", fact(n));
}
