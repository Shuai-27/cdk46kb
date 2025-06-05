# ====================================================================================
# 文件路径：scripts/build_data.py
# 功能：  1) 将 raw_data 里各模块的原始文件（CSV/Excel/.cyjs/.json）复制到 data/ 下
#        2) 对需要合并的子网（luminal_aug、tnbc_aug）做边的合并、节点生成
#        3) 最后自动把 data/stats/ 下所有非 .zip 文件打包成 cdk4_6_kb_full.zip
# ====================================================================================

import pandas as pd
import json
import os
import shutil
import zipfile
from pathlib import Path

RAW = Path("raw_data")
DST = Path("data")

# 1) 在 data/ 下创建各子目录
STAT       = DST / "stats";            STAT.mkdir(parents=True, exist_ok=True)
NETWORK    = DST / "network";          NETWORK.mkdir(parents=True, exist_ok=True)
CENTRALITY = DST / "centrality";       CENTRALITY.mkdir(parents=True, exist_ok=True)
ORGANIC    = DST / "organic";          ORGANIC.mkdir(parents=True, exist_ok=True)
SUBTYPE    = DST / "subtype";          SUBTYPE.mkdir(parents=True, exist_ok=True)


# ——————————————————————————————————————————————————————————
# 1. Statistics 模块
#    raw_data\1.stats\cdk4_6_kb.csv  →  data\stats\cdk4_6_kb.csv
#    raw_data\1.stats\CDK46知识库统计表 英文版.xlsx （可选，不强制）
#    最后打包 data/stats 下所有非.zip 文件，生成 cdk4_6_kb_full.zip
# ——————————————————————————————————————————————————————————
src_stats_csv   = RAW / "1.stats" / "cdk4_6_kb.csv"
src_stats_xlsx  = RAW / "1.stats" / "cdk4_6_kb.xlsx"
src_stats_eng   = RAW / "1.stats" / "CDK46知识库统计表 英文版.xlsx"

if src_stats_csv.exists():
    shutil.copy(src_stats_csv, STAT / "cdk4_6_kb.csv")
    print("✔ copied cdk4_6_kb.csv → data/stats/")
else:
    print("⚠ missing cdk4_6_kb.csv in raw_data/1.stats")

# （可选）如果你想保留原始 Excel 一同复制，可以放到 data/stats/ 里。
if src_stats_xlsx.exists():
    shutil.copy(src_stats_xlsx, STAT / "cdk4_6_kb.xlsx")
    print("✔ copied cdk4_6_kb.xlsx → data/stats/")
if src_stats_eng.exists():
    shutil.copy(src_stats_eng, STAT / "CDK46知识库统计表 英文版.xlsx")
    print("✔ copied CDK46知识库统计表 英文版.xlsx → data/stats/")


# ——————————————————————————————————————————————————————————
# 2. Global Network 模块
#    raw_data\2.network\gene_nodes_simple.csv  →  data\network\
#    raw_data\2.network\gene_cooccurrence_edges.csv  →  data\network\
#    raw_data\2.network\network_full.cyjs  →  data\network\
#    raw_data\2.network\styles.json  →  data\network\
#    （如果有 .xml 样式文件可忽略，.json 足够渲染）
# ——————————————————————————————————————————————————————————

nodes_src    = RAW / "2.network" / "gene_nodes_simple.csv"
edges_src    = RAW / "2.network" / "gene_cooccurrence_edges.csv"
cyjs_src     = RAW / "2.network" / "network_full.cyjs"
style_src    = RAW / "2.network" / "styles.json"

if nodes_src.exists():
    shutil.copy(nodes_src, NETWORK / "gene_nodes_simple.csv")
    print("✔ copied gene_nodes_simple.csv → data/network/")
else:
    print("⚠ missing gene_nodes_simple.csv in raw_data/2.network")

if edges_src.exists():
    shutil.copy(edges_src, NETWORK / "gene_cooccurrence_edges.csv")
    print("✔ copied gene_cooccurrence_edges.csv → data/network/")
else:
    print("⚠ missing gene_cooccurrence_edges.csv in raw_data/2.network")

if cyjs_src.exists():
    shutil.copy(cyjs_src, NETWORK / "network_full.cyjs")
    print("✔ copied network_full.cyjs → data/network/")
else:
    print("⚠ missing network_full.cyjs in raw_data/2.network")

if style_src.exists():
    shutil.copy(style_src, NETWORK / "styles.json")
    print("✔ copied styles.json → data/network/")
else:
    print("⚠ missing styles.json in raw_data/2.network")


