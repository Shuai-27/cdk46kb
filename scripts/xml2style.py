import json
from pathlib import Path

raw = Path("raw_data/2.network/styles.json")
dst = Path("data/network/style.json")
dst.parent.mkdir(exist_ok=True, parents=True)

d = json.load(open(raw, encoding="utf8"))  # 这会读出一个 Array，取第一个元素
d = d[0]                                   # 取那个对象
js_styles = []
for rule in d["style"]:
    sel = rule["selector"]
    css = rule["css"]
    js_styles.append({
        "selector": sel,
        "style": css     # 注意 key 要叫 "style"，不是 "css"
    })

with open(dst, "w", encoding="utf8") as fo:
    json.dump(js_styles, fo, ensure_ascii=False, indent=2)
print("✔ style.json 转换完毕，规则数 =", len(js_styles))
