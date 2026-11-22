#!/usr/bin/env bash
# Installs every tool listed for one architecture, refusing any checksum mismatch.
set -euo pipefail

lock_file=$1
architecture=$2
target_dir=$3

install_tool() {
  local name=$1 sha256=$2 url=$3 work_dir
  work_dir=$(mktemp -d)

  curl --fail --silent --show-error --location --retry 3 --output "$work_dir/download" "$url"
  echo "$sha256  $work_dir/download" | sha256sum --check --quiet

  case $url in
    *.tar.gz)
      mkdir "$work_dir/unpacked"
      tar --extract --gzip --file "$work_dir/download" --directory "$work_dir/unpacked"
      find "$work_dir/unpacked" -type f -name "$name" -exec install -m 0755 {} "$target_dir/$name" \;
      ;;
    *)
      install -m 0755 "$work_dir/download" "$target_dir/$name"
      ;;
  esac

  rm -rf "$work_dir"
  test -x "$target_dir/$name"
  echo "installed $name ($architecture)"
}

mkdir -p "$target_dir"
installed=0
while read -r name tool_architecture sha256 url; do
  case $name in '' | '#'*) continue ;; esac
  if [ "$tool_architecture" = "$architecture" ]; then
    install_tool "$name" "$sha256" "$url"
    installed=$((installed + 1))
  fi
done < "$lock_file"

if [ "$installed" -eq 0 ]; then
  echo "no tool is pinned for architecture '$architecture'" >&2
  exit 1
fi
