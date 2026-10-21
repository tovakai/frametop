#include "../extension-motion.h"
#include <cassert>
#include <cmath>

struct Mat { float m[3][4]; };
Mat rotation(double degrees) {
    const double angle = degrees * 3.14159265358979323846 / 180;
    Mat m{};
    m.m[0][0] = float(std::cos(angle));
    m.m[0][2] = float(std::sin(angle));
    m.m[1][1] = 1;
    m.m[2][0] = float(-std::sin(angle));
    m.m[2][2] = float(std::cos(angle));
    return m;
}
bool near(double a, double b, double tolerance = 0.0001) {
    return std::fabs(a - b) < tolerance;
}
int main() {
    assert(near(ft_extension::ease(-1), 0));
    assert(near(ft_extension::ease(0), 0));
    assert(near(ft_extension::ease(.5), .5));
    assert(near(ft_extension::ease(1), 1));
    assert(near(ft_extension::ease(2), 1));
    assert(near(ft_extension::fade(.3f, .9f, .5), .6));
    const Mat a = rotation(0), b = rotation(90);
    Mat start = ft_extension::pose(a, b, 0);
    Mat halfway = ft_extension::pose(a, b, .5);
    Mat end = ft_extension::pose(a, b, 1);
    assert(near(start.m[0][0], 1));
    assert(near(end.m[0][0], 0));
    assert(near(halfway.m[0][0], std::sqrt(.5)));
    assert(near(halfway.m[0][2], std::sqrt(.5)));
    // A 180/-180 boundary must travel the short way, not rotate back through zero.
    Mat wrap = ft_extension::pose(rotation(179), rotation(-179), .5);
    assert(wrap.m[0][0] < -.999f);
    // Easing moves translation smoothly; no distortion of the rotation axes.
    Mat translated = rotation(90);
    translated.m[0][3] = 4;
    translated.m[1][3] = -2;
    Mat middle = ft_extension::pose(a, translated, .5);
    assert(near(middle.m[0][3], 2));
    assert(near(middle.m[1][3], -1));
    double length = 0, dot = 0;
    for (int i = 0; i < 3; ++i) {
        length += middle.m[i][0] * middle.m[i][0];
        dot += middle.m[i][0] * middle.m[i][1];
    }
    assert(near(length, 1));
    assert(near(dot, 0));
}
