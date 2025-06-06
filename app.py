import streamlit as st
import pandas as pd
import glob
import json
import os
import altair as alt
import streamlit.components.v1 as components
from pathlib import Path
import matplotlib.pyplot as plt
from venn import venn
import re
from graphviz import Digraph
import requests  # 用于向本地 FastAPI 请求 JSON
################################################################################
# --------------------------  FUNCTIONS & HELPERS  ----------------------------
################################################################################
@st.cache_data(show_spinner=False)
def load_csv(path: Path):
    """
    读取本地 CSV 文件并返回 DataFrame。如果文件不存在，返回 None。
    """
    if path.exists():
        return pd.read_csv(path)
    return None

@st.cache_data(show_spinner=False)
def load_excel(path: Path):
    """
    读取本地 Excel 文件并返回 DataFrame。如果文件不存在，返回 None。
    """
    if path.exists():
        return pd.read_excel(path)
    return None

def build_dot_with_links(lines):
    """
    根据 knowledge_map.txt 的行，构造一个有 URL 链接的 Graphviz 图。
    """
    dot = Digraph(format='svg')
    dot.attr(
        rankdir='LR',
        splines='ortho',
        nodesep='0.3',
        ranksep='0.6'
    )
    dot.node_attr.update(
        shape='box',
        style='rounded,filled',
        fillcolor='#F8F9FA',
        fontname='Microsoft YaHei',
        fontsize='10',
        margin='0.08,0.06'
    )

    for line in lines:
        text = line.strip()
        if not text:
            continue

        m = re.match(r'^(\d+(?:\.\d+)*)(?:[\. ]+\s*(.+))?$', text)
        if not m:
            continue
        code = m.group(1)
        desc = m.group(2) or ''
        label = f"{code} {desc}"

        dot.node(
            code,
            label=label,
            URL=f"?node={code}",
            target="_self"
        )

        if '.' in code:
            parent = '.'.join(code.split('.')[:-1])
            dot.edge(parent, code)
        else:
            dot.node(code, fillcolor='#D62728', fontcolor='white')

    return dot