# ——————————————————————————————————————————————————————————
# 3. Centrality 模块
#    raw_data\3.centrality\*.xlsx 中带 "top32" 的文件转换为 CSV，放到 data\centrality
#    例如 "Betweenness(Weight)top32.xlsx" → data/centrality/betweenness.csv
#    把所有 "*top32.xlsx" 读出来，去除 "(Weight)top32" 后缀，lowercase，写为 .csv
# ——————————————————————————————————————————————————————————

centrality_folder = RAW / "3.centrality"
if centrality_folder.exists():
    for f in centrality_folder.iterdir():
        fname = f.name
        # 我们只处理 “*top32.xlsx” 这类文件
        if fname.lower().endswith("top32.xlsx"):
            # 例如： "Betweenness(Weight)top32.xlsx"
            # 先去掉后缀 ".xlsx"
            stem = fname[:-5]  # e.g. "Betweenness(Weight)top32"
            # 再去掉 "(Weight)top32"
            metric_name = stem.replace("(Weight)top32", "").lower()  # e.g. "betweenness"
            try:
                df = pd.read_excel(f)
            except Exception as e:
                print(f"⚠ failed to read {fname}: {e}")
                continue
            # 输出 CSV 路径
            out_csv = CENTRALITY / f"{metric_name}.csv"
            df.to_csv(out_csv, index=False)
            print(f"✔ centrality: converted {fname} → data/centrality/{metric_name}.csv")
    print("✔ centrality module done")
else:
    print("⚠ missing folder raw_data/3.centrality")


# ——————————————————————————————————————————————————————————
# 4. Organic Framework 模块
#    raw_data\4.Organic framework\organic_nodes.csv/.xlsx   → data\organic\
#    raw_data\4.Organic framework\organic_edges.csv/.xlsx   → data\organic\
#    raw_data\4.Organic framework\organic_framework.cyjs      → data\organic\
#    raw_data\4.Organic framework\styles.json                 → data\organic\
# ——————————————————————————————————————————————————————————

org_folder = RAW / "4.Organic framework"
if org_folder.exists():
    # 4.1 拷贝 .cyjs + .json 样式
    cyjs_src2  = org_folder / "organic_framework.cyjs"
    style_src2 = org_folder / "styles.json"

    if cyjs_src2.exists():
        shutil.copy(cyjs_src2, ORGANIC / "organic_full.cyjs")
        print("✔ copied organic_framework.cyjs → data/organic/")
    else:
        print("⚠ missing organic_framework.cyjs in raw_data/4.Organic framework")

    if style_src2.exists():
        shutil.copy(style_src2, ORGANIC / "organic_style.json")
        print("✔ copied styles.json → data/organic/")
    else:
        print("⚠ missing styles.json in raw_data/4.Organic framework")

    # 4.2 如果存在 CSV，就优先用它；否则用 XLSX 转 CSV
    nodes_csv_src = org_folder / "organic_nodes.csv"
    edges_csv_src = org_folder / "organic_edges.csv"
    nodes_xlsx_src = org_folder / "organic_nodes.xlsx"
    edges_xlsx_src = org_folder / "organic_edges.xlsx"

    if nodes_csv_src.exists() and edges_csv_src.exists():
        shutil.copy(nodes_csv_src, ORGANIC / "organic_nodes.csv")
        shutil.copy(edges_csv_src, ORGANIC / "organic_edges.csv")
        print("✔ copied organic_nodes.csv & organic_edges.csv → data/organic/")
    elif nodes_xlsx_src.exists() and edges_xlsx_src.exists():
        # 读 Excel，再写 CSV
        try:
            pd.read_excel(nodes_xlsx_src).to_csv(ORGANIC / "organic_nodes.csv", index=False)
            pd.read_excel(edges_xlsx_src).to_csv(ORGANIC / "organic_edges.csv", index=False)
            print("✔ converted organic_nodes.xlsx, organic_edges.xlsx → data/organic/*.csv")
        except Exception as e:
            print(f"⚠ failed to convert organic XLSX → CSV: {e}")
    else:
        print("⚠ missing organic nodes/edges CSV or XLSX in raw_data/4.Organic framework")
else:
    print("⚠ missing folder raw_data/4.Organic framework")


# ——————————————————————————————————————————————————————————
# 5. Subtype Networks 模块
#    5.1 对“原始”子网(原始 luminal_original, tnbc_original) 直接拷贝 .cyjs/.json/.csv/.xlsx
#    5.2 对“增强”子网(luminal_aug, tnbc_aug) 合并原始 edges + 新增 edges，生成新的 edges.csv & nodes.csv
#    5.3 拷贝 *.cyjs 和 *_style.json
# ——————————————————————————————————————————————————————————

