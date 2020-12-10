int fact (int n) {
  int i;
  int f = 1;
  for (i=2; i<=n; i++) {
    f *= i;
  }
  return f;
}

int fact_rec (int n) {
  if (n <= 0) {
    return 1;
  } else {
    return n*fact_rec(n-1);
  }
}
