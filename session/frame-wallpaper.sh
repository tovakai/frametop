#!/usr/bin/env bash
# Frame wallpaper helpers. The staged end-4 scripts source this when
# FT_FRAME_SESSION is set. The laptop copies do not.
# Upscayl is an x86_64 Arch app, so a small image is scaled to the panel
# with ImageMagick. The file button uses kdialog, which the container has.

frame_image_ext() {
  local link=$1 ext
  if [ -z "$link" ] || [ "$link" = "null" ]; then
    notify-send -a "Wallpaper switcher" "Wallpaper download failed" \
      "The site did not return an image." >/dev/null 2>&1 || true
    return 1
  fi
  link=${link%%\?*}
  ext=${link##*.}
  ext=${ext,,}
  case $ext in
    jpg|jpeg|png|webp|avif|bmp|gif) ;;
    *) ext=jpg ;;
  esac
  printf '%s\n' "$ext"
}

frame_require_download() {
  local path=$1
  if [ ! -s "$path" ]; then
    notify-send -a "Wallpaper switcher" "Wallpaper download failed" \
      "The image was empty, so the current wallpaper was left as it is." >/dev/null 2>&1 || true
    return 1
  fi
}

frame_screen_size() {
  local width height
  if [[ ${FT_FRAME_SCREEN_WIDTH:-} =~ ^[0-9]+$ && ${FT_FRAME_SCREEN_HEIGHT:-} =~ ^[0-9]+$ ]]; then
    printf '%s %s\n' "$FT_FRAME_SCREEN_WIDTH" "$FT_FRAME_SCREEN_HEIGHT"
    return
  fi
  read -r width height < <(hyprctl monitors -j | jq -r '[([.[].width] | max), ([.[].height] | max)] | @tsv')
  printf '%s %s\n' "$width" "$height"
}