# 5.1 定义各个子网对应的 raw_data 子目录
subtype_folders = {
    "luminal_original": "5.Luminal figure",
    "luminal_aug":      "6.luminal figure after knowledge map augmentation",
    "tnbc_original":    "7.TNBC figure",
    "tnbc_aug":         "8.TNBC figure after knowledge map augmentation",
}

# ----- 5.1.a 先处理“原始”子网，直接拷贝文件 -----
for key, folder_name in subtype_folders.items():
    folder = RAW / folder_name

    # 如果目录不存在，就跳过
    if not folder.exists():
        print(f"⚠ missing folder raw_data/{folder_name}")
        continue

    # 1) 拷贝 .cyjs
    cyjs_file = folder / f"{key}.cyjs"
    if cyjs_file.exists():
        shutil.copy(cyjs_file, SUBTYPE / f"{key}.cyjs")
        print(f"✔ copied {key}.cyjs → data/subtype/")
    else:
        print(f"⚠ missing {key}.cyjs in raw_data/{folder_name}")

    # 2) 拷贝 style JSON（凡 *.json，排除掉 .cyjs）
    style_file = None
    for j in folder.glob("*.json"):
        if not j.name.endswith(".cyjs"):  # 排除同名 .cyjs
            style_file = j
            break
    if style_file and style_file.exists():
        shutil.copy(style_file, SUBTYPE / f"{key}_style.json")
        print(f"✔ copied {style_file.name} → data/subtype/{key}_style.json")
    else:
        print(f"⚠ missing *_style.json in raw_data/{folder_name}")

    # 3) “原始”子网同时可能有 nodes.csv / edges.csv
    nodes_csv_raw = folder / f"{key}_nodes.csv"
    edges_csv_raw = folder / f"{key}_edges.csv"
    nodes_xlsx_raw= folder / f"{key}_nodes.xlsx"
    edges_xlsx_raw= folder / f"{key}_edges.xlsx"

    # 优先拷贝 CSV；如果只有 XLSX，就转成 CSV 再拷贝
    if nodes_csv_raw.exists() and edges_csv_raw.exists():
        shutil.copy(nodes_csv_raw, SUBTYPE / f"{key}_nodes.csv")
        shutil.copy(edges_csv_raw, SUBTYPE / f"{key}_edges.csv")
        print(f"✔ copied {key}_nodes.csv & {key}_edges.csv → data/subtype/")
    elif nodes_xlsx_raw.exists() and edges_xlsx_raw.exists():
        try:
            pd.read_excel(nodes_xlsx_raw).to_csv(SUBTYPE / f"{key}_nodes.csv", index=False)
            pd.read_excel(edges_xlsx_raw).to_csv(SUBTYPE / f"{key}_edges.csv", index=False)
            print(f"✔ converted {key}_nodes.xlsx & {key}_edges.xlsx → data/subtype/{key}_*.csv")
        except Exception as e:
            print(f"⚠ failed to convert {key}_*.xlsx → CSV: {e}")
    else:
        # 如果是“增强”子网(luminal_aug/tnbc_aug)，这里暂时不做拷贝，后面走合并逻辑
        # 如果是“原始”子网且找不到，则给警告
        if key.endswith("_original"):
            print(f"⚠ missing {key}_nodes.csv/_nodes.xlsx or {key}_edges.csv/_edges.xlsx in raw_data/{folder_name}")


# ----- 5.2 对“增强”子网做“合并原始 + 新增”操作 -----
#     luminal_aug 需要把 raw_data/5.Luminal figure/luminal_original_edges.csv 和
#                  raw_data/6....../Common_High-Ranked_Gene_Links5%_import.xlsx.csv 合并
#     tnbc_aug     需要把 raw_data/7.TNBC figure/tnbc_original_edges.csv 和
#                  raw_data/8....../TNBC_Common_High-Ranked_Gene_Links_import50.csv 合并

# 定义原始与增强的文件映射
aug_map = {
    "luminal_aug": {
        "orig_folder": "5.Luminal figure",
        "orig_edges_csv": "luminal_original_edges.csv",
        "orig_nodes_csv": "luminal_original_nodes.csv",
        "aug_edges_csv":  "Common_High-Ranked_Gene_Links5%_import.xlsx.csv"
    },
    "tnbc_aug": {
        "orig_folder": "7.TNBC figure",
        "orig_edges_csv": "TNBC_original_edges.csv",
        "orig_nodes_csv": "TNBC_original_nodes.csv",
        "aug_edges_csv":  "TNBC_Common_High-Ranked_Gene_Links_import50.csv"
    },
}

