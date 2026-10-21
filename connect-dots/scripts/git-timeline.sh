#!/usr/bin/env bash
# 用法: bash git-timeline.sh <仓库路径> [子目录]
# 输出 git 历史的"考古摘要"，供 connect-dots skill 分析演化过程。
# 已过滤噪音：merge commit、bot 作者、锁文件/构建产物、依赖升级与格式化类 commit。
set -eu   # 不用 pipefail：git log | head 会触发 SIGPIPE

REPO="${1:-.}"
SUBDIR="${2:-.}"
cd "$REPO"

if [ "$(git rev-parse --is-shallow-repository)" = "true" ]; then
  echo "!! 这是浅克隆，历史不完整。请先执行: git fetch --unshallow" >&2
  exit 1
fi

# 噪音路径
EXCL=(
  ":(exclude)*package-lock.json" ":(exclude)*yarn.lock" ":(exclude)*pnpm-lock.yaml"
  ":(exclude)*Cargo.lock" ":(exclude)*go.sum" ":(exclude)*poetry.lock" ":(exclude)*uv.lock"
  ":(exclude)*.min.js" ":(exclude)*.snap" ":(exclude)dist/*" ":(exclude)vendor/*"
  ":(exclude)node_modules/*" ":(exclude)CHANGELOG*" ":(exclude)History.md"
)
# 噪音 commit：bot 作者，或说明是依赖升级/格式化/lint
NOISE='\[bot\]|^(chore\(deps|build\(deps)|[Bb]ump |[Uu]pdate dependenc|[Uu]pgrade dependenc|lockfile|[Pp]rettier|[Rr]eformat|[Ff]ormat code|[Ll]int'

LOG=(git log --no-merges)

echo "## 基本信息"
TOTAL=$("${LOG[@]}" --format=%h -- "$SUBDIR" | wc -l)
echo "commit 总数（不含 merge）: $TOTAL"
echo "最早: $("${LOG[@]}" --reverse --format='%h %ad %s' --date=short -- "$SUBDIR" | head -1)"
echo "最新: $("${LOG[@]}" -1 --format='%h %ad %s' --date=short -- "$SUBDIR")"
FIRST=$("${LOG[@]}" --reverse --format=%h -- "$SUBDIR" | head -1)
echo "首个 commit 规模: $(git show --shortstat --format= "$FIRST" | tr -s ' ')"
FIRST_INS=$(git show --shortstat --format= "$FIRST" | grep -o '[0-9]* insertion' | grep -o '[0-9]*' || echo 0)
if [ "${FIRST_INS:-0}" -gt 2000 ]; then
  echo "!! 首个 commit 新增 ${FIRST_INS} 行，可能是整体倒入（AI 生成或闭源后开源），早期演化不可见。"
fi
if [ "$TOTAL" -lt 30 ]; then
  echo "!! 历史很短（<30 commit），考古信号弱。分析重心应转向意图文件、Issue/PR 讨论和前人工作对比。"
fi
echo

echo "## 意图文件（作者显式写下的约束与决策，优先阅读）"
find . -maxdepth 3 -not -path './node_modules/*' -not -path './.git/*' \( \
  -iname 'CLAUDE.md' -o -iname 'AGENTS.md' -o -iname '.cursorrules' -o -iname 'GEMINI.md' \
  -o -iname 'DESIGN*.md' -o -iname 'ARCHITECTURE*.md' -o -iname 'PHILOSOPHY*.md' \
  -o -iname 'RFC*' -o -iname 'adr' -o -iname 'decisions' -o -iname 'rfcs' \
  -o -iname 'CONTRIBUTING.md' -o -iname '.github/copilot-instructions.md' \) -print | sort
echo "（README 中的 Non-goals / Why / Motivation 段落也属于此类）"
echo

echo "## 首批 15 个 commit（第一个形态是什么）"
"${LOG[@]}" --reverse --format='%h %ad %s' --date=short -- "$SUBDIR" | head -15
echo

# 历史超过 3 年按季度统计，否则按月
SPAN_MONTHS=$("${LOG[@]}" --format='%ad' --date=format:'%Y-%m' -- "$SUBDIR" | sort -u | wc -l)
if [ "$SPAN_MONTHS" -gt 36 ]; then
  echo "## 季度提交密度（突然变密 = 可能的节奏变化点）"
  "${LOG[@]}" --format='%ad' --date=format:'%Y %m' -- "$SUBDIR" \
    | awk '{q=int(($2-1)/3)+1; print $1"-Q"q}' | sort | uniq -c \
    | awk '{bar=""; for(i=0;i<$1/5;i++) bar=bar"#"; printf "%-8s %4d %s\n", $2, $1, bar}'
else
  echo "## 月度提交密度（突然变密 = 可能的节奏变化点）"
  "${LOG[@]}" --format='%ad' --date=format:'%Y-%m' -- "$SUBDIR" | sort | uniq -c \
    | awk '{bar=""; for(i=0;i<$1;i++) bar=bar"#"; printf "%-8s %4d %s\n", $2, $1, bar}'
fi
echo

echo "## 删除行数最多的 15 个 commit（作者放弃了什么；已过滤噪音）"
"${LOG[@]}" --shortstat --format='COMMIT %h %ad %an | %s' --date=short -- "$SUBDIR" "${EXCL[@]}" \
  | awk '/^COMMIT/ {c=$0} /deletion/ {for(i=1;i<=NF;i++) if($i ~ /^deletion/) print $(i-1), c}' \
  | grep -Ev "$NOISE" | sort -rn | head -15 | sed 's/ COMMIT / /'
echo

echo "## 变更最频繁的 20 个文件（重力中心；已过滤噪音）"
"${LOG[@]}" --name-only --format='@@ %an | %s' -- "$SUBDIR" "${EXCL[@]}" \
  | awk -v noise="$NOISE" '/^@@ / {skip = ($0 ~ noise)} !/^@@ / && NF && !skip {print}' \
  | grep -Ev '^(package\.json|README|Readme|readme)' | sort | uniq -c | sort -rn | head -20
echo

echo "## tag / 版本时间线（共 $(git tag | wc -l) 个；显示最早 5 个与最近 10 个）"
git tag --sort=creatordate --format='%(creatordate:short) %(refname:short)' | head -5
echo "..."
git tag --sort=creatordate --format='%(creatordate:short) %(refname:short)' | tail -10
echo

echo "## 贡献者（top 10，不含 bot）"
git shortlog -sn --no-merges HEAD -- "$SUBDIR" | grep -v '\[bot\]' | head -10
