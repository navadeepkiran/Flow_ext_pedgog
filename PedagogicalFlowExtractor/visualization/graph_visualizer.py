"""Interactive Knowledge Graph Visualizer using PyVis.

Renders the NetworkX knowledge graph as a beautiful, interactive HTML
visualization with dark theme, gradient-colored nodes, glow effects,
and elegant custom tooltips.
"""

import json
import os
import re
import tempfile

import networkx as nx
from pyvis.network import Network

from utils.config import load_config, resolve_path
from utils.logger import get_logger

logger = get_logger(__name__)

MIN_NODE_SIZE = 20
MAX_NODE_SIZE = 50

# Community color palette — distinct colors for up to 10 communities
COMMUNITY_COLORS = [
    "#4dd0e1",  # teal
    "#ff7043",  # deep orange
    "#66bb6a",  # green
    "#ab47bc",  # purple
    "#ffa726",  # orange
    "#42a5f5",  # blue
    "#ef5350",  # red
    "#26c6da",  # cyan
    "#8d6e63",  # brown
    "#78909c",  # blue-grey
]


def _community_color(community_id: int) -> str:
    """Return a color for a community ID from the palette."""
    return COMMUNITY_COLORS[community_id % len(COMMUNITY_COLORS)]


def _importance_color(ratio: float) -> str:
    """Map normalized importance [0,1] to a teal-blue-indigo gradient."""
    if ratio < 0.5:
        t = ratio * 2
        r = int(77 + (33 - 77) * t)
        g = int(208 + (150 - 208) * t)
        b = int(225 + (243 - 225) * t)
    else:
        t = (ratio - 0.5) * 2
        r = int(33 + (92 - 33) * t)
        g = int(150 + (107 - 150) * t)
        b = int(243 + (192 - 243) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _lighten(hex_color: str, amount: int = 40) -> str:
    """Lighten a hex color for borders/highlights."""
    r = min(255, int(hex_color[1:3], 16) + amount)
    g = min(255, int(hex_color[3:5], 16) + amount)
    b = min(255, int(hex_color[5:7], 16) + amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def _build_custom_html(node_data: dict, edge_data: dict) -> str:
    """Build custom CSS + JS for beautiful tooltips, injected into PyVis HTML."""
    css = """
<style>
  div.vis-tooltip { display: none !important; }

  .kg-tt {
    display: none; position: fixed; z-index: 99999;
    min-width: 220px; max-width: 340px;
    background: rgba(15,17,26,0.97);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(99,179,237,0.18);
    border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.55), 0 0 30px rgba(33,150,243,0.07);
    color: #e2e8f0;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px; pointer-events: none;
    animation: kgFade 0.14s ease-out; overflow: hidden;
  }
  .kg-tt.edge-variant { border-color: rgba(255,183,77,0.18); }
  @keyframes kgFade { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }

  .kg-tt .th { padding:14px 18px 10px; border-bottom:1px solid rgba(255,255,255,0.06); }
  .kg-tt .tn { font-size:16px; font-weight:600; color:#90caf9; letter-spacing:-0.2px; }
  .kg-tt .tb { padding:10px 18px 14px; }
  .kg-tt .tr { display:flex; justify-content:space-between; align-items:center; padding:4px 0; }
  .kg-tt .tl { color:#64748b; font-size:11px; text-transform:uppercase; letter-spacing:0.6px; }
  .kg-tt .tv { color:#f1f5f9; font-weight:500; }
  .kg-tt .tp { width:100%; height:4px; background:rgba(255,255,255,0.06); border-radius:3px; margin-top:10px; }
  .kg-tt .tf { height:100%; border-radius:3px; background:linear-gradient(90deg,#4dd0e1,#2196f3,#5c6bc0); }

  .kg-tt .eh { font-size:15px; font-weight:600; color:#ffb74d; padding:14px 18px 6px; }
  .kg-tt .ed { color:#94a3b8; font-size:12px; padding:2px 18px; line-height:1.5; }
  .kg-tt .ed:last-child { padding-bottom:14px; }
</style>
"""

    js_template = """
<div class="kg-tt" id="ntt"></div>
<div class="kg-tt edge-variant" id="ett"></div>
<script>
(function(){
  var ND=__ND__;
  var ED=__ED__;
  var ntt=document.getElementById('ntt'), ett=document.getElementById('ett');

  function pos(el,ev){
    var x=ev.center?ev.center.x:0, y=ev.center?ev.center.y:0;
    el.style.left=(x+18)+'px'; el.style.top=(y+18)+'px'; el.style.display='block';
    var r=el.getBoundingClientRect();
    if(r.right>window.innerWidth-10) el.style.left=(x-r.width-18)+'px';
    if(r.bottom>window.innerHeight-10) el.style.top=(y-r.height-18)+'px';
  }
  function wait(){if(typeof network!=='undefined')init();else setTimeout(wait,80);}
  function init(){
    network.setOptions({interaction:{tooltipDelay:999999,hover:true}});

    network.on("hoverNode",function(p){
      var d=ND[p.node]; if(!d)return; ett.style.display='none';
      var h='<div class="th"><div class="tn">'+d.n+'</div></div><div class="tb">';
      h+='<div class="tr"><span class="tl">Importance</span><span class="tv">'+d.i+'</span></div>';
      h+='<div class="tr"><span class="tl">Mentions</span><span class="tv">'+d.f+'</span></div>';
      h+='<div class="tr"><span class="tl">PageRank</span><span class="tv">'+d.pr+'</span></div>';
      if(parseFloat(d.bw)>0) h+='<div class="tr"><span class="tl">Betweenness</span><span class="tv">'+d.bw+'</span></div>';
      h+='<div class="tr"><span class="tl">Depth</span><span class="tv">'+d.dp+'</span></div>';
      if(d.cm>=0) h+='<div class="tr"><span class="tl">Cluster</span><span class="tv">#'+(d.cm+1)+'</span></div>';
      if(d.t.length) h+='<div class="tr"><span class="tl">Appears at</span><span class="tv">'+d.t.join(', ')+'</span></div>';
      h+='<div class="tp"><div class="tf" style="width:'+d.p+'%"></div></div></div>';
      ntt.innerHTML=h; pos(ntt,p.event);
    });
    network.on("blurNode",function(){ntt.style.display='none';});

    network.on("hoverEdge",function(p){
      var d=ED[p.edge]; if(!d)return; ntt.style.display='none';
      var h='<div class="eh">'+d.s+' \\u2192 '+d.t+'</div>';
      h+='<div class="ed">Confidence: '+d.c+'</div>';
      if(d.m) h+='<div class="ed">Method: '+d.m+'</div>';
      if(d.e) h+='<div class="ed" style="margin-top:2px;font-style:italic">\\u201c'+d.e+'\\u201d</div>';
      ett.innerHTML=h; pos(ett,p.event);
    });
    network.on("blurEdge",function(){ett.style.display='none';});

    network.on("dragStart",function(){ntt.style.display='none';ett.style.display='none';});
    network.on("zoom",function(){ntt.style.display='none';ett.style.display='none';});
  }
  wait();
})();
</script>
"""
    js = js_template.replace(
        "__ND__", json.dumps(node_data, ensure_ascii=False)
    ).replace(
        "__ED__", json.dumps(edge_data, ensure_ascii=False)
    )

    return css + js


def visualize_graph(
    graph: nx.DiGraph,
    output_path: str = None,
    title: str = "Pedagogical Knowledge Graph",
    height: str = "700px",
    width: str = "100%",
) -> str:
    """Render a NetworkX graph as a beautiful interactive HTML visualization.

    Args:
        graph: NetworkX DiGraph from GraphBuilder.
        output_path: Where to save the HTML file.
        title: Title displayed on the graph.
        height: Graph display height.
        width: Graph display width.

    Returns:
        Path to the saved HTML file.
    """
    cfg = load_config()

    net = Network(
        height=height,
        width=width,
        directed=True,
        bgcolor="#0f1117",
        font_color="#e2e8f0",
    )

    net.barnes_hut(
        gravity=-4000,
        central_gravity=0.3,
        spring_length=180,
        spring_strength=0.04,
        damping=0.09,
    )

    # Calculate scaling factors — prefer PageRank for sizing if available
    pageranks = [data.get("pagerank", 0) for _, data in graph.nodes(data=True)]
    use_pagerank = any(pr > 0 for pr in pageranks)
    if use_pagerank:
        scores = pageranks
    else:
        scores = [data.get("importance_score", 0) for _, data in graph.nodes(data=True)]
    max_score = max(scores) if scores else 1.0

    # Check if communities are available
    has_communities = any(
        data.get("community") is not None for _, data in graph.nodes(data=True)
    )
    num_communities = len(graph.graph.get("communities", {}))
    use_community_colors = has_communities and num_communities > 1

    node_tooltip_data = {}
    edge_tooltip_data = {}

    # ── Nodes ────────────────────────────────────────────────
    for node, data in graph.nodes(data=True):
        importance = data.get("importance_score", 0)
        difficulty = data.get("difficulty", "unknown")
        timestamps = data.get("timestamps", [])
        normalized = data.get("normalized_name", node)
        frequency = data.get("frequency", 0)
        pagerank = data.get("pagerank", 0)
        betweenness = data.get("betweenness", 0)
        depth = data.get("depth", 0)
        community = data.get("community", 0)

        size_val = pagerank if use_pagerank else importance
        ratio = size_val / max_score if max_score > 0 else 0.5
        size = MIN_NODE_SIZE + ratio * (MAX_NODE_SIZE - MIN_NODE_SIZE)

        # Color by community if available, else by importance gradient
        if use_community_colors:
            color = _community_color(community)
        else:
            color = _importance_color(ratio)
        border = _lighten(color)
        display_name = normalized.replace("_", " ").title()

        net.add_node(
            node,
            label=display_name,
            title="",
            size=size,
            color={
                "background": color,
                "border": border,
                "highlight": {"background": border, "border": "#ffffff"},
                "hover": {"background": border, "border": "#ffffff"},
            },
            font={
                "size": 13,
                "color": "#e2e8f0",
                "face": "Segoe UI, system-ui, sans-serif",
                "strokeWidth": 3,
                "strokeColor": "#0f1117",
            },
            borderWidth=2,
            shadow={"enabled": True, "color": color, "size": 14, "x": 0, "y": 0},
            shape="dot",
        )

        node_tooltip_data[node] = {
            "n": display_name,
            "i": f"{importance:.2f}",
            "f": frequency,
            "d": difficulty,
            "t": timestamps[:6],
            "p": round(ratio * 100),
            "pr": f"{pagerank:.4f}",
            "bw": f"{betweenness:.3f}",
            "dp": depth,
            "cm": community if use_community_colors else -1,
        }

    # ── Edges ────────────────────────────────────────────────
    for i, (source, target, data) in enumerate(graph.edges(data=True)):
        confidence = data.get("confidence", 0)
        evidence = data.get("evidence", "")
        method = data.get("detection_method", "")

        edge_id = f"e{i}"
        edge_width = 1.0 + confidence * 2.5
        opacity = 0.20 + confidence * 0.50
        edge_color = f"rgba(148, 163, 184, {opacity:.2f})"

        src_display = graph.nodes[source].get("normalized_name", source).replace("_", " ").title()
        tgt_display = graph.nodes[target].get("normalized_name", target).replace("_", " ").title()

        net.add_edge(
            source,
            target,
            id=edge_id,
            title="",
            width=edge_width,
            color={"color": edge_color, "highlight": "#90caf9", "hover": "#90caf9"},
            arrows={"to": {"enabled": True, "scaleFactor": 0.7, "type": "arrow"}},
            smooth={"type": "curvedCW", "roundness": 0.15},
        )

        edge_tooltip_data[edge_id] = {
            "s": src_display,
            "t": tgt_display,
            "c": f"{confidence:.2f}",
            "m": method,
            "e": evidence[:100] if evidence else "",
        }

    # ── Save & post-process ──────────────────────────────────
    if output_path is None:
        video_id = graph.graph.get("video_id", "graph")
        output_path = f"outputs/graphs/{video_id}_knowledge_graph.html"

    full_path = resolve_path(output_path) if not os.path.isabs(output_path) else output_path
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    net.save_graph(full_path)

    with open(full_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Remove PyVis duplicate heading
    html = re.sub(r"<center>\s*<h1>.*?</h1>\s*</center>\s*", "", html, count=1)

    # Inject dark background on body
    html = html.replace(
        "<body>",
        '<body style="margin:0;padding:0;overflow:hidden;background:#0f1117;">',
    )

    # Inject custom tooltip CSS + JS before </body>
    custom_html = _build_custom_html(node_tooltip_data, edge_tooltip_data)
    html = html.replace("</body>", custom_html + "\n</body>")

    with open(full_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("Interactive graph saved to: %s", full_path)
    return full_path


def get_graph_html(graph: nx.DiGraph, height: str = "600px") -> str:
    """Generate graph HTML string for embedding in Streamlit."""
    tmp = os.path.join(tempfile.gettempdir(), "_temp_graph.html")
    visualize_graph(graph, output_path=tmp, height=height)
    with open(tmp, "r", encoding="utf-8") as f:
        return f.read()
