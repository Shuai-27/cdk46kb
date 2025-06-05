# api.py

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
import pandas as pd
import json

BASE = Path(__file__).parent / "data"

# —— 1. FastAPI 应用 & CORS 设置 ——
app = FastAPI(
    title="CDK4/6 Knowledge-Base REST API",
    description="提供对 data/ 目录下各种统计表格、网络 JSON、子网 JSON 等资源的 HTTP 访问接口。",
    version="0.1"
)

# 允许任意域名跨域访问（如果要限制特定域名，可把 ["*"] 改为 ["https://yourdomain.com"] 等）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


# —— 2. 根路由，交互式帮助信息 ——
@app.get("/")
def root():
    return {
        "message": "CDK4/6 Knowledge-Base REST API 已启用。可用端点示例：",
        "endpoints": {
            "/api/stats": "知识库统计表格 (JSON)",
            "/api/network/full": "全局网络 Cytoscape.js JSON",
            "/api/centrality": "中心性指标列表",
            "/api/centrality/{metric}?top=N": "按指标名称获取前 N 行 CSV 数据",
            "/api/organic/elements": "Organic Framework Cytoscape.js JSON",
            "/api/organic/nodes": "Organic Framework 节点表 (JSON)",
            "/api/organic/edges": "Organic Framework 边表 (JSON)",
            "/api/subtype": "可用子网标签列表",
            "/api/subtype/{tag}": "子网 {tag} Cytoscape.js JSON",
            "/api/subtype/{tag}/nodes": "子网 {tag} 节点表 (JSON)",
            "/api/subtype/{tag}/edges": "子网 {tag} 边表 (JSON)"
        }
    }


# —— 3. Statistics 模块 ——
@app.get("/api/stats")
def get_stats():
    """
    返回 data/stats/cdk4_6_kb.csv 中所有行，按 JSON 数组返回字段 'records'。
    """
    fp = DATA_DIR / "stats" / "cdk4_6_kb.csv"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="stats CSV 文件未找到 (data/stats/cdk4_6_kb.csv)")
    # 读取 CSV，全部当作字符串处理，空值用空字符串代替
    df = pd.read_csv(fp, dtype=str).fillna("")
    records = df.to_dict(orient="records")
    return JSONResponse(content={"records": records})


# —— 4. Global Network 模块 ——
@app.get("/api/network/full")
def get_network_full():
    """
    原样返回 data/network/network_full.cyjs 文件，以 application/json 形式输出。
    """
    fp = DATA_DIR / "network" / "network_full.cyjs"
    if not fp.exists():
        raise HTTPException(status_code=404, detail="network_full.cyjs 未找到 (data/network/network_full.cyjs)")
    return FileResponse(fp, media_type="application/json")


# —— 5. Centrality 模块 ——
@app.get("/api/centrality")
def list_centrality_metrics():
    """
    列出 data/centrality 文件夹下所有 CSV 文件（不含扩展名）。
    """
    folder = DATA_DIR / "centrality"
    if not folder.exists():
        raise HTTPException(status_code=404, detail="centrality 文件夹未找到 (data/centrality)")
    # 仅查后缀为 .csv 的文件
    metrics = [p.stem for p in folder.glob("*.csv")]
    return {"metrics": metrics}


@app.get("/api/centrality/{metric_name}")
def get_centrality_metric(
    metric_name: str,
    top: int = Query(30, ge=1, description="返回 CSV 文件的前 N 行")
):
    """
    返回 data/centrality/{metric_name}.csv 文件前 top 行的记录（按 JSON 数组格式）。
    例：
      GET /api/centrality/degree(weight)?top=20
    """
    csv_fp = DATA_DIR / "centrality" / f"{metric_name}.csv"
    if not csv_fp.exists():
        raise HTTPException(status_code=404, detail=f"centrality 文件未找到: {metric_name}.csv")
    df = pd.read_csv(csv_fp, dtype=str).fillna("")
    df_top = df.head(top)
    rows = df_top.to_dict(orient="records")
    return {"metric": metric_name, "top": top, "rows": rows}


# —— 6. Organic Framework 模块 ——

