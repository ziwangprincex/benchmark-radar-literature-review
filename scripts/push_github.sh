#!/usr/bin/env bash
# 推到 GitHub：README 换成 GitHub 版（deploy/README.github.md），其余和 main 一样。
# 工蜂上的 README.md 写的是开发机部署；GitHub 上写的是 GitHub Pages 部署。
set -euo pipefail
cd "$(dirname "$0")/.."
git fetch -q github main
# GitHub 网页上直接改过 README 的话先停下：上次推的 README 和现在 GitHub 上的不一样，
# 说明有人在 GitHub 上改了，要先把改动同步进 deploy/README.github.md，否则会被覆盖。
mark=.git/github_readme_blob
remote_blob=$(git rev-parse FETCH_HEAD:README.md)
if [ -f "$mark" ] && [ "$(cat "$mark")" != "$remote_blob" ] && \
   [ "$remote_blob" != "$(git hash-object deploy/README.github.md)" ]; then
  echo "GitHub 上的 README 被改过，先看 git diff \$(cat $mark) FETCH_HEAD:README.md，同步到 deploy/README.github.md 再推" >&2
  exit 1
fi
export GIT_INDEX_FILE=$(mktemp)
git read-tree HEAD
blob=$(git hash-object -w deploy/README.github.md)
git update-index --cacheinfo 100644,"$blob",README.md
git rm -q --cached deploy/README.github.md
tree=$(git write-tree)
rm -f "$GIT_INDEX_FILE"
sha=$(git commit-tree "$tree" -p FETCH_HEAD -m "$(git log -1 --format=%s)")
git push -q github "$sha:refs/heads/main"
echo "$blob" > "$mark"
echo "github: $sha"
