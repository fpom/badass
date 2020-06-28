//let fact = randname()
//let n = randname()
unsigned long long int fact (int n) {
  //shuffle
  //let f = randname()
  unsigned long long int f = 1;
  //let i = randname()
  int i;
  //end shuffle
  for (i=2; i<=n; i++) {
    f *= i;
  }
  return f;
}
