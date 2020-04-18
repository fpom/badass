#include "fact.c"
#include <assert.h>

int main () {
  assert(fact(0) == 1);
  assert(fact(1) == 1);
  assert(fact(5) == 120);
}
