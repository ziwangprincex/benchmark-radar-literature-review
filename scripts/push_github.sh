#!/usr/bin/env bash
# 推到 GitHub：README 换成 GitHub 版（deploy/README.github.md），其余和 main 一样。
# 工蜂上的 README.md 写的是开发机部署；GitHub 上写的是 GitHub Pages 部署。
set -euo pipefail
cd "$(dirname "$0")/.."
git fetch -q github main
export GIT_INDEX_FILE=$(mktemp)
git read-tree HEAD
blob=$(git hash-object -w deploy/README.github.md)
git update-index --cacheinfo 100644,"$blob",README.md
git rm -q --cached deploy/README.github.md
tree=$(git write-tree)
rm -f "$GIT_INDEX_FILE"
sha=$(git commit-tree "$tree" -p FETCH_HEAD -m "$(git log -1 --format=%s)")
git push -q github "$sha:refs/heads/main"
echo "github: $sha"
