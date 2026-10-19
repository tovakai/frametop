// Experimental per-screen stereoscopic preview parameters.
// This is a generic compositor capability, not a depth inference engine.
// No SteamVR/GPU dependencies, so validation can be exercised offline.
#pragma once

#include <cmath>

namespace ft_stereo {

constexpr double kMaxStrength = 0.03;  // maximum UV-width disparity parameter

struct Preview {
    float strength = 0.0f;     // 0 disables the effect
    float convergence = 0.5f;  // neutral brightness/depth plane, 0..1
    bool swap = false;
};

inline bool valid(double strength, double convergence, int swap) {
    return std::isfinite(strength) && std::isfinite(convergence) &&
           strength >= 0.0 && strength <= kMaxStrength &&
           convergence >= 0.0 && convergence <= 1.0 && (swap == 0 || swap == 1);
}

inline bool enabled(const Preview &p) { return p.strength > 0.0f; }

inline bool same(const Preview &a, const Preview &b) {
    return a.strength == b.strength && a.convergence == b.convergence && a.swap == b.swap;
}

}  // namespace ft_stereo
