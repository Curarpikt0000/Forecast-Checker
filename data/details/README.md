# data/details/ — 预言级 detail 源文件（SSOT）

每个文件 `<person_id>.json` 是**源文件**，不是派生产物。

由 `scripts/merge_backfill.py` 的 `_DETAILS_DIR` 逻辑读取，按 `summary` 精确匹配
挂到 `backfill_full.json` 对应预言条目的 `detail` 字段上。

## 格式
```json
{
  "person_id": "martin_armstrong",
  "_collected_on": "2026-08-21",
  "details": [
    {
      "summary": "<必须与 backfill_full.json 中该条 summary 完全一致，用于匹配>",
      "detail": "<80-250 字，基于 source_url 真实内容的二次核实展开>",
      "source_url": "<核实所用来源，可与原 source_url 不同>"
    }
  ]
}
```

## 铁律
- `detail` 必须来自真实可访问来源，**绝不由 summary 凭空扩写**。
- 查不到实质信息的条目 **直接不输出该条**，留空由前端优雅降级，不硬凑。
- `summary` 字段是匹配键，一个字都不能改。
