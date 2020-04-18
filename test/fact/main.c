unsigned int fact (unsigned int);

#include "fact.c"

#include "badass.h"

int main () {
  unsigned int __FACT[50];
  __FACT[0] = __FACT[1] = 1;
  for (int n=2; n<50; n++) {
    __FACT[n] = n * __FACT[n-1];
  }
  assopen("run.ass");
  assess(n=0, fact(0) == __FACT[0]);
  assess(n=1, fact(1) == __FACT[1]);
  assess(n=2, fact(2) == __FACT[2]);
  assess(n=3, fact(3) == __FACT[3]);
  assess(n=4, fact(4) == __FACT[4]);
  assess(n=5, fact(5) == __FACT[5]);
  assess(n=6, fact(6) == __FACT[6]);
  assess(n=7, fact(7) == __FACT[7]);
  assess(n=8, fact(8) == __FACT[8]);
  assess(n=9, fact(9) == __FACT[9]);
  assess(n=10, fact(10) == __FACT[10]);
  assess(n=20, fact(20) == __FACT[20]);
  assess(n=30, fact(30) == __FACT[30]);
  assess(n=40, fact(40) == __FACT[40]);
}
