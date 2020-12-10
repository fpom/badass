#include "fact.h"
#include <stdio.h>
#include <stdlib.h>

int main (int argc, char** argv) {
  int i, n;
  char* s = malloc(10);
  for (i=0; i<=10; i++) {
    s[i] = 0;
  }
  printf("Bonjour !\n");
  printf("Quelle est votre nombre ? ");
  scanf("%i", &n);
  printf("Le rÃ©sultat est : %i\n", fact(n));
  printf("Bye bye!\n");
}
