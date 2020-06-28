#include <stdio.h>
//skip
#define LEN 6
#define DATA {0, 1, 2, 3, 4, 5}
//end skip

//include test-fact.c

int main (int argc, char** argv) {
  //let tab = randname()
  //let LEN = randint(10, 20)
  //let DATA = randint(0, 20, LEN, unique=True)
  //let p = randname()
  //shuffle
  int tab[] = DATA;
  int p;
  //end shuffle
  for (p=0; p<LEN; ++p) {
    printf("%i! = %llu\n", tab[p], fact(tab[p]));
  }
}
