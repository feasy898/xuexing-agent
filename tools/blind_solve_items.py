"""批量盲解工具：单代理题 -> 独立代理 ledger（签署测试卡 TC-7/TC-8 数据侧）。

产出与 tools/dual_agent_verify.py 的 ledger 通道完全兼容：
  {"agent_id": <name>, "answers": {item_id: 最终答案}}
盲解纪律：solver 只见题干+选项（绝不见 answer/solution/kps）；输出 ledger
后由 tools/dv2_batch_verify.py 用双代理内核裁决（agree 才可回填）。

网络纪律（G0-5 不受影响）：
- 必须显式 --allow-network 且环境已注入 LLM_API_KEY，否则拒绝运行；
- 端点白名单（https + 主机后缀）：api.moonshot.cn / open.bigmodel.cn /
  api.stepfun.com；key 只从环境变量读，绝不打印、绝不写入任何产物；
- 配额熔断：响应含配额/余额类错误（1310 等）立即整体停止并报告，不重试。

用法：
  LLM_API_KEY=... LLM_BASE_URL=https://api.moonshot.cn/v1 \
  python tools/blind_solve_items.py --subject math --grade 11 \
      --model <model-name> --solver-agent kimi3-blind-dv2-20261008 \
      --forms choice,mcq_multi,fill --allow-network
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOST_SUFFIXES = ("api.moonshot.cn", "api.kimi.com", "open.bigmodel.cn", "api.stepfun.com", "api.minimax.cn", "api.minimaxi.com")
QUOTA_MARKERS = ("1310", "quota", "余额", "欠费", "balance", "insufficient")
ANSWER_RE = re.compile(r"^\s*ANSWER\s*[:：]\s*(.+?)\s*$", re.M)

FORM_RULES = {
    "choice": "单选题：只写正确选项的字母（例如 A）。",
    "mcq_multi": "多选题：只写全部正确选项字母，逗号分隔且按字母序（例如 A,C）。",
    "truefalse": "判断题：只写「对」或「错」。",
    "fill": "填空题：只写填空处的最终答案；多个空用「；」分隔，与题干空序一致。数值用最简形式（分数写成分数，不要小数化）。",
    "computation": "计算题：只写各问最终结果；多个问用「；（1）…（2）…」形式，不要过程。",
    "solve": "解答题：只写最终结果或结论（关键结论逐条给出），不要证明过程。",
    "proof": "证明题：只写证明的关键步骤链（每步一句）。",
    "synthesis": "综合题：只写各问最终结果/结论。",
    "word_problem": "应用题：只写最终答案（含单位）。",
}


def _check_endpoint(base_url):
    if not base_url.startswith("https://"):
        raise SystemExit("LLM_BASE_URL 必须 https")
    host = base_url.split("/")[2]
    if not any(host == s or host.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES):
        raise SystemExit(f"端点 {host} 不在白名单 {ALLOWED_HOST_SUFFIXES}")


def _chat(base_url, api_key, model, messages, timeout=90):
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": messages,
        # 不传 temperature：部分模型（如 k3）仅允许固定值，由服务端默认决定
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    last_err = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            if any(m in detail.lower() or m in detail for m in QUOTA_MARKERS):
                print(f"STOP-QUOTA 配额/余额类错误，按纪律立即停止：HTTP {e.code} {detail}")
                sys.exit(3)
            if e.code in (429, 500, 502, 503):
                last_err = f"HTTP {e.code}: {detail}"
                time.sleep((2, 5, 10)[min(attempt, 2)])
                continue
            raise SystemExit(f"端点错误 HTTP {e.code}: {detail}")
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
            time.sleep((2, 5, 10)[min(attempt, 2)])
    raise SystemExit(f"重试耗尽：{last_err}")


def build_messages(item):
    form = item.get("form") or ""
    rule = FORM_RULES.get(form, "只写最终答案，不要过程。")
    lines = [f"[{item['id']}] 题目类型：{form or item.get('item_type','')}", item["stem"].strip()]
    options = item.get("options") or []
    if options:
        lines.append("选项：")
        lines.extend(str(o).strip() for o in options)
    lines.append(f"作答要求：{rule}")
    lines.append("最后一行必须是：ANSWER: <最终答案>")
    messages = [
        {"role": "system", "content": "你是独立解题代理。只依据题面作答，与任何标准答案无关；不要解释，最终答案放在最后一行 ANSWER: 之后。"},
        {"role": "user", "content": "\n".join(lines)},
    ]
    return messages


def extract_answer(text):
    matches = ANSWER_RE.findall(text or "")
    if not matches:
        return None
    ans = matches[-1].strip().strip("`")
    return ans or None


def solve_one(base_url, api_key, model, item):
    content = _chat(base_url, api_key, model, build_messages(item))
    answer = extract_answer(content)
    if answer is None:
        # 一次提醒重试
        content2 = _chat(base_url, api_key, model,
                         messages=build_messages(item)[:-1] + [
                             {"role": "assistant", "content": (content or "")[-200:]},
                             {"role": "user", "content": "你缺少最后一行 ANSWER: <最终答案>。请只补这一行。"}],
                         )
        answer = extract_answer(content2)
        content = content2
    return item["id"], answer, content


def main() -> int:
    ap = argparse.ArgumentParser(description="批量盲解单代理题 -> ledger（网络显式门控）")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--grade", required=True, type=int)
    ap.add_argument("--forms", default="", help="逗号分隔的 form 白名单；空=全部")
    ap.add_argument("--item-types", default="", help="逗号分隔的 item_type 白名单（choice/fill/solve）；空=全部")
    ap.add_argument("--limit", type=int, default=0, help="最多解多少题（0=全部）")
    ap.add_argument("--model", required=True)
    ap.add_argument("--solver-agent", required=True, help="ledger agent_id（须与批验 --solver-agent 一致）")
    ap.add_argument("--out", default="")
    ap.add_argument("--date", required=True, help="批次日期（如 20261008），用于台账命名")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--data-dir", default=os.path.join(ROOT, "data"))
    ap.add_argument("--allow-network", action="store_true", help="显式确认本次运行会真实调用 LLM API")
    args = ap.parse_args()

    if not args.allow_network:
        raise SystemExit("拒绝运行：本工具会真实调用 LLM API，必须显式加 --allow-network")
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("STEPFUN_API_KEY") or ""
    base_url = os.environ.get("LLM_BASE_URL", "")
    if not api_key or not base_url:
        raise SystemExit("拒绝运行：环境未注入 LLM_API_KEY / LLM_BASE_URL（key 只从环境变量读）")
    _check_endpoint(base_url)

    path = os.path.join(args.data_dir, "items", f"{args.subject}_grade{args.grade}_items.json")
    with open(path, encoding="utf-8") as f:
        items = json.load(f)["items"]
    forms = {x.strip() for x in args.forms.split(",") if x.strip()}
    itypes = {x.strip() for x in args.item_types.split(",") if x.strip()}
    scope = [
        it for it in items
        if len((it.get("verification") or {}).get("agents", [])) == 1
        and (not forms or it.get("form") in forms)
        and (not itypes or it.get("item_type") in itypes)
    ]
    if args.limit:
        scope = scope[: args.limit]
    if not scope:
        print("NOTHING-TO-SOLVE（该范围内无单代理题）")
        return 0
    print(f"SOLVING {len(scope)} items: subject={args.subject} grade={args.grade} "
          f"forms={sorted(forms) if forms else 'all'} types={sorted(itypes) if itypes else 'all'} model={args.model}")

    raw_path = args.out.rstrip(".json") + ".raw.jsonl" if args.out else os.path.join(
        args.data_dir, "verification", f"ledger_dv2_{args.subject}_grade{args.grade}_{args.date}.raw.jsonl")
    answers = {}
    fails = []
    with open(raw_path, "w", encoding="utf-8") as raw:
        def _work(item):
            t0 = time.monotonic()
            try:
                item_id, answer, content = solve_one(base_url, api_key, args.model, item)
                return item_id, answer, content, time.monotonic() - t0, None
            except SystemExit:
                raise
            except Exception as e:  # noqa: BLE001
                return item["id"], None, "", time.monotonic() - t0, f"{type(e).__name__}: {e}"

        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex:
            for item_id, answer, content, dt, err in ex.map(_work, scope):
                if err is not None:
                    fails.append((item_id, err))
                    raw.write(json.dumps({"id": item_id, "ok": False, "error": err}, ensure_ascii=False) + "\n")
                    continue
                if answer is None:
                    fails.append((item_id, "no ANSWER line"))
                    raw.write(json.dumps({"id": item_id, "ok": False, "error": "no ANSWER line"}, ensure_ascii=False) + "\n")
                    continue
                answers[item_id] = answer
                raw.write(json.dumps({"id": item_id, "ok": True, "answer": answer,
                                      "seconds": round(dt, 2)}, ensure_ascii=False) + "\n")
                raw.flush()

    out = args.out or os.path.join(
        args.data_dir, "verification", f"ledger_dv2_{args.subject}_grade{args.grade}_{args.date}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"agent_id": args.solver_agent, "answers": answers}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"SOLVED {len(answers)} / {len(scope)} FAILED {len(fails)}")
    for item_id, err in fails[:10]:
        print(f"  FAIL {item_id}: {err}")
    print(f"LEDGER {out}")
    print(f"RAW {raw_path}")
    print("BLIND-SOLVE-OK" if not fails else "BLIND-SOLVE-PARTIAL")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
