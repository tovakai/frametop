#include "../stereo-preview.h"
#include <cassert>
#include <limits>

int main() {
    using namespace ft_stereo;
    Preview off{};
    assert(!enabled(off));
    assert(valid(0, 0.5, 0));
    assert(valid(kMaxStrength, 1, 1));
    assert(!valid(kMaxStrength + 0.001, 0.5, 0));
    assert(!valid(-0.001, 0.5, 0));
    assert(!valid(0.01, -0.01, 0));
    assert(!valid(0.01, 1.01, 0));
    assert(!valid(0.01, 0.5, 2));
    assert(!valid(std::numeric_limits<double>::quiet_NaN(), 0.5, 0));
    assert(!valid(0.01, std::numeric_limits<double>::infinity(), 0));
    Preview left{0.01f, 0.5f, false};
    assert(enabled(left));
    assert(!same(off, left));
    assert(same(left, left));
    assert(!same(left, Preview{0.01f, 0.5f, true}));
    assert(!same(left, Preview{0.02f, 0.5f, false}));
    assert(!same(left, Preview{0.01f, 0.6f, false}));
}
