#!/usr/bin/env python3
"""
collect_forecast_checker_topic.py — Forecast-Checker 专用采集入口（薄包装）

为什么需要它（2026-09-04 实测根因，与 Notion-Summary 同族）：
  cron 的 agent 型 job，pre-run script **拿不到 workdir**（scheduler 只在
  no_agent 分支传 workdir），所以通用采集器 collect_topic_conversation.py
  只能靠 jobs.json 的 fire_claim 反推自己是哪个 job。fire_claim 的匹配键是
  **脚本文件名**，20 个 distill job 共用同一个脚本名 —— 键不唯一。

  本次不是「排在同一分钟」，而是**前一个 job 还没跑完**：
  eco-vol-context-distill（06:00）的 agent 轮仍在运行，scheduler 的心跳把它的
  fire_claim.at 持续刷新成「刚刚」；06:15 forecast-checker 触发时看到两个年龄
  都 ≈0s 的 claim，CLAIM_AMBIGUOUS_SECS=60 歧义闸命中 → fail-closed、当天零归档。
  ⇒ 错开排班治不了这种，因为「撞车」由**运行时长**决定，不由 cron 表达式决定。

  scheduler 不支持 script_args，无法在 job 配置里传 --thread。所以给本项目单独
  一个脚本名：fire_claim 按文件名匹配时全局只有一个候选，歧义在结构上不可能发生，
  身份来自显式参数而非环境推断。

行为：等价于
  collect_topic_conversation.py --thread <你的 chat_id>:<你的 thread_id>
其余参数（--hours / --max-chars / --db）原样透传。
"""
import os
import runpy
import sys

# 接手方必须设置：chat_id:thread_id，形如 -100xxxxxxxxxx:12345，见 ~/.hermes/project_topic_map.json。
# 不给默认值——写死别人的话题 ID 会把对话归档到不属于你的项目里，宁可明确报错。
FORECAST_CHECKER_THREAD = os.environ.get("FC_TOPIC_THREAD", "").strip()
COLLECTOR = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         "collect_topic_conversation.py")


def main():
    if not FORECAST_CHECKER_THREAD:
        print("NO_NEW_CONTENT (FC_TOPIC_THREAD 未设置：接手方需在 cron 环境里设 FC_TOPIC_THREAD=<chat_id>:<thread_id>，见 SETUP.md §5)")
        return
    if not os.path.exists(COLLECTOR):
        print(f"NO_NEW_CONTENT (collector not found: {COLLECTOR})")
        return
    argv = list(sys.argv[1:])
    # 调用方若显式给了 --thread/--project 就尊重之，否则钉死本项目 topic
    if not any(a.split("=")[0] in ("--thread", "--project") for a in argv):
        argv += ["--thread", FORECAST_CHECKER_THREAD]
    sys.argv = [COLLECTOR] + argv
    runpy.run_path(COLLECTOR, run_name="__main__")


if __name__ == "__main__":
    main()