frame_scale_wallpaper() {
  local img=$1 width height img_w img_h out
  if [ ! -f "$img" ]; then
    printf '%s\n' "$img"
    return
  fi
  read -r width height < <(frame_screen_size)
  if ! [[ $width =~ ^[0-9]+$ && $height =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$img"
    return
  fi
  img_w=$(identify -format '%w' "$img" 2>/dev/null || echo 0)
  img_h=$(identify -format '%h' "$img" 2>/dev/null || echo 0)
  if [[ ${img_w:-0} -ge $width && ${img_h:-0} -ge $height ]]; then
    printf '%s\n' "$img"
    return
  fi
  out=${XDG_STATE_HOME:-$HOME/.local/state}/quickshell/user/generated/wallpaper/frame-scaled.png
  mkdir -p "$(dirname "$out")"
  if command -v magick >/dev/null 2>&1; then
    magick "$img" -filter Lanczos -resize "${width}x${height}^" -gravity center -extent "${width}x${height}" "$out"
  elif command -v convert >/dev/null 2>&1; then
    convert "$img" -filter Lanczos -resize "${width}x${height}^" -gravity center -extent "${width}x${height}" "$out"
  else
    printf '%s\n' "$img"
    return
  fi
  printf '%s\n' "$out"
}

frame_pick_wallpaper() {
  local dir config data
  dir=$(xdg-user-dir PICTURES 2>/dev/null || true)
  [ -n "$dir" ] || dir=$HOME/Pictures
  mkdir -p "$dir/Wallpapers"
  config=${FT_APP_CONFIG_HOME:-$HOME/.config/frametop/hyprland}
  data=${FT_APP_DATA_HOME:-$HOME/.local/share/frametop/hyprland}
  if [ -n "${FT_FRAME_SESSION:-}" ] && [ -f "$FT_FRAME_SESSION/frame-kde-theme.py" ]; then
    python3 "$FT_FRAME_SESSION/frame-kde-theme.py" --previews "$config" || true
  fi
  if command -v kdialog >/dev/null 2>&1; then
    # The shell's own config home is the staged tree. The dialog has to read
    # the session kdeglobals, where the preview view is turned on.
    XDG_CONFIG_HOME=$config \
      XDG_DATA_HOME=$data \
      QT_QPA_PLATFORMTHEME=kde \
      QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-wayland} \
      kdialog --getopenfilename "$dir/Wallpapers" '*.png *.jpg *.jpeg *.webp *.avif *.bmp|Images' --title 'Choose wallpaper'
    return
  fi
  if command -v zenity >/dev/null 2>&1; then
    zenity --file-selection --title='Choose wallpaper' --filename="$dir/Wallpapers/"
    return
  fi
  notify-send -a "Wallpaper switcher" "No file chooser" \
    "kdialog is not installed in this session." >/dev/null 2>&1 || true
  return 1
}

frame_color_venv() {
  printf '%s\n' "${FT_COLOR_VENV:-$HOME/.local/share/frametop/hyprland/color-venv}"
}

frame_scheme_for_image() {
  local img=$1 py
  py=$(frame_color_venv)/bin/python
  if [ -x "$py" ] && [ -n "${SCRIPT_DIR:-}" ] && [ -f "$SCRIPT_DIR/scheme_for_image.py" ]; then
    "$py" "$SCRIPT_DIR/scheme_for_image.py" "$img" 2>/dev/null | tr -d '\n'
    return
  fi
  printf '%s' 'scheme-tonal-spot'
}

frame_write_matugen_config() {
  local dest=$1 state_dir=$2 app_config=$3 colors_out=$4
  local templates=$FT_FRAME_SESSION/matugen/templates
  cat > "$dest" <<EOF
[config]
version_check = false

[templates.m3colors]
input_path = '$templates/colors.json'
output_path = '$colors_out'

[templates.gtk3]
input_path = '$templates/gtk-3.0/gtk.css'
output_path = '$app_config/gtk-3.0/gtk.css'

[templates.gtk4]
input_path = '$templates/gtk-4.0/gtk.css'
output_path = '$app_config/gtk-4.0/gtk.css'

[templates.source]
input_path = '$templates/kde/color.txt'
output_path = '$state_dir/user/generated/matugen-source.txt'
EOF
}

# Generate session colors from a wallpaper. Arguments are matugen's own
# (image PATH --mode dark --type scheme-tonal-spot). Outputs stay under the
# session state and the frametop config home. This does not call
# kde-material-you-colors and does not write the host's ~/.config.
frame_recolor() {
  local state_dir app_config app_data cfg py
  state_dir=${XDG_STATE_HOME:-$HOME/.local/state}/quickshell
  app_config=${FT_APP_CONFIG_HOME:-$HOME/.config/frametop/hyprland}
  app_data=${FT_APP_DATA_HOME:-$HOME/.local/share/frametop/hyprland}
  case "$app_config" in
    "$HOME/.config"|"$HOME/.config/")
      echo "frametop: refusing to recolor the host config" >&2
      return 1
      ;;
  esac
  case "$app_config" in
    *frametop*) ;;
    *)
      echo "frametop: refusing theme path $app_config" >&2
      return 1
      ;;
  esac
  if [ -z "${FT_FRAME_SESSION:-}" ] || [ ! -f "$FT_FRAME_SESSION/matugen/templates/colors.json" ]; then
    echo "frametop: matugen templates are not in this session" >&2
    return 1
  fi
  mkdir -p "$state_dir/user/generated/incoming" "$app_config/gtk-3.0" "$app_config/gtk-4.0" "$app_data"
  local live=$state_dir/user/generated/colors.json
  local staged=$state_dir/user/generated/incoming/colors.json
  cfg=$(mktemp)
  frame_write_matugen_config "$cfg" "$state_dir" "$app_config" "$staged"
  if [ -n "${FT_MATUGEN_CONFIG_COPY:-}" ]; then
    cp "$cfg" "$FT_MATUGEN_CONFIG_COPY"
  fi
  if ! command -v matugen >/dev/null 2>&1; then
    notify-send -a "Wallpaper switcher" "Colors were not updated" \
      "matugen is not installed in this session." >/dev/null 2>&1 || true
    rm -f "$cfg"
    return 1
  fi
  # The shell passes --source-color-index. Fedora's matugen 3.1 rejects it
  # and then no colors are written, so the desktop stays on the old theme.
  local args=() prev="" arg
  for arg in "$@"; do
    if [ "$prev" = "--source-color-index" ]; then
      prev=""
      continue
    fi
    if [ "$arg" = "--source-color-index" ]; then
      prev=$arg
      continue
    fi
    args+=("$arg")
    prev=""
  done
  if ! matugen --config "$cfg" "${args[@]}"; then
    rm -f "$cfg" "$staged"
    return 1
  fi
  rm -f "$cfg"
  # Quickshell watches this inode. Replacing the file leaves that watch on
  # the old one, so a new wallpaper would not repaint the shell.
  if [ -e "$live" ]; then
    cat "$staged" > "$live"
    rm -f "$staged"
  else
    mv "$staged" "$live"
  fi
  py=$(frame_color_venv)/bin/python
  if [ -x "$py" ] && [ -n "${SCRIPT_DIR:-}" ] && [ -f "$SCRIPT_DIR/generate_colors_material.py" ]; then
    "$py" "$SCRIPT_DIR/generate_colors_material.py" ${generate_colors_material_args[@]+"${generate_colors_material_args[@]}"} \
      > "$state_dir/user/generated/material_colors.scss" || true
    if [ -f "$SCRIPT_DIR/applycolor.sh" ]; then
      "$SCRIPT_DIR/applycolor.sh" || true
    fi
  fi
  python3 "$FT_FRAME_SESSION/frame-kde-theme.py" \
    "$state_dir/user/generated/colors.json" "$app_config" "$app_data"
}
