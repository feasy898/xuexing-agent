#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L4-02 / L4-02b — xuexing-agent 验收（快检 + RUN_HEAVY 全量 pytest）
# 依据：audit/notes/project-xuexing-agent.md §5（2026-10-01 当日实跑：
#       HEAD 6f59b5a、specs/frozen 16 份契约、.venv/bin/python -m pytest → 709 passed/2 skipped/0 failed）
# 运行注意（勘察原文）：必须用仓内 .venv（Python 3.12）；pytest.ini addopts 已含 -q，
#                       命令行不再叠加 -q（双重安静会隐藏末行统计）
# ---------------------------------------------------------------------------
set -u
source "$RUN_ALL_ROOT/tests/lib/probe.sh"

# ---- GPU 访问：tailnet 主路 + 公网备路（同一台机器，test-plan L0-02/L0-03 口径）----
# 实测背景（2026-10-01 14 时段）：tailscale 数据面偶发瞬断（TCP 可建连但 sshd 无任何
# 日志即被关闭），公网备路同机同 key 可达——主路失败时自动切备路，stderr 留痕。
SSH_GPU_PUB="${SSH_GPU_PUB:-anuser@36.139.118.235}"
gpu_run() {
  local out rc
  out="$(ssh_run "$SSH_GPU" "$@")"; rc=$?
  if [ "$rc" -ne 0 ] && [ -z "$out" ]; then
    echo "[L4] tailnet 主路失败(rc=$rc)，切公网备路 $SSH_GPU_PUB" >&2
    out="$(ssh_run "$SSH_GPU_PUB" "$@")"; rc=$?
  fi
  printf '%s\n' "$out"
  return "$rc"
}

ID="L4-02"; NAME="xuexing-agent 快检（git HEAD + 冻结契约 16 份）"; LAYER="L4"
PROBE_SSH_TIMEOUT=120

out="$(gpu_run 'cd /opt/gpumachine/projects/xuexing-agent && echo "HEAD=$(git log -1 --format=%h)"; echo "SPECS=$(ls specs/frozen/*.spec.md 2>/dev/null | wc -l)"')"
rc=$?
if [ "$rc" -ne 0 ] || [ -z "$out" ]; then
  emit_fail "$ID" "$NAME" "$LAYER" "ssh 双路（tailnet+公网）均不可达(rc=$rc)，GPU 机项目目录无法验证"
  exit 0
fi
gh="$(printf '%s\n' "$out" | sed -n 's/^HEAD=//p')"
gspec="$(printf '%s\n' "$out" | sed -n 's/^SPECS=//p')"
printf '%s\n' "$out" | grep -v '^[A-Z]*=' >&2 || true
if [ -n "$gh" ] && [ "$gspec" = "16" ]; then
  emit_pass "$ID" "$NAME" "$LAYER" "HEAD=$gh specs/frozen 契约 16/16 在位（勘察基线 6f59b5a/16 份）"
else
  emit_fail "$ID" "$NAME" "$LAYER" "HEAD=[$gh] 冻结契约=[$gspec]（基线 6f59b5a/16）"
fi

# ---- L4-02b 全量 pytest（RUN_HEAVY 门控） ----
IDB="L4-02b"; NAMEB="xuexing-agent 全量 pytest（基线 709 passed）"
if ! gate_on RUN_HEAVY; then
  emit_skip "$IDB" "$NAMEB" "$LAYER" "门控 RUN_HEAVY 未开启——全量 pytest（勘察实测 709 passed/2 skipped/0 failed，2.5s）；设 RUN_HEAVY=1 启用"
  exit 0
fi
PROBE_SSH_TIMEOUT=420
out="$(gpu_run 'cd /opt/gpumachine/projects/xuexing-agent && o=$(timeout 280 .venv/bin/python -m pytest 2>&1); rc=$?; echo "PYTEST_RC=$rc"; printf "%s" "$o" | tail -2')"
rc=$?
prc="$(printf '%s\n' "$out" | sed -n 's/^PYTEST_RC=//p')"
ptail="$(printf '%s\n' "$out" | grep -v '^PYTEST_RC=')"
printf '%s\n' "$ptail" >&2 || true
if [ "$rc" -eq 0 ] && [ "$prc" = "0" ] && printf '%s' "$ptail" | grep -q 'passed' && ! printf '%s' "$ptail" | grep -Eq '[1-9][0-9]* failed'; then
  emit_pass "$IDB" "$NAMEB" "$LAYER" "exit 0 零 failed：$(printf '%s' "$ptail" | tail -1)"
else
  emit_fail "$IDB" "$NAMEB" "$LAYER" "ssh_rc=$rc pytest_rc=$prc 尾行=[$(printf '%s' "$ptail" | tail -1)]（基线 709 passed, 2 skipped）"
fi
exit 0
