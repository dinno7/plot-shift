#! /bin/env bash

set -eu

get_url_size() {
  local url="$1"
  curl -sI "$url" | grep -i content-length | awk '{print $2}'
}

get_local_file_size() {
  local file="$1"
  stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null
}

download_and_extract() {
  local url="${1:?URL not set}"
  local gz_file="${2:?Gz path not set}"
  local tsv_file="${3:?TSV path not set}"

  if [[ -f "$tsv_file" ]]; then
    echo "$tsv_file exists"
    return 0
  fi

  echo "$tsv_file not exists"

  if [[ -f "$gz_file" ]]; then
    echo "$gz_file exists"
    local remote_size="$(get_url_size "$url")"
    local local_size="$(get_local_file_size "$gz_file")"

    if [[ "$remote_size" -eq "$local_size" ]]; then
      echo "✓ Sizes match - file is complete"
    else
      echo "✗ Sizes differ - file may be incomplete or different"
      echo "Downloading $gz_file..."
      wget -c "$url" -O "$gz_file"
    fi
  else
    echo "$gz_file not exists"
    echo "Downloading $gz_file..."
    wget -c "$url" -O "$gz_file"
  fi

  echo "Gunzip the $gz_file to $tsv_file"
  gunzip "$gz_file"
}

basics_out_url="https://datasets.imdbws.com/title.basics.tsv.gz"
basics_out_tsv="$PWD/data/raw/title.basics.tsv"
basics_out_gz="$PWD/data/raw/title.basics.tsv.gz"
mkdir -p dirname "$basics_out_gz"

ratings_out_url="https://datasets.imdbws.com/title.ratings.tsv.gz"
ratings_out_tsv="$PWD/data/raw/title.ratings.tsv"
ratings_out_gz="$PWD/data/raw/title.ratings.tsv.gz"
mkdir -p dirname "$ratings_out_gz"

download_and_extract "$basics_out_url" "$basics_out_gz" "$basics_out_tsv"
download_and_extract "$ratings_out_url" "$ratings_out_gz" "$ratings_out_tsv"
