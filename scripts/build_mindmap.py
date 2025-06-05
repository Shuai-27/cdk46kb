# scripts/build_mindmap.py

import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent.parent
RAW  = BASE / "raw_data"
DST  = BASE / "data" / "mindmap"
DST.mkdir(parents=True, exist_ok=True)

def parse_to_jsmind(lines):
    nodes = []
    stack = []  # 存 (level, id)
    cid = 0
    for line in lines:
        text = line.strip()
        if not text:
            continue
        # 假设每两个空格是一个层级，也可按编号 “1.” 来算
        indent = len(line) - len(line.lstrip(' '))
        level = indent // 2
        nid = f"n{cid}"; cid += 1

        # 找 parent
        while stack and stack[-1][0] >= level:
            stack.pop()
        if stack:
            nodes.append({"id": nid, "parentid": stack[-1][1], "topic": text})
        else:
            nodes.append({"id": nid, "isroot": True,           "topic": text})
        stack.append((level, nid))

    return {
        "meta":   {"name":"CDK4/6-KG", "author":"you", "version":"1.0"},
        "format": "node_tree",
        "data":   nodes
    }

def main():
    # 1) 读入你的结构化文本（放 raw_data/knowledge_map.txt）
    txt = RAW / "knowledge_map.txt"
    if not txt.exists():
        print("⚠ 找不到 raw_data/knowledge_map.txt")
        return

    lines = txt.read_text(encoding="utf-8").splitlines()
    jm   = parse_to_jsmind(lines)

    # 2) 输出到 data/mindmap/cdk46_mindmap.json
    out = DST / "cdk46_mindmap.json"
    out.write_text(json.dumps(jm, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ 已生成 {out}")

if __name__ == "__main__":
    main()