for tag, info in aug_map.items():
    orig_folder = RAW / info["orig_folder"]
    orig_edges  = orig_folder / info["orig_edges_csv"]
    orig_nodes  = orig_folder / info["orig_nodes_csv"]

    aug_folder  = RAW / subtype_folders[tag]
    aug_edges   = aug_folder / info["aug_edges_csv"]

    # 检查文件是否齐全
    if not orig_edges.exists() or not orig_nodes.exists():
        print(f"⚠ edges/nodes missing for original {tag.replace('_aug','_original')}: "
              f"{orig_edges}  or  {orig_nodes}")
        continue
    if not aug_edges.exists():
        print(f"⚠ missing augmented edges CSV for {tag}: {aug_edges}")
        continue

    # 1) 读原始边表、读原始节点表
    df_orig_edges = pd.read_csv(orig_edges, dtype=str)
    df_orig_edges.columns = df_orig_edges.columns.str.lower()

    # 2) 读增强边表（aug_edges 已经是 *.csv）
    df_aug_edges = pd.read_csv(aug_edges, dtype=str)
    df_aug_edges.columns = df_aug_edges.columns.str.lower()

    # 3) 合并边表
    df_combined = pd.concat([df_orig_edges, df_aug_edges], ignore_index=True)
    # 去重（如果需要去重的话，可以加 .drop_duplicates()）
    df_combined = df_combined.drop_duplicates()

    # 4) 写到 data/subtype/{tag}_edges.csv
    out_edges = SUBTYPE / f"{tag}_edges.csv"
    df_combined.to_csv(out_edges, index=False)

    # 5) 从合并后的边表自动生成节点列表
    #    边表里行的 source、target 两列（小写）中取所有 unique
    if "source" in df_combined.columns and "target" in df_combined.columns:
        all_nodes = pd.unique(df_combined[["source", "target"]].values.ravel())
    else:
        # 假如列名不一致，就按第一二列来拆
        all_nodes = pd.unique(df_combined.iloc[:, :2].values.ravel())

    df_nodes = pd.DataFrame({"id": all_nodes})
    df_nodes.to_csv(SUBTYPE / f"{tag}_nodes.csv", index=False)

    print(f"✔ merged subtype edges for {tag}: "
          f"{len(all_nodes)} nodes, {len(df_combined)} edges")

# 5.3 复制“增强”子网的 .cyjs 和 style.json
for key, folder_name in subtype_folders.items():
    if not key.endswith("_aug"):
        continue
    folder = RAW / folder_name

    cyjs_file = folder / f"{key}.cyjs"
    style_file = None
    for j in folder.glob("*.json"):
        if not j.name.endswith(".cyjs"):
            style_file = j
            break

    if cyjs_file.exists():
        shutil.copy(cyjs_file, SUBTYPE / f"{key}.cyjs")
        print(f"✔ copied {key}.cyjs → data/subtype/")
    else:
        print(f"⚠ missing {key}.cyjs in raw_data/{folder_name}")

    if style_file and style_file.exists():
        shutil.copy(style_file, SUBTYPE / f"{key}_style.json")
        print(f"✔ copied {style_file.name} → data/subtype/{key}_style.json")
    else:
        print(f"⚠ missing style JSON for {key} in raw_data/{folder_name}")

print("🎉 Subtype modules all built! 🎉")


# ——————————————————————————————————————————————————————————
# 6. 最后一步：将 data/stats/ 下的所有非 .zip 文件打包成 cdk4_6_kb_full.zip
# ——————————————————————————————————————————————————————————
def make_stats_zip():
    stats_dir = STAT  # 等于 Path("data/stats")
    zip_path  = stats_dir / "cdk4_6_kb_full.zip"

    # 收集所有非 .zip 文件
    files_to_zip = [
        f for f in stats_dir.iterdir()
        if f.is_file() and f.suffix.lower() != ".zip"
    ]

    if not files_to_zip:
        print("⚠ data/stats/ 下没有任何要打包的文件。")
        return

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files_to_zip:
            zf.write(f, arcname=f.name)
            print(f"  + Added {f.name} to ZIP")

    print(f"✔ Generated ZIP: {zip_path}")

# 立即调用
make_stats_zip()
print("🎉 All modules built and stats ZIP generated! 🎉")
