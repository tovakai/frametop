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
  local dir
  dir=$(xdg-user-dir PICTURES 2>/dev/null || true)
  [ -n "$dir" ] || dir=$HOME/Pictures
  mkdir -p "$dir/Wallpapers"
  if command -v kdialog >/dev/null 2>&1; then
    QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-wayland} \
      kdialog --getopenfilename "$dir/Wallpapers" --title 'Choose wallpaper'
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
