// Small, dependency-free P6 loader for *static* FrameDepth desktop snapshots.
// This never decodes untrusted compressed image formats or captures a screen.
// Keep image dimensions bounded: stereo output buffers are twice as wide.
// Header-only so the parser can be regression-tested outside Steam Frame.
#pragma once

#include <charconv>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <istream>
#include <string>
#include <vector>

namespace ft_stereo_image {

constexpr int kMaxWidth = 2048;
constexpr int kMaxHeight = 1152;
constexpr int kMaxPixels = kMaxWidth * kMaxHeight;

struct Image {
    int width = 0;
    int height = 0;
    std::vector<uint8_t> rgb;  // P6, 8-bit RGB, tightly packed
};

inline std::string Token(std::istream &in) {
    std::string value;
    while (true) {
        const int c = in.peek();
        if (c == EOF) return {};
        if (c == '#') {
            std::string comment;
            std::getline(in, comment);
        } else if (std::isspace(static_cast<unsigned char>(c))) {
            in.get();
        } else {
            break;
        }
    }
    while (true) {
        const int c = in.peek();
        if (c == EOF || std::isspace(static_cast<unsigned char>(c))) break;
        if (value.size() >= 32) return {};
        value.push_back(char(in.get()));
    }
    // Consume one delimiter, not arbitrary whitespace: the first binary pixel
    // is allowed to begin with a space, a newline or a '#' byte.
    const int delimiter = in.get();
    if (delimiter == '\r' && in.peek() == '\n') in.get();
    return value;
}

inline bool Integer(const std::string &text, int &out) {
    if (text.empty()) return false;
    const char *first = text.data(), *last = first + text.size();
    const auto result = std::from_chars(first, last, out);
    return result.ec == std::errc{} && result.ptr == last;
}

inline bool Read(std::istream &in, Image &out, std::string &error) {
    Image image;
    if (Token(in) != "P6") {
        error = "expected binary P6 PPM (convert screenshots with ImageMagick)";
        return false;
    }
    const std::string sw = Token(in), sh = Token(in), sm = Token(in);
    int max = 0;
    if (!Integer(sw, image.width) || !Integer(sh, image.height) ||
        !Integer(sm, max) || max != 255 ||
        image.width < 1 || image.height < 1 ||
        image.width > kMaxWidth || image.height > kMaxHeight ||
        int64_t(image.width) * image.height > kMaxPixels) {
        error = "invalid PPM dimensions or maxval; use at most 2048x1152, 8-bit P6";
        return false;
    }
    image.rgb.resize(size_t(image.width) * size_t(image.height) * 3);
    in.read(reinterpret_cast<char *>(image.rgb.data()), std::streamsize(image.rgb.size()));
    if (in.gcount() != std::streamsize(image.rgb.size())) {
        error = "truncated PPM pixel data";
        return false;
    }
    out = std::move(image);
    error.clear();
    return true;
}

inline bool Load(const std::string &filename, Image &out, std::string &error) {
    std::ifstream in(filename, std::ios::binary);
    if (!in) {
        error = "could not open " + filename;
        return false;
    }
    return Read(in, out, error);
}

}  // namespace ft_stereo_image
