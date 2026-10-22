#!/usr/bin/env bash
# Build Aquamarine v0.15.1 plus the configure-ack fix into this tree's build/aquamarine.
# Does not replace the container's COPR package and does not enable a repository.
# Run on the Frame, inside the experimental checkout (not the installed one).
set -euo pipefail
here=$(dirname "$(readlink -f "$0")")
root=$(readlink -f "$here/..")

if [ "${1:-}" != --inner ]; then
  if (( $# != 0 )); then
    echo "Usage: $0" >&2
    exit 2
  fi
  exec "$root/scripts/in-box" "$0" --inner
fi

tag=v0.15.1
sha=2f9de98c0bd1b7b1b09c576e390a2fef436449762fb334163c414f0c300296f2
patch=$here/patches/aquamarine-0.15.1-configure-ack.patch
prefix=$root/build/aquamarine
src_root=$root/build/src
tarball=$src_root/aquamarine-$tag.tar.gz
extracted=$src_root/aquamarine-${tag#v}
stamp=$prefix/.frametop-stamp
patch_id=$(sha256sum "$patch" | awk '{print $1}')
want="$tag $sha $patch_id"

if [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$want" ] &&
   { [ -e "$prefix/lib64/libaquamarine.so.14" ] || [ -e "$prefix/lib/libaquamarine.so.14" ]; }; then
  echo "frametop: patched aquamarine already built at $prefix"
  exit 0
fi

for tool in cmake ninja curl patch sha256sum pkg-config; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "frametop: $tool is required to build aquamarine" >&2
    exit 1
  fi
done

mkdir -p "$src_root"
if [ ! -f "$tarball" ] || ! echo "$sha  $tarball" | sha256sum -c --status; then
  curl -fsSL "https://github.com/hyprwm/aquamarine/archive/refs/tags/$tag.tar.gz" -o "$tarball.part"
  echo "$sha  $tarball.part" | sha256sum -c
  mv "$tarball.part" "$tarball"
fi
rm -rf "$extracted"
tar -xzf "$tarball" -C "$src_root"
patch -p1 -d "$extracted" < "$patch"
# Fedora's hwdata package ships /usr/share/hwdata/pnp.ids and no pkg-config file.
# Aquamarine only uses that directory. A tree-local .pc keeps the lookup working
# without adding a file under /usr.
pcdir=$extracted/build/pkgconfig
mkdir -p "$pcdir"
cat > "$pcdir/hwdata.pc" << 'EOF'
prefix=/usr
datadir=${prefix}/share
pkgdatadir=${datadir}/hwdata
Name: hwdata
Description: hardware identification data
Version: 0
EOF
export PKG_CONFIG_PATH="$pcdir${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
cmake -S "$extracted" -B "$extracted/build" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$prefix"
cmake --build "$extracted/build"
cmake --install "$extracted/build"
printf '%s\n' "$want" > "$stamp"
echo "frametop: installed patched aquamarine to $prefix"
