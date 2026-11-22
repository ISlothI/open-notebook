#!/usr/bin/env bash
# Installs the named tools for one architecture, refusing any checksum mismatch.
set -euo pipefail

lock_file=$1
architecture=$2
target_dir=$3
shift 3

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
for wanted in "$@"; do
  entry=$(awk -v name="$wanted" -v arch="$architecture" '$1 == name && $2 == arch' "$lock_file")
  if [ -z "$entry" ]; then
    echo "$wanted is not pinned for architecture '$architecture'" >&2
    exit 1
  fi
  read -r name _ sha256 url <<< "$entry"
  install_tool "$name" "$sha256" "$url"
done
