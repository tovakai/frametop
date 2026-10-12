// Pure pose/opacity interpolation for the external extension control API.
// No OpenVR dependency: the tests run on a normal C++17 toolchain.
#pragma once

#include <algorithm>
#include <cmath>

namespace ft_extension {

inline double ease(double phase) {
    const double t = std::clamp(phase, 0.0, 1.0);
    return 0.5 - 0.5 * std::cos(3.14159265358979323846 * t);
}

inline float fade(float start, float end, double phase) {
    return float(start + (end - start) * ease(phase));
}

struct Quat {
    double w, x, y, z;
};

template <typename Mat>
Quat quaternion(const Mat &m) {
    const double trace = double(m.m[0][0]) + m.m[1][1] + m.m[2][2];
    Quat q{};
    if (trace > 0) {
        const double s = std::sqrt(trace + 1.0) * 2.0;
        q = {0.25 * s, (m.m[2][1] - m.m[1][2]) / s,
             (m.m[0][2] - m.m[2][0]) / s, (m.m[1][0] - m.m[0][1]) / s};
    } else if (m.m[0][0] > m.m[1][1] && m.m[0][0] > m.m[2][2]) {
        const double s = std::sqrt(1.0 + m.m[0][0] - m.m[1][1] - m.m[2][2]) * 2.0;
        q = {(m.m[2][1] - m.m[1][2]) / s, 0.25 * s,
             (m.m[0][1] + m.m[1][0]) / s, (m.m[0][2] + m.m[2][0]) / s};
    } else if (m.m[1][1] > m.m[2][2]) {
        const double s = std::sqrt(1.0 + m.m[1][1] - m.m[0][0] - m.m[2][2]) * 2.0;
        q = {(m.m[0][2] - m.m[2][0]) / s, (m.m[0][1] + m.m[1][0]) / s,
             0.25 * s, (m.m[1][2] + m.m[2][1]) / s};
    } else {
        const double s = std::sqrt(1.0 + m.m[2][2] - m.m[0][0] - m.m[1][1]) * 2.0;
        q = {(m.m[1][0] - m.m[0][1]) / s, (m.m[0][2] + m.m[2][0]) / s,
             (m.m[1][2] + m.m[2][1]) / s, 0.25 * s};
    }
    const double norm = std::sqrt(q.w * q.w + q.x * q.x + q.y * q.y + q.z * q.z);
    return {q.w / norm, q.x / norm, q.y / norm, q.z / norm};
}

inline Quat slerp(Quat a, Quat b, double t) {
    double dot = a.w*b.w + a.x*b.x + a.y*b.y + a.z*b.z;
    if (dot < 0) {
        b = {-b.w, -b.x, -b.y, -b.z};
        dot = -dot;
    }
    double wa = 1 - t, wb = t;
    if (dot < 0.9995) {
        const double theta = std::acos(std::clamp(dot, -1.0, 1.0));
        const double denom = std::sin(theta);
        wa = std::sin((1.0 - t) * theta) / denom;
        wb = std::sin(t * theta) / denom;
    }
    Quat out{wa*a.w + wb*b.w, wa*a.x + wb*b.x, wa*a.y + wb*b.y, wa*a.z + wb*b.z};
    const double norm = std::sqrt(out.w*out.w + out.x*out.x + out.y*out.y + out.z*out.z);
    return {out.w / norm, out.x / norm, out.y / norm, out.z / norm};
}

// Interpolate a rigid 3x4 matrix; quaternion rotation keeps panels orthonormal
// and takes the shortest arc, including when yaw crosses 180/-180 degrees.
template <typename Mat>
Mat pose(const Mat &a, const Mat &b, double phase) {
    if (phase <= 0) return a;
    if (phase >= 1) return b;
    const double t = ease(phase);
    const Quat q = slerp(quaternion(a), quaternion(b), t);
    const double xx = q.x*q.x, yy = q.y*q.y, zz = q.z*q.z;
    const double xy = q.x*q.y, xz = q.x*q.z, yz = q.y*q.z;
    const double wx = q.w*q.x, wy = q.w*q.y, wz = q.w*q.z;
    Mat out{};
    out.m[0][0] = float(1 - 2*(yy+zz));
    out.m[0][1] = float(2*(xy-wz));
    out.m[0][2] = float(2*(xz+wy));
    out.m[1][0] = float(2*(xy+wz));
    out.m[1][1] = float(1 - 2*(xx+zz));
    out.m[1][2] = float(2*(yz-wx));
    out.m[2][0] = float(2*(xz-wy));
    out.m[2][1] = float(2*(yz+wx));
    out.m[2][2] = float(1 - 2*(xx+yy));
    for (int i=0;i<3;++i) out.m[i][3] = float(a.m[i][3] + (b.m[i][3]-a.m[i][3])*t);
    return out;
}

}  // namespace ft_extension
