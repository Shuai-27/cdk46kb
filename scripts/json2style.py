# scripts/json2style.py
import json
import re
from pathlib import Path

BASE        = Path(__file__).resolve().parent.parent
RAW_STYLES  = BASE / "raw_data" / "2.network" / "styles.json"
OUT_STYLE   = BASE / "data" / "network" / "style.json"
OUT_STYLE.parent.mkdir(parents=True, exist_ok=True)

# 1) 读进来，取第 0 项的 style 规则
arr  = json.load(open(RAW_STYLES, encoding="utf8"))
conf = arr[0]
rules = conf.get("style", [])

js_styles = []
for rule in rules:
    sel = rule["selector"]
    # 去掉千分位逗号
    sel = re.sub(r"(?<=\d),(?=\d)", "", sel)
    css = rule.get("css", {})
    # 同样修正 css 里 mapData 的数字参数
    css_fixed = {}
    for k,v in css.items():
        if isinstance(v, str):
            css_fixed[k] = re.sub(r"(?<=\d),(?=\d)", "", v)
        else:
            css_fixed[k] = v
    js_styles.append({
        "selector": sel,
        "style": css_fixed
    })

# 2) 写到 data/network/style.json
with open(OUT_STYLE, "w", encoding="utf8") as fo:
    json.dump(js_styles, fo, ensure_ascii=False, indent=2)

print(f"✔ Converted {len(js_styles)} style rules → {OUT_STYLE}")