@app.get("/api/organic/elements")
def get_organic_elements():
    """
    返回 Cytoscape.js 需要的 elements 部分（nodes + edges）。
    直接从 data/organic/organic_full.cyjs 里读取整个 JSON，解析后取出 "elements" 键对应的内容并返回。
    最终返回值为：
      {
        "elements": {
            "nodes": [...],
            "edges": [...]
        }
      }
    """
    cyjs_fp = DATA_DIR / "organic" / "organic_full.cyjs"
    if not cyjs_fp.exists():
        raise HTTPException(status_code=404, detail="organic_full.cyjs not found")
    # 1. 先将文件内容读为字符串
    raw_str = cyjs_fp.read_text(encoding="utf8")
    # 2. 把它解析成 Python 的 dict
    try:
        full_dict = json.loads(raw_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse organic_full.cyjs as JSON")
    # 3. 从 dict 中取出 "elements" 部分
    elements_obj = full_dict.get("elements", None)
    if elements_obj is None:
        raise HTTPException(status_code=500, detail="字段 'elements' 不存在于 organic_full.cyjs 中")
    # 4. 以一个 dict 返回，FastAPI 会自动把它序列化为 JSON 字符串
    return {"elements": elements_obj}


@app.get("/api/organic/style")
def get_organic_style():
    """
    返回 Cytoscape.js 的样式数组（style 配置）。
    直接从 data/organic/organic_style.json 里读取并解析，
    最终返回一个 Python list 或 dict，由 FastAPI 自动序列化。
    """
    style_fp = DATA_DIR / "organic" / "organic_style.json"
    if not style_fp.exists():
        raise HTTPException(status_code=404, detail="organic_style.json not found")
    raw_style = style_fp.read_text(encoding="utf8")
    try:
        style_list = json.loads(raw_style)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse organic_style.json as JSON")
    return style_list


@app.get("/api/organic/nodes")
def get_organic_nodes():
    """
    返回 data/organic 下的节点表格内容：
      - 优先读取 organic_nodes.xlsx
      - 如果不存在再读 organic_nodes.csv
    最终输出格式：
      {
        "nodes": [ {…}, {…}, … ]
      }
    """
    xlsx_fp = DATA_DIR / "organic" / "organic_nodes.xlsx"
    csv_fp  = DATA_DIR / "organic" / "organic_nodes.csv"

    if xlsx_fp.exists():
        try:
            df = pd.read_excel(xlsx_fp, dtype=str).fillna("")
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to read organic_nodes.xlsx")
    elif csv_fp.exists():
        try:
            df = pd.read_csv(csv_fp, dtype=str).fillna("")
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to read organic_nodes.csv")
    else:
        raise HTTPException(status_code=404, detail="organic nodes 文件未找到 (xlsx 或 csv)")

    records = df.to_dict(orient="records")
    return JSONResponse(content={"nodes": records})


@app.get("/api/organic/edges")
def get_organic_edges():
    """
    返回 data/organic 下的边表格内容：
      - 优先读取 organic_edges.xlsx
      - 如果不存在再读 organic_edges.csv
    最终输出格式：
      {
        "edges": [ {…}, {…}, … ]
      }
    """
    xlsx_fp = DATA_DIR / "organic" / "organic_edges.xlsx"
    csv_fp  = DATA_DIR / "organic" / "organic_edges.csv"

    if xlsx_fp.exists():
        try:
            df = pd.read_excel(xlsx_fp, dtype=str).fillna("")
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to read organic_edges.xlsx")
    elif csv_fp.exists():
        try:
            df = pd.read_csv(csv_fp, dtype=str).fillna("")
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to read organic_edges.csv")
    else:
        raise HTTPException(status_code=404, detail="organic edges 文件未找到 (xlsx 或 csv)")

    records = df.to_dict(orient="records")
    return JSONResponse(content={"edges": records})

# —— 7. Subtype Networks 模块 ——
# ------------------------------------------------------------
# 1. 列出所有可用的 subtype tags
# ------------------------------------------------------------
@app.get("/api/subtype")
def list_subtypes():
    """
    列出 data/subtype 文件夹下所有 .cyjs 文件（去掉后缀后的文件名作为 tag）。
    返回：{ "subtypes": ["luminal_original", "luminal_aug", ...] }
    """
    folder = DATA_DIR / "subtype"
    if not folder.exists():
        raise HTTPException(status_code=404, detail="subtype 文件夹未找到 (data/subtype)")
    tags = [p.stem for p in folder.glob("*.cyjs")]
    return {"subtypes": tags}


# ------------------------------------------------------------
# 2. /api/subtype/{tag} —— 直接下载 / 查看 整个 .cyjs 文件
# ------------------------------------------------------------
@app.get("/api/subtype/{tag}")
def download_subtype_cyjs(tag: str):
    """
    返回整个 data/subtype/{tag}.cyjs 文件（Cytoscape.js JSON），
    前端可以用 FileResponse 直接下载或打开。
    """
    cyjs_fp = DATA_DIR / "subtype" / f"{tag}.cyjs"
    if not cyjs_fp.exists():
        raise HTTPException(status_code=404, detail=f"子网 JSON 未找到: {tag}.cyjs")
    # 直接让浏览器下载或打开这个 .cyjs 文件
    return FileResponse(cyjs_fp, media_type="application/json")


# ------------------------------------------------------------
# 3. /api/subtype/{tag}/elements —— 只返回 .cyjs 中的 "elements" 部分
# ------------------------------------------------------------
@app.get("/api/subtype/{tag}/elements")
def get_subtype_elements(tag: str):
    """
    例如 GET /api/subtype/luminal_original/elements
    读取 data/subtype/{tag}.cyjs 文件，把它 parse 成 Python dict，然后只提取 "elements" 键。
    返回格式：{ "elements": [ {...}, {...}, ... ] }
    """
    cyjs_fp = DATA_DIR / "subtype" / f"{tag}.cyjs"
    if not cyjs_fp.exists():
        raise HTTPException(status_code=404, detail=f"{tag}.cyjs not found")
    raw_str = cyjs_fp.read_text(encoding="utf8")
    try:
        full_dict = json.loads(raw_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"{tag}.cyjs 内容不是合法的 JSON")
    elements_list = full_dict.get("elements")
    if elements_list is None:
        # 如果 .cyjs 文件里没有 "elements" 字段，就返回空数组
        return {"elements": []}
    return {"elements": elements_list}


# ------------------------------------------------------------
# 4. /api/subtype/{tag}/style —— 返回 .cyjs 中的样式（从 style.json 拿）
# ------------------------------------------------------------
@app.get("/api/subtype/{tag}/style")
def get_subtype_style(tag: str):
    """
    例如 GET /api/subtype/luminal_original/style
    读取 data/subtype/{tag}_style.json 文件，解析后直接返回给前端。
    返回格式：整个 style JSON 数组或字典，例如：
      [
        { "selector": "node", "style": { ... } },
        ...
      ]
    """
    style_fp = DATA_DIR / "subtype" / f"{tag}_style.json"
    if not style_fp.exists():
        raise HTTPException(status_code=404, detail=f"{tag}_style.json not found")
    raw_str = style_fp.read_text(encoding="utf8")
    try:
        style_obj = json.loads(raw_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"{tag}_style.json 内容不是合法的 JSON")
    return style_obj


# ------------------------------------------------------------
# 5. /api/subtype/{tag}/nodes —— 返回节点表的 JSON 数组
# ------------------------------------------------------------
@app.get("/api/subtype/{tag}/nodes")
def get_subtype_nodes(tag: str):
    """
    读取 data/subtype/{tag}_nodes.csv 文件，将其转成 JSON 数组返回：
      { "nodes": [ {col1: val1, col2: val2, ...}, {...}, ... ] }
    """
    nodes_fp = DATA_DIR / "subtype" / f"{tag}_nodes.csv"
    if not nodes_fp.exists():
        raise HTTPException(status_code=404, detail=f"子网节点文件未找到: {tag}_nodes.csv")
    df = pd.read_csv(nodes_fp, dtype=str).fillna("")
    return {"nodes": df.to_dict(orient="records")}


# ------------------------------------------------------------
# 6. /api/subtype/{tag}/edges —— 返回边表的 JSON 数组
# ------------------------------------------------------------
@app.get("/api/subtype/{tag}/edges")
def get_subtype_edges(tag: str):
    """
    读取 data/subtype/{tag}_edges.csv 文件，将其转成 JSON 数组返回：
      { "edges": [ {col1: val1, col2: val2, ...}, {...}, ... ] }
    """
    edges_fp = DATA_DIR / "subtype" / f"{tag}_edges.csv"
    if not edges_fp.exists():
        raise HTTPException(status_code=404, detail=f"子网边文件未找到: {tag}_edges.csv")
    df = pd.read_csv(edges_fp, dtype=str).fillna("")
    return {"edges": df.to_dict(orient="records")}
