// This is our own fixture, not an Adobe symbol or reverse-engineered implementation.
static volatile int fixture_total = 0;
extern "C" __attribute__((noinline)) void fstr_fixture_notification(int value) {
    fixture_total = fixture_total + value;
}
int main() {
    for (int i = 1; i <= 3; ++i) fstr_fixture_notification(i);
    return fixture_total == 6 ? 0 : 1;
}