################################################################################
# -----------------------------  PAGE SETTINGS  --------------------------------
################################################################################
st.set_page_config(
    page_title="CDK4/6 Knowledge-Base | CDK4/6 知识库",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 隐藏 Streamlit 默认菜单
st.markdown("""
<style>
  #MainMenu {visibility: hidden;}
  footer    {visibility: hidden;}
  h1,h2,h3  {text-align: center; font-family: 'Segoe UI', sans-serif;}
  div[data-testid="stDataFrame"] {border:1px solid #e0e0e0; border-radius:6px;}
</style>
""", unsafe_allow_html=True)

################################################################################
# -----------------------------  NAVIGATION  -----------------------------------
################################################################################
page = st.sidebar.radio("选择模块 | Select Module", [
    "1. Statistics | 统计信息",
    "2. Global Network | 全局网络",
    "3. Centrality | 中心性分析",
    "4. Organic Framework | 有机框架",
    "5. Subtype Networks | 亚型网络"
])

DATA_DIR = Path("data")
RAW_DIR  = Path("raw_data")

################################################################################
# --------------------------  1. STATISTICS TAB  -------------------------------
################################################################################
if page.startswith("1."):
    st.header("📈 Knowledge-Base Statistics | 知识库统计信息")

    # 数据表格
    csv_fp = DATA_DIR / "stats" / "cdk4_6_kb.csv"
    df = load_csv(csv_fp)
    if df is None:
        st.warning("请将 cdk4_6_kb.csv 放到 data/stats/ 下 (Please place cdk4_6_kb.csv into data/stats/)。")
        st.stop()
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("下载 CSV | Download CSV", df.to_csv(index=False).encode("utf-8"), "cdk4_6_kb.csv")

    # —— 在这里插入“整包下载”按钮 ——
    stats_zip_fp = DATA_DIR / "stats" / "cdk4_6_kb_full.zip"
    if stats_zip_fp.exists():
        st.download_button(
            "下载全部数据 | Download Full CDK4/6 KB Data",
            open(stats_zip_fp, "rb").read(),
            file_name="cdk4_6_kb_full.zip"
        )
    else:
        st.info("Full data ZIP is not yet generated. | 整包 ZIP 文件尚未生成。")

    # 统计图片
    stats_img = RAW_DIR / "1.stats" / "stats.png"
    if stats_img.exists():
        cols = st.columns([1,4,1])
        with cols[1]:
            st.image(
                str(stats_img),
                caption="CDK4/6 Knowledge-Base – Overview | CDK4/6 知识库概览",
                use_container_width=True
            )
    else:
        st.info("请将 stats.png 放到 raw_data/1.stats/ 下 (Please place stats.png into raw_data/1.stats/)。")

    # 点击知识图谱节点以后，用 ?node=xxx 来筛选 table
    params   = st.experimental_get_query_params()
    selected = params.get("node", [None])[0]
    if selected:
        st.markdown(f"**🔍 已选节点：{selected} | Selected Node: {selected}**")
        df_sel = df[df["四级标签"] == selected]
        if not df_sel.empty:
            st.dataframe(df_sel, use_container_width=True, hide_index=True)
        else:
            st.warning("未找到对应记录 (No matching records found)。")

    # 静态 Graphviz 图（左右层级分明，点击节点可定位表格）
    st.markdown("### 🧠 CDK4/6 Knowledge Graph | CDK4/6 知识图谱 (Click Nodes to Locate Table Entries / 点击节点定位表格)")
    km_file = RAW_DIR / "knowledge_map.txt"
    if km_file.exists():
        lines = km_file.read_text(encoding="utf-8").splitlines()
        dot   = build_dot_with_links(lines)
        st.graphviz_chart(dot.source, use_container_width=True)
    else:
        st.info("请将 knowledge_map.txt 放到 raw_data/ 下并重启应用 (Please place knowledge_map.txt into raw_data/ and restart)。")

################################################################################
# ------------------------  2. GLOBAL NETWORK TAB  -----------------------------
################################################################################
elif page.startswith("2."):
    st.header("🌐 Global Gene Co-Occurrence Network | 全局基因共现网络")

    # —— 1. 先渲染全局大图 (与已有逻辑一致) ——
    cyjs_fp = DATA_DIR / "network" / "network_full.cyjs"
    if not cyjs_fp.exists():
        st.error("❌ 找不到 network_full.cyjs，请先跑 scripts/build_data.py 导入它 (network_full.cyjs not found; please run scripts/build_data.py to import it)。")
        st.stop()

    cfg = json.load(open(cyjs_fp, encoding="utf8"))
    cfg["layout"] = {"name": "preset"}
    cfg["style"]  = [
        {
            "selector": "node",
            "style": {
                "label": "data(name)",
                "width":        "mapData(pmid_count, 1, 1873, 60, 130)",
                "height":       "mapData(pmid_count, 1, 1873, 60, 130)",
                "background-color": "mapData(pmid_count, 1, 1873, #FFEB3B, #9C27B0)",
                "border-width": "mapData(pmid_count, 1, 1873, 4, 10)",
                "border-color": "#333",
                "color":        "mapData(pmid_count, 1, 1873, black, white)",
                "font-size":    10,
                "text-valign":  "center",
                "text-halign":  "center"
            }
        },
        {
            "selector": "edge",
            "style": {
                "width":      1,
                "line-color": "#9e9e9e"
            }
        }
    ]
    cfg_json = json.dumps(cfg)
    html_full = f"""
    <div id="cy_global" style="width:100%; height:60vh; border:1px solid #e0e0e0;"></div>
    <script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
    <script>
      var opts = {cfg_json};
      opts.container = document.getElementById('cy_global');
      cytoscape(opts);
    </script>
    """
    components.html(html_full, height=700, scrolling=True)

    # —— 2. 搜索 & 子网 ——
    st.markdown("---")
    st.subheader("🔎 Search in Any Column and Build Subnetwork | 在任意列搜索并构建子网络")

    # 2.1 让用户先选在哪一列搜索
    col_choice = st.selectbox(
        "请选择要在以下哪一列进行模糊搜索 | Please select a column to search:",
        ["Gene Symbol | 基因符号", "Cell type | 细胞类型", "Disease | 疾病", "Drugs | 药物", "Pathway | 通路"]
    )

    # 2.2 让用户在输入框里输入关键词
    term = st.text_input(
        f"输入 {col_choice} 关键词（支持模糊匹配），按 Enter 键搜索 | Enter keyword for {col_choice} (fuzzy matching, press Enter):",
        placeholder="例如 / e.g.: CDK4"
    ).strip()

    if term:
        # 2.3 读取知识库表格
        kb_fp = DATA_DIR / "stats" / "cdk4_6_kb.csv"
        df_kb = load_csv(kb_fp)
        if df_kb is None:
            st.error("⚠ 无法加载 cdk4_6_kb.csv，请确保已放到 data/stats/ 下 (Cannot load cdk4_6_kb.csv; please place it under data/stats/).")
            st.stop()

        # 2.4 拆分出真正的列名（去掉“|”后面的中文）
        actual_col = col_choice.split("|")[0].strip()
        df_filt = df_kb[df_kb[actual_col].astype(str).str.contains(term, case=False, na=False)]
        if df_filt.empty:
            st.warning(f"未找到在 {actual_col} 列中包含 “{term}” 的任何记录 | No records found in {actual_col} containing “{term}.")
            st.stop()
        else:
            st.success(f"🔍 找到 {len(df_filt)} 条记录。（{actual_col} 中包含 “{term}”） | Found {len(df_filt)} record(s) where {actual_col} contains {term}.")
            st.dataframe(df_filt, use_container_width=True, hide_index=True)

        # —— 3. 构建子网元素 ——
        cols = ["Gene Symbol", "Cell type", "Disease", "Drugs", "Pathway"]
        node_type = {}

        # 3.1 跳过空值或 "-"，收集节点
        for c in cols:
            for raw_val in df_filt[c].dropna().astype(str):
                v = raw_val.strip()
                if v == "-" or v == "":
                    continue
                node_type[v] = c

        # 3.2 两两配对生成边
        edges = set()
        for _, row in df_filt.iterrows():
            vals = []
            for c in cols:
                raw_val = row[c]
                if pd.isna(raw_val):
                    continue
                v = str(raw_val).strip()
                if v == "-" or v == "":
                    continue
                vals.append(v)
            for i in range(len(vals)):
                for j in range(i + 1, len(vals)):
                    a, b = sorted((vals[i], vals[j]))
                    edges.add((a, b))

        # 3.3 转成 Cytoscape.js 所需格式
        elements = []
        for node_name, typ in node_type.items():
            elements.append({
                "data": {"id": node_name, "label": node_name, "type": typ}
            })
        for s, t in edges:
            elements.append({"data": {"source": s, "target": t}})

        # —— 4. 子网样式 ——
        style_sub = [
            {
                "selector": "node",
                "style": {
                    "content":      "data(label)",
                    "width":        70,
                    "height":       70,
                    "font-size":    10,
                    "text-valign":  "center",
                    "text-halign":  "center"
                }
            },
            {
                "selector": "node[type='Gene Symbol']",
                "style": {
                    "shape":            "ellipse",
                    "background-color": "#FFFFCC"
                }
            },
            {
                "selector": "node[type='Cell type']",
                "style": {
                    "shape":            "diamond",
                    "background-color": "#EC7014"
                }
            },
            {
                "selector": "node[type='Disease']",
                "style": {
                    "shape":            "roundrectangle",
                    "background-color": "#8C6BB1"
                }
            },
            {
                "selector": "node[type='Drugs']",
                "style": {
                    "shape":            "rectangle",
                    "background-color": "#41AB5D"
                }
            },
            {
                "selector": "node[type='Pathway']",
                "style": {
                    "shape":            "triangle",
                    "background-color": "#4EB3D3"
                }
            },
            {
                "selector": "edge",
                "style": {
                    "width":       1,
                    "line-color":  "#ccc"
                }
            }
        ]

        # —— 5. 渲染子网 (Circle 布局) ——
        st.markdown("#### 匹配项的子网络 (Circle 布局) | Subnetwork of Matching Terms (Circle Layout)")
        html_sub = f"""
        <div id="cy_subnet" style="width:100%; height:400px; border:1px solid #e0e0e0; margin-bottom:8px;"></div>
        <script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
        <script>
          var cy = cytoscape({{
            container: document.getElementById('cy_subnet'),
            elements: {json.dumps(elements)},
            style:    {json.dumps(style_sub)},
            layout: {{
              name:    'circle',
              fit:     true,
              padding: 80
            }},
            wheelSensitivity: 0.2
          }});
        </script>
        """
        components.html(html_sub, height=450, scrolling=True)

        # —— 6. 二次筛选功能 ——
        st.markdown("---")
        node_list = sorted(node_type.keys())
        chosen_node = st.selectbox(
            "🔎 请选择下方子网中要二次过滤的节点 | Select a node from the subnet below for secondary filtering:",
            ["(· 请选择 ·)"] + node_list
        )
        if chosen_node != "(· 请选择 ·)":
            mask = (
                df_filt["Gene Symbol"].astype(str).str.contains(chosen_node, case=False, na=False)
                | df_filt["Cell type"].astype(str).str.contains(chosen_node, case=False, na=False)
                | df_filt["Disease"].astype(str).str.contains(chosen_node, case=False, na=False)
                | df_filt["Drugs"].astype(str).str.contains(chosen_node, case=False, na=False)
                | df_filt["Pathway"].astype(str).str.contains(chosen_node, case=False, na=False)
            )
            df_second = df_filt[mask]
            if df_second.empty:
                st.warning(f"⚠ 二次筛选后，没有找到任何在 5 列中包含 “{chosen_node}” 的记录 | No records found in any of the 5 columns containing {chosen_node} after secondary filtering.")
            else:
                st.markdown(f"**二次筛选结果：在已匹配 {term} 且 {actual_col} 列中的记录里，包含节点 {chosen_node} 的行如下 | Secondary filtering result: Rows containing node {chosen_node} in records where {actual_col} contains {term}:**")
                st.dataframe(df_second, use_container_width=True, hide_index=True)
        else:
            st.info("👉 上方的下拉列表中选择一个节点来查看二级过滤结果 | Select a node above to view secondary filtering results here.")

################################################################################
# -------------------------  3. CENTRALITY TAB  -------------------------------
################################################################################
elif page.startswith("3."):
    st.header("📊 Centrality Analysis / 中心性分析")

    # 1) 找到 data/centrality 里面所有 CSV
    files = sorted(glob.glob(str(DATA_DIR / "centrality" / "*.csv")))
    if not files:
        st.error("⚠ data/centrality 下未找到任何 CSV 文件 | No centrality CSV files found in data/centrality/.")
        st.stop()

    top_sets = {}
    for fp in files:
        fp_path = Path(fp)
        df = load_csv(fp_path)
        if df is None:
            st.warning(f"⚠ 无法加载文件 {fp_path.name}，请检查路径或文件名 | Cannot load file {fp_path.name}.")
            continue

        # —— 自动识别“基因列”和“数值列” ——
        cols = df.columns.tolist()
        # 常见：第一列是基因名，可能叫 "shared name" 或 "Shared name"；其余列里可能包含 "(Weight)" 或者直接就是指标名
        # 我们先在 cols 里找 “shared name” （大小写不敏感）
        gene_col = None
        for c in cols:
            if c.lower() == "shared name":
                gene_col = c
                break
        if gene_col is None:
            # 如果没找到 "shared name"，就把第一列当作基因列
            gene_col = cols[0]

        # 数值列就是除了 gene_col 外的剩下第一列
        val_cols = [c for c in cols if c != gene_col]
        if not val_cols:
            st.warning(f"⚠ 在文件 {fp_path.name} 中找不到数值列，请检查列名 | No value column found in {fp_path.name}.")
            continue
        val_col = val_cols[0]  # 取第一个数值列

        # 重命名为统一的 "gene" 和 "value"
        df2 = df[[gene_col, val_col]].rename(columns={gene_col: "gene", val_col: "value"})
        metric_name = val_col.replace("_", " ").replace("(Weight)", "").strip().title()
        st.subheader(f"{metric_name} (Top 30)")

        sub = df2.head(30)
        chart = (
            alt.Chart(sub)
               .mark_bar(size=18)
               .encode(
                   x=alt.X("gene:N", sort="-y", title="Gene / 基因"),
                   y=alt.Y("value:Q", title="Value / 数值"),
                   tooltip=["gene", "value"]
               )
               .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)
        st.download_button(
            f"下载 {metric_name}.csv",
            df2.to_csv(index=False).encode("utf-8"),
            f"{metric_name}.csv"
        )
        top_sets[metric_name] = set(df2["gene"].head(32))

    if len(top_sets) == 4:
        st.markdown("### 🔗 Venn Diagram of Top-32 Genes Across Metrics / 四大指标前32基因维恩图")
        fig, ax = plt.subplots(figsize=(6, 6))
        venn(top_sets, ax=ax)
        ax.set_title("Overlap of Top-32 Genes / 前32基因重叠情况")
        st.pyplot(fig)

        common_all = set.intersection(*top_sets.values())
        st.markdown("**同时出现在所有 4 个指标前 32 的基因 / Common to All 4 Metrics**")
        st.write("，  ".join(sorted(common_all)) if common_all else "没有完全重合的基因。")
    else:
        st.info("需要正好 4 个 Centrality CSV 文件来绘制 Venn 图，请检查 data/centrality 文件夹 | Need exactly 4 centrality CSVs to draw Venn diagram; please check data/centrality folder.")

    st.markdown("### 🧠 Updated CDK4/6 Knowledge Graph (20 Central Genes Annotated) | 更新的 CDK4/6 知识图谱（20 个中心基因标注）")
    km2 = Path("raw_data") / "updated_knowledge_map_corrected.txt"
    if km2.exists():
        lines2 = km2.read_text(encoding="utf-8").splitlines()
        dot2   = build_dot_with_links(lines2)

        params = st.experimental_get_query_params()
        sel    = params.get("node", [None])[0]
        if sel:
            st.markdown(f"**🔍 在 Statistics 表中定位：{sel} | Locate in Statistics table: {sel}**")
            df_stats = load_csv(DATA_DIR / "stats" / "cdk4_6_kb.csv")
            if df_stats is not None:
                df_f = df_stats[df_stats["四级标签"] == sel]
                if not df_f.empty:
                    st.dataframe(df_f, use_container_width=True, hide_index=True)
                else:
                    st.warning("在 Statistics 表中未找到此标签 | No such tag found in Statistics table.")
        st.graphviz_chart(dot2.source, use_container_width=True)
    else:
        st.info("⚠ 请将 updated_knowledge_map_corrected.txt 放到 raw_data/ 下并重启应用 | Please place updated_knowledge_map_corrected.txt into raw_data/ and restart.")

################################################################################
# ----------------------  4. ORGANIC FRAMEWORK TAB  ----------------------------
################################################################################
elif page.startswith("4."):
    st.header("🧱 Organic Framework Sub-Network | 有机框架子网络")

    # —— 1. 调用 REST API 拿到 elements 和 style ——
    try:
        # 读取节点/边列表数据
        resp_elems = requests.get("https://cdk46kb.onrender.com/api/organic/elements")
        resp_elems.raise_for_status()
        data_elems = resp_elems.json()
        cy_elems = data_elems.get("elements", [])

        # 读取样式配置
        resp_style = requests.get("https://cdk46kb.onrender.com/api/organic/style")
        resp_style.raise_for_status()
        style_all = resp_style.json()
    except Exception as e:
        st.warning(
            "❗ 无法从 API 获取 Organic Framework 数据，请确认：\n"
            "  • FastAPI 服务已启动并监听在 https://cdk46kb.onrender.com\n"
            "  • GET https://cdk46kb.onrender.com/api/organic/elements 能返回 { \"elements\": […] }\n"
            "  • GET https://cdk46kb.onrender.com/api/organic/style 能返回 Cytoscape 样式数组\n\n"
            f"错误详情: {e}"
        )
        st.stop()

    # —— 2. 如果需要，也可以把本地节点/边表格预览给用户看 ——
    nodes_fp = DATA_DIR / "organic" / "organic_nodes.xlsx"
    edges_fp = DATA_DIR / "organic" / "organic_edges.xlsx"
    if nodes_fp.exists() and edges_fp.exists():
        df_nodes = pd.read_excel(nodes_fp)
        df_edges = pd.read_excel(edges_fp)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Nodes Preview | 节点预览")
            st.dataframe(df_nodes, height=250, use_container_width=True)
        with col2:
            st.subheader("Edges Preview | 边预览")
            st.dataframe(df_edges, height=250, use_container_width=True)
    else:
        st.info("提示：未找到 organic_nodes.xlsx 或 organic_edges.xlsx，仅展示网络可视化。")

    # —— 3. 整理从 API 拿到的 style_all JSON ——
    # 有两种常见结构：
    #   A) style_all 是一个列表，第一项里有 "style" 字段：[{ "formatVersion": "...", "style": [ {...}, ... ] }, …]
    #   B) style_all 直接就是 Cytoscape 样式数组：[{ "selector": "...", "style": { … } }, …]
    if isinstance(style_all, list) and len(style_all) > 0 and isinstance(style_all[0], dict) and "style" in style_all[0]:
        style_cfg = style_all[0]["style"]
    else:
        style_cfg = style_all

    # —— 4. 渲染 Cytoscape（只用 preset 布局，不加载 cose-bilkent） ——
    #    preset 布局会使用 .cyjs 文件里导出的坐标。这样保证你在 Cytoscape Desktop 调好的样式、位置能“原样”搬到浏览器。
    html = f"""
    <div id='cyf' style='width:100%; height:75vh; border:1px solid #e0e0e0;'></div>
    <script src='https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js'></script>
    <script>
      // 初始化 Cytoscape
      var cy = cytoscape({{
        container: document.getElementById('cyf'),
        elements: {json.dumps(cy_elems)},
        style:    {json.dumps(style_cfg)},
        layout:   {{ name: 'preset' }},
        wheelSensitivity: 0.2
      }});
    </script>
    """
    st.markdown("#### Organic Subnetwork | 有机子网络")
    components.html(html, height=680, scrolling=True)
################################################################################
# -----------------------  5. SUBTYPE NETWORKS TAB  ----------------------------
################################################################################
else:
    st.header("🔬 Breast Cancer Subtype-Specific Networks | 乳腺癌亚型网络")

    choice = st.selectbox(
        "Choose subtype | 选择亚型",
        [
            "Luminal B1 Original | Luminal B1 原始图",
            "Luminal B1 Augmented | Luminal B1 推测图",
            "TNBC Original | TNBC 原始图",
            "TNBC Augmented | TNBC 推测图"
        ]
    )

    # 拆分中英文标题（保证下拉里的“|”两边按照格式来写）
    eng_part = choice.split("|")[0].strip()
    chi_part = choice.split("|")[1].strip()
    title_eng = f"{eng_part} Subtype Network Visualization"
    title_chi = f"{chi_part} 网络可视化"
    st.markdown(f"#### {title_eng} | {title_chi}")

    key_map = {
        "Luminal B1 Original":   "luminal_original",
        "Luminal B1 Augmented":  "luminal_aug",
        "TNBC Original":         "tnbc_original",
        "TNBC Augmented":        "tnbc_aug"
    }
    key = key_map[eng_part]  # 比如 "luminal_original"

    # —— 1. 先获取 nodes.csv 和 edges.csv 的预览（可选） ——
    #     下面演示直接本地加载，若想统一使用 API，也可以改成 requests.get("/api/subtype/.../nodes").json()
    nodes_fp = Path("data/subtype") / f"{key}_nodes.csv"
    edges_fp = Path("data/subtype") / f"{key}_edges.csv"
    if not (nodes_fp.exists() and edges_fp.exists()):
        st.warning("Please run build_data.py to generate the required CSV files. | 请运行 build_data.py 生成所需 CSV 文件。")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Nodes | 节点")
        df_nodes = pd.read_csv(nodes_fp)
        st.dataframe(df_nodes, height=250, use_container_width=True)
    with col2:
        st.subheader("Edges | 边")
        df_edges = pd.read_csv(edges_fp)
        st.dataframe(df_edges, height=250, use_container_width=True)

    # —— 2. 调用 API 拿交互网络（cyjs）和样式 ——
    # 注意：下面所有 requests.get 都要调用 .json()，不要用 .text()，否则拿到的是字符串类型。
    base_url = "https://cdk46kb.onrender.com/api/subtype"

    # 2.1 拿 elements（节点+边）
    try:
        resp_elem = requests.get(f"{base_url}/{key}/elements")
        resp_elem.raise_for_status()
        elem_dict = resp_elem.json()  # 一定要 .json() 变成 Python dict
        elements = elem_dict.get("elements", [])  # 得到一个列表
    except Exception as e:
        st.error(f"❌ 无法从 API 获取 /api/subtype/{key}/elements：{e}")
        st.stop()

    # 2.2 拿 style（样式）
    try:
        resp_style = requests.get(f"{base_url}/{key}/style")
        resp_style.raise_for_status()
        style_data = resp_style.json()  # 一定要 .json()，否则 style_data 还是 str
        # style_data 可能是一个列表 [ { "style": [...] } ] 或者直接就是一个样式数组
        # 如果返回的是 [{"style": [...]}, …] 这种形式，就要把真正的列表取出来
        if isinstance(style_data, list) and style_data and isinstance(style_data[0], dict) and "style" in style_data[0]:
            style_list = style_data[0]["style"]
        else:
            style_list = style_data
    except Exception as e:
        st.error(f"❌ 无法从 API 获取 /api/subtype/{key}/style：{e}")
        st.stop()

    # 2.3 在所有 node 统一加上一个固定大小的 style
    universal_size = {
        "selector": "node",
        "style": {
            "width": 60,
            "height": 60
        }
    }
    # style_list 一定要是 Python 列表，才能调用 insert()
    if isinstance(style_list, list):
        style_list.insert(0, universal_size)
    else:
        # 万一 style_list 解析后也是字符串，就给个兜底提示
        st.error("❌ 从 API 返回的 style 不是列表，无法插入 universal_size。")
        st.stop()

    # —— 3. 渲染 Cytoscape.js ——
    html4 = f"""
    <div id='cy_sub' style='width:100%; height:75vh; border:1px solid #e0e0e0;'></div>
    <script src='https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js'></script>
    <script>
      var cy = cytoscape({{
        container: document.getElementById('cy_sub'),
        elements: {json.dumps(elements)},
        style:    {json.dumps(style_list)},
        layout:   {{ name: 'circle', fit: true }},
        wheelSensitivity: 0.2
      }});
    </script>
    """
    components.html(html4, height=760, scrolling=True)