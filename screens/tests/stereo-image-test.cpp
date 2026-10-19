#include "../stereo-image.h"

#include <cassert>
#include <sstream>
#include <string>

namespace {
bool Parse(const std::string &data, ft_stereo_image::Image &image, std::string &error) {
    std::istringstream in(data, std::ios::binary);
    return ft_stereo_image::Read(in, image, error);
}
}

int main() {
    using namespace ft_stereo_image;
    Image image;
    std::string error;
    // A leading newline, space and '#' can be literal RGB pixel values.
    const std::string rgb("\x0a\x20\x23\x00\xff\x80", 6);
    assert(Parse("P6\n# generated on Frame\n2 1\n255\n" + rgb, image, error));
    assert(image.width == 2 && image.height == 1);
    assert(std::string(image.rgb.begin(), image.rgb.end()) == rgb);
    assert(Parse("P6\r\n2 1\r\n255\r\n" + rgb, image, error));
    assert(std::string(image.rgb.begin(), image.rgb.end()) == rgb);
    assert(!Parse("P3\n2 1\n255\n" + rgb, image, error));
    assert(!Parse("P6\n2 1\n65535\n" + rgb, image, error));
    assert(!Parse("P6\n2049 1\n255\n" + rgb, image, error));
    assert(!Parse("P6\n2 1153\n255\n" + rgb, image, error));
    assert(!Parse("P6\n9999999999999 2\n255\n" + rgb, image, error));
    assert(!Parse("P6\n2 1\n255\n" + rgb.substr(0, 5), image, error));
    assert(!Parse("P6\n0 1\n255\n" + rgb, image, error));
    assert(!Parse("P6\n2 1\n255\n", image, error));
    // Comments and arbitrary regular whitespace between header tokens.
    assert(Parse("P6 \n# comment\n2\t1\n255\n" + rgb, image, error));
    assert(image.rgb[0] == '\n');
}
