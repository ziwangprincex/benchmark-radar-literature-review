#!/usr/bin/env bash
# 每周刷新（服务器版）：服务器上不了 arXiv，所以本机抓论文，传过去，让服务器入库、分类、推送。
# 用法: bash deploy/remote_refresh.sh            正常跑
#       bash deploy/remote_refresh.sh --no-push  不发企业微信
set -euo pipefail
HOST="${RADAR_SERVER:?先设置 RADAR_SERVER=服务器地址}"
SSH="ssh -p 36000 -o BatchMode=yes -o LogLevel=ERROR"
REMOTE_DIR=/data/benchmark-idea-radar
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILE="/tmp/radar_new_papers_$(date +%Y%m%d).jsonl"

python3 "$ROOT/scripts/sweep_arxiv_benchmarks.py" 600 --dump "$FILE"
scp -P 36000 -o BatchMode=yes -o LogLevel=ERROR "$FILE" "$HOST:$REMOTE_DIR/data/incoming.jsonl"
$SSH "$HOST" "cd $REMOTE_DIR && .venv/bin/python scripts/weekly_refresh.py --from data/incoming.jsonl $*"
echo "---- 服务器上的 reports/weekly_refresh.md ----"
$SSH "$HOST" "cat $REMOTE_DIR/reports/weekly_refresh.md"
