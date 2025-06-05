import streamlit as st
import pandas as pd
import altair as alt
import json
import glob
import streamlit.components.v1 as components

st.set_page_config(page_title="CDK4/6 KB Explorer", layout="wide")
st.title("CDK4/6 Knowledge Base · Explorer")

# ---------- 数据加载 ----------
@st.cache_data
def load_centrality():
    frames = [pd.read_csv(f) for f in glob.glob("data/centrality/*.csv")]
    return pd.concat(frames, ignore_index=True)

@st.cache_data
def load_network():
    try:
        return json.load(open("data/network.json", encoding="utf8"))
    except FileNotFoundError:
        return {"elements": []}

cent = load_centrality()

# ---------- 页签 ----------
tab1, tab2, tab3 = st.tabs(["Centrality", "Venn", "Network"])

# ——1. 中心性柱状图 —— 
with tab1:
    for metric in cent.metric.unique():
        sub = cent[cent.metric == metric].sort_values("value", ascending=False)
        st.subheader(metric.capitalize())
        chart = (
            alt.Chart(sub.head(32))
            .mark_bar()
            .encode(
                x=alt.X("gene:N", sort="-y"),
                y="value:Q",
                tooltip=["gene", "value"],
            )
            .properties(width=900, height=350)
        )
        st.altair_chart(chart, use_container_width=True)
        st.download_button(
            f"Download full {metric}.csv",
            sub.to_csv(index=False).encode(),
            f"{metric}.csv",
            "text/csv",
        )

# ——2. 静态 Venn 图 ——
with tab2:
    st.subheader("Overlap of Top-32 Genes (Venn Diagram)")
    # 直接展示静态图
    st.image(
        "assets/venn4.png",
        use_container_width=True,
        caption="Top-32 genes overlap across four metrics"
    )

# ——3. 交互网络图 ——
with tab3:
    st.subheader("Interactive Knowledge Graph")
    net = load_network()
    html = f"""
    <div id='cy' style='width:100%; height:780px;'></div>
    <script src='https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js'></script>
    <script>
      var cy = cytoscape({{
        container: document.getElementById('cy'),
        elements: {json.dumps(net["elements"])},
        style: [
          {{ selector: 'node', style: {{
                'content':'data(label)', 'font-size':'5px',
                'background-color':'#6c8', 'width':8, 'height':8
            }} }},
          {{ selector: 'edge', style: {{
                'width':0.4, 'line-color':'#ccc'
            }} }}
        ],
        layout: {{ name:'cose', fit:true }}
      }});
    </script>
    """
    components.html(html, height=800, scrolling=True)

# 侧边栏提示
st.sidebar.success("← 选择标签开始浏览")
