"""Knowledge Graph Builder.

Constructs a directed knowledge graph from extracted concepts and
detected prerequisite relationships using NetworkX.

Produces:
  - NetworkX DiGraph object (for visualization)
  - Structured JSON output (for export/API)

Enhancements:
  - Embedding-based concept deduplication (sentence-transformers)
  - Edge weight refinement (weighted average of multi-source edges)
  - Community detection (Louvain on undirected projection)
"""

import re
from collections import defaultdict
from difflib import SequenceMatcher

import networkx as nx

from utils.config import load_config
from utils.helpers import now_iso, save_json
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Optional: sentence-transformers for semantic dedup ───────────
_EMBEDDER = None

def _get_embedder():
    """Lazily load sentence-transformer model (cached across calls)."""
    global _EMBEDDER
    if _EMBEDDER is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded sentence-transformer for semantic dedup")
        except ImportError:
            logger.warning("sentence-transformers not installed; falling back to string similarity")
            _EMBEDDER = False  # sentinel: tried and failed
    return _EMBEDDER if _EMBEDDER else None


class GraphBuilder:
    """Builds and manages a pedagogical knowledge graph."""

    def __init__(self):
        """Initialize with an empty directed graph."""
        self.graph = nx.DiGraph()
        self.cfg = load_config()

    def build(
        self,
        video_id: str,
        concepts: list[dict],
        relationships: list[dict],
        transcript: dict = None,
    ) -> nx.DiGraph:
        """Build the knowledge graph from extracted data.

        Pipeline:
          1. Embedding-based concept deduplication
          2. Add nodes
          3. Edge weight refinement (merge multi-source edges)
          4. Compute metrics (PageRank, centrality, HITS, depth)
          5. Community detection (Louvain)

        Args:
            video_id: Identifier for the source video.
            concepts: List of concept dicts from ConceptExtractor.
            relationships: List of relationship dicts from DependencyDetector.
            transcript: Optional transcript dict for metadata.

        Returns:
            NetworkX DiGraph with concepts as nodes and prerequisites as edges.
        """
        logger.info("Building knowledge graph for: %s", video_id)

        # ── Step 1: Semantic deduplication ───────────────────────
        concepts, relationships = self._deduplicate_concepts(concepts, relationships)

        self.graph = nx.DiGraph()
        self.graph.graph["video_id"] = video_id
        self.graph.graph["created_at"] = now_iso()

        # ── Step 2: Add concept nodes ────────────────────────────
        for concept in concepts:
            self.graph.add_node(
                concept["name"],
                normalized_name=concept.get("normalized_name", concept["name"]),
                importance_score=concept.get("importance_score", 0),
                frequency=concept.get("frequency", 0),
                first_mention=concept.get("first_mention", ""),
                timestamps=concept.get("timestamps", []),
                difficulty=concept.get("difficulty", "unknown"),
                teaching_style=[],
            )

        # ── Step 3: Edge weight refinement ───────────────────────
        # Merge duplicate edges from multiple sources using weighted average
        edge_bucket = defaultdict(list)
        for rel in relationships:
            source = rel["from"]
            target = rel["to"]
            if source in self.graph and target in self.graph:
                edge_bucket[(source, target)].append(rel)

        METHOD_WEIGHT = {
            "llm": 0.50,
            "pattern_matching": 0.30,
            "temporal_order": 0.10,
            "co_occurrence": 0.10,
        }

        for (source, target), rels in edge_bucket.items():
            if len(rels) == 1:
                r = rels[0]
                self.graph.add_edge(
                    source, target,
                    relation=r.get("relation", "prerequisite"),
                    confidence=r.get("confidence", 0),
                    evidence=r.get("evidence", ""),
                    timestamp=r.get("timestamp", ""),
                    detection_method=r.get("detection_method", ""),
                )
            else:
                # Weighted average: higher-trust methods count more
                total_weight = 0
                weighted_conf = 0
                evidences = []
                methods = []
                for r in rels:
                    method = r.get("detection_method", "unknown")
                    w = METHOD_WEIGHT.get(method, 0.15)
                    conf = r.get("confidence", 0)
                    weighted_conf += conf * w
                    total_weight += w
                    if r.get("evidence"):
                        evidences.append(r["evidence"])
                    if method not in methods:
                        methods.append(method)

                merged_conf = min(weighted_conf / total_weight if total_weight else 0, 1.0)
                # Boost: multiple sources corroborating adds +0.05 per extra source (cap 1.0)
                merged_conf = min(merged_conf + 0.05 * (len(rels) - 1), 1.0)

                self.graph.add_edge(
                    source, target,
                    relation="prerequisite",
                    confidence=round(merged_conf, 4),
                    evidence=evidences[0] if evidences else "",
                    timestamp="",
                    detection_method="+".join(methods),
                )

        logger.info(
            "Graph built: %d nodes, %d edges",
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
        )

        # ── Step 4: Compute graph metrics ────────────────────────
        self._compute_metrics()

        # ── Step 5: Community detection ──────────────────────────
        self._detect_communities()

        return self.graph

    # ── Embedding-based Concept Deduplication ─────────────────────

    def _deduplicate_concepts(
        self, concepts: list[dict], relationships: list[dict],
        sim_threshold: float = 0.82,
    ) -> tuple[list[dict], list[dict]]:
        """Merge near-duplicate concepts using embedding similarity.

        Falls back to string similarity (SequenceMatcher) when
        sentence-transformers is not installed.

        Args:
            concepts: Raw concept list.
            relationships: Raw relationship list.
            sim_threshold: Cosine similarity threshold for merging.

        Returns:
            (deduplicated_concepts, updated_relationships)
        """
        if len(concepts) <= 1:
            return concepts, relationships

        names = [c["name"] for c in concepts]
        embedder = _get_embedder()

        # Build similarity matrix
        if embedder is not None:
            embeddings = embedder.encode(names, convert_to_tensor=False)
            import numpy as np
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1
            normed = embeddings / norms
            sim_matrix = normed @ normed.T
        else:
            # String-based fallback
            n = len(names)
            sim_matrix = [[0.0] * n for _ in range(n)]
            for i in range(n):
                for j in range(n):
                    sim_matrix[i][j] = SequenceMatcher(None, names[i], names[j]).ratio()

        # Union-Find to group duplicates
        parent = list(range(len(names)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                score = float(sim_matrix[i][j]) if embedder else sim_matrix[i][j]
                if score >= sim_threshold:
                    union(i, j)

        # Build groups and pick the canonical concept (highest importance)
        groups = defaultdict(list)
        for i in range(len(names)):
            groups[find(i)].append(i)

        merged_count = sum(1 for g in groups.values() if len(g) > 1)
        if merged_count:
            logger.info("Semantic dedup: merging %d groups of near-duplicates", merged_count)

        # Map old name → canonical name
        name_map = {}
        deduped_concepts = []
        for idxs in groups.values():
            # Pick the concept with highest importance as canonical
            best_idx = max(idxs, key=lambda i: concepts[i].get("importance_score", 0))
            canonical = concepts[best_idx].copy()
            # Merge frequencies and timestamps from duplicates
            for idx in idxs:
                if idx != best_idx:
                    canonical["frequency"] = canonical.get("frequency", 0) + concepts[idx].get("frequency", 0)
                    extra_ts = concepts[idx].get("timestamps", [])
                    existing_ts = set(canonical.get("timestamps", []))
                    canonical["timestamps"] = canonical.get("timestamps", []) + [
                        t for t in extra_ts if t not in existing_ts
                    ]
                name_map[concepts[idx]["name"]] = canonical["name"]
            deduped_concepts.append(canonical)

        # Remap relationship endpoints
        updated_rels = []
        seen_edges = set()
        for r in relationships:
            src = name_map.get(r["from"], r["from"])
            tgt = name_map.get(r["to"], r["to"])
            if src == tgt:
                continue
            edge_key = (src, tgt)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            updated_rels.append({**r, "from": src, "to": tgt})

        return deduped_concepts, updated_rels

    # ── Community Detection ───────────────────────────────────────

    def _detect_communities(self) -> None:
        """Detect topic communities using Louvain on the undirected projection.

        Stores 'community' (int) on each node and 'communities' (dict)
        on the graph object for visualization coloring.
        """
        g = self.graph
        if g.number_of_nodes() < 2:
            for n in g.nodes():
                g.nodes[n]["community"] = 0
            g.graph["communities"] = {}
            return

        undirected = g.to_undirected()
        try:
            communities = nx.community.louvain_communities(undirected, seed=42)
        except Exception:
            # Fallback: label propagation
            try:
                communities = list(nx.community.label_propagation_communities(undirected))
            except Exception:
                communities = [set(g.nodes())]

        # Assign community IDs to nodes
        community_map = {}
        for cid, members in enumerate(communities):
            for node in members:
                g.nodes[node]["community"] = cid
                community_map[node] = cid

        g.graph["communities"] = {
            cid: sorted(members) for cid, members in enumerate(communities)
        }
        logger.info("Community detection: %d communities found", len(communities))

    def _compute_metrics(self) -> None:
        """Compute graph-theoretic metrics and store them on each node."""
        g = self.graph
        if g.number_of_nodes() == 0:
            return

        # PageRank on REVERSED graph — high score = foundational
        # (In our graph edges go prereq→dependent, so reversing makes
        #  dependents point back to prerequisites, boosting foundational nodes)
        try:
            rev = g.reverse()
            pagerank = nx.pagerank(rev, alpha=0.85)
        except Exception:
            pagerank = {n: 1.0 / g.number_of_nodes() for n in g.nodes()}

        # Betweenness centrality — bridge/gateway concepts
        betweenness = nx.betweenness_centrality(g)

        # In-degree centrality — complex topics (many prerequisites)
        in_degree_c = nx.in_degree_centrality(g)

        # Out-degree centrality — foundational concepts (many depend on them)
        out_degree_c = nx.out_degree_centrality(g)

        # HITS — hubs (gateway concepts) and authorities (core concepts)
        try:
            hubs, authorities = nx.hits(g, max_iter=100)
        except Exception:
            hubs = {n: 0.0 for n in g.nodes()}
            authorities = {n: 0.0 for n in g.nodes()}

        # Depth in DAG — topological depth (longest path from a root)
        depth = self._compute_depth(g)

        # Store on nodes
        for node in g.nodes():
            g.nodes[node]["pagerank"] = round(pagerank.get(node, 0), 6)
            g.nodes[node]["betweenness"] = round(betweenness.get(node, 0), 4)
            g.nodes[node]["in_degree_centrality"] = round(in_degree_c.get(node, 0), 4)
            g.nodes[node]["out_degree_centrality"] = round(out_degree_c.get(node, 0), 4)
            g.nodes[node]["hub_score"] = round(hubs.get(node, 0), 4)
            g.nodes[node]["authority_score"] = round(authorities.get(node, 0), 4)
            g.nodes[node]["depth"] = depth.get(node, 0)

        logger.info("Graph metrics computed for %d nodes", g.number_of_nodes())

    @staticmethod
    def _compute_depth(g: nx.DiGraph) -> dict[str, int]:
        """Compute topological depth for each node (longest path from any root)."""
        depth = {}
        # Work on a DAG copy — remove cycles via weakest edges
        dag = g.copy()
        try:
            while True:
                cycle = nx.find_cycle(dag)
                # Remove weakest edge in the cycle
                weakest = min(cycle, key=lambda e: dag.edges[e[0], e[1]].get("confidence", 0))
                dag.remove_edge(weakest[0], weakest[1])
        except nx.NetworkXNoCycle:
            pass

        for node in nx.topological_sort(dag):
            preds = list(dag.predecessors(node))
            if not preds:
                depth[node] = 0
            else:
                depth[node] = max(depth.get(p, 0) for p in preds) + 1
        return depth

    def get_metrics_summary(self) -> dict:
        """Return aggregate graph metrics for the analytics dashboard."""
        g = self.graph
        if g.number_of_nodes() == 0:
            return {}

        pageranks = [g.nodes[n].get("pagerank", 0) for n in g.nodes()]
        betweenness = [g.nodes[n].get("betweenness", 0) for n in g.nodes()]
        depths = [g.nodes[n].get("depth", 0) for n in g.nodes()]

        density = nx.density(g)
        try:
            dag = g.copy()
            try:
                while True:
                    cycle = nx.find_cycle(dag)
                    weakest = min(cycle, key=lambda e: dag.edges[e[0], e[1]].get("confidence", 0))
                    dag.remove_edge(weakest[0], weakest[1])
            except nx.NetworkXNoCycle:
                pass
            longest_path_len = nx.dag_longest_path_length(dag)
        except Exception:
            longest_path_len = 0

        # Top-5 by PageRank
        ranked = sorted(g.nodes(), key=lambda n: g.nodes[n].get("pagerank", 0), reverse=True)
        top_pagerank = [(n, g.nodes[n].get("pagerank", 0)) for n in ranked[:5]]

        # Top-5 gateway (betweenness)
        ranked_bw = sorted(g.nodes(), key=lambda n: g.nodes[n].get("betweenness", 0), reverse=True)
        top_gateway = [(n, g.nodes[n].get("betweenness", 0)) for n in ranked_bw[:5]]

        # Most foundational (highest out-degree centrality)
        ranked_out = sorted(g.nodes(), key=lambda n: g.nodes[n].get("out_degree_centrality", 0), reverse=True)
        top_foundational = [(n, g.out_degree(n)) for n in ranked_out[:5]]

        # Most complex (highest in-degree centrality)
        ranked_in = sorted(g.nodes(), key=lambda n: g.nodes[n].get("in_degree_centrality", 0), reverse=True)
        top_complex = [(n, g.in_degree(n)) for n in ranked_in[:5]]

        # Community summary
        communities = g.graph.get("communities", {})
        community_summary = []
        for cid, members in communities.items():
            community_summary.append({
                "id": cid,
                "size": len(members),
                "members": [m.replace("_", " ").title() for m in sorted(members)[:8]],
            })

        return {
            "density": round(density, 4),
            "max_depth": max(depths) if depths else 0,
            "longest_path": longest_path_len,
            "top_pagerank": top_pagerank,
            "top_gateway": top_gateway,
            "top_foundational": top_foundational,
            "top_complex": top_complex,
            "communities": community_summary,
            "num_communities": len(communities),
        }

    def to_json(self, transcript: dict = None) -> dict:
        """Export the graph to the standard JSON output format.

        Args:
            transcript: Optional transcript dict for metadata inclusion.

        Returns:
            Structured JSON-serializable dictionary.
        """
        video_id = self.graph.graph.get("video_id", "unknown")

        # Build concepts list
        concepts_out = []
        for i, (node, data) in enumerate(self.graph.nodes(data=True), 1):
            concepts_out.append({
                "id": i,
                "name": node,
                "normalized_name": data.get("normalized_name", node),
                "importance_score": data.get("importance_score", 0),
                "frequency": data.get("frequency", 0),
                "first_mention": data.get("first_mention", ""),
                "timestamps": data.get("timestamps", []),
                "difficulty": data.get("difficulty", "unknown"),
                "teaching_style": data.get("teaching_style", []),
                "pagerank": data.get("pagerank", 0),
                "betweenness": data.get("betweenness", 0),
                "in_degree_centrality": data.get("in_degree_centrality", 0),
                "out_degree_centrality": data.get("out_degree_centrality", 0),
                "hub_score": data.get("hub_score", 0),
                "authority_score": data.get("authority_score", 0),
                "depth": data.get("depth", 0),
                "community": data.get("community", 0),
            })

        # Sort by importance
        concepts_out.sort(key=lambda x: -x["importance_score"])

        # Build relationships list
        relationships_out = []
        for source, target, data in self.graph.edges(data=True):
            relationships_out.append({
                "from": source,
                "to": target,
                "relation": data.get("relation", "prerequisite"),
                "confidence": data.get("confidence", 0),
                "evidence": data.get("evidence", ""),
                "timestamp": data.get("timestamp", ""),
                "detection_method": data.get("detection_method", ""),
            })

        # Build timeline
        timeline = []
        for concept in concepts_out:
            if concept["first_mention"]:
                timeline.append({
                    "time": concept["first_mention"],
                    "concept": concept["name"],
                    "importance": concept["importance_score"],
                })
        # Sort timeline by timestamp
        timeline.sort(key=lambda x: self._time_to_seconds(x["time"]))

        # Metadata
        metadata = {
            "video_id": video_id,
            "processed_at": now_iso(),
            "language": "code-mixed (Hindi-English)",
        }
        if transcript:
            metadata["source_file"] = transcript.get("metadata", {}).get("source_file", "")
            metadata["language_detected"] = transcript.get("metadata", {}).get("language_detected", "")

        # Analytics summary
        analytics = {
            "total_concepts": len(concepts_out),
            "total_relationships": len(relationships_out),
            "avg_confidence": round(
                sum(r["confidence"] for r in relationships_out) / max(len(relationships_out), 1),
                4,
            ),
        }

        output = {
            "video_id": video_id,
            "metadata": metadata,
            "concepts": concepts_out,
            "relationships": relationships_out,
            "timeline": timeline,
            "analytics": analytics,
        }

        return output

    def save(self, output_path: str = None, transcript: dict = None) -> str:
        """Save the knowledge graph JSON to disk.

        Args:
            output_path: Where to save. Auto-generated if None.
            transcript: Optional transcript dict for metadata.

        Returns:
            Path where the file was saved.
        """
        data = self.to_json(transcript)
        video_id = data["video_id"]

        if output_path is None:
            output_path = f"outputs/json/{video_id}_knowledge_graph.json"

        path = save_json(data, output_path)
        logger.info("Knowledge graph saved to: %s", path)
        return path

    def get_prerequisites_for(self, concept: str) -> list[str]:
        """Get all prerequisites (ancestors) for a concept.

        Args:
            concept: Concept name.

        Returns:
            List of prerequisite concept names.
        """
        if concept not in self.graph:
            return []
        return list(nx.ancestors(self.graph, concept))

    def get_dependents_of(self, concept: str) -> list[str]:
        """Get all concepts that depend on this concept.

        Args:
            concept: Concept name.

        Returns:
            List of dependent concept names.
        """
        if concept not in self.graph:
            return []
        return list(nx.descendants(self.graph, concept))

    def get_learning_path(self) -> list[str]:
        """Get a recommended learning order using pedagogical topological sort.

        Uses Kahn's algorithm with a priority queue so that when multiple
        nodes are ready (in-degree 0), we pick the most foundational one
        first based on: out-degree (teaches more → earlier), first
        mention time (introduced earlier → earlier), importance.

        Returns:
            List of concept names in suggested learning order.
            Falls back to importance-based ordering if graph has cycles.
        """
        import heapq

        g = self.graph.copy()

        # Break cycles so topological sort always works
        try:
            cycles = list(nx.simple_cycles(g))
            for cycle in cycles:
                # Remove the weakest edge in the cycle
                weakest_edge = None
                weakest_conf = float("inf")
                for i in range(len(cycle)):
                    u, v = cycle[i], cycle[(i + 1) % len(cycle)]
                    if g.has_edge(u, v):
                        conf = g.edges[u, v].get("confidence", 0)
                        if conf < weakest_conf:
                            weakest_conf = conf
                            weakest_edge = (u, v)
                if weakest_edge and g.has_edge(*weakest_edge):
                    g.remove_edge(*weakest_edge)
        except Exception:
            pass

        # Build in-degree map
        in_degree = {n: 0 for n in g.nodes()}
        for _u, v in g.edges():
            in_degree[v] = in_degree.get(v, 0) + 1

        def _sort_key(node):
            """Lower value = higher priority (picked earlier).

            Among nodes with in-degree 0 at the same time, we want to
            pick the most foundational one first:
              1. Lower depth → more fundamental → pick first
              2. Higher out-degree → teaches more things → pick first
              3. Higher reversed-PageRank → structurally foundational
              4. Earlier first mention in video → pick first
              5. Higher importance score → pick first
            """
            data = g.nodes[node]
            # 1. Lower depth = more foundational
            d = data.get("depth", 0)
            # 2. More outgoing edges → teaches more → pick first
            out_deg = g.out_degree(node)
            # 3. Higher reversed PageRank → foundational
            pr = data.get("pagerank", 0)
            # 4. Earlier first mention → pick first
            ts = data.get("first_mention", "")
            if ts:
                parts = ts.split(":")
                try:
                    secs = int(parts[0]) * 60 + int(parts[1])
                except (ValueError, IndexError):
                    secs = 9999
            else:
                secs = 9999
            # 5. Higher importance → pick first
            importance = data.get("importance_score", 0)
            return (d, -out_deg, -pr, secs, -importance, node)

        # Kahn's algorithm with priority queue
        heap = []
        for n in g.nodes():
            if in_degree[n] == 0:
                heapq.heappush(heap, (_sort_key(n), n))

        result = []
        while heap:
            _key, node = heapq.heappop(heap)
            result.append(node)
            for _u, neighbor in g.out_edges(node):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    heapq.heappush(heap, (_sort_key(neighbor), neighbor))

        # If some nodes missed (shouldn't happen after cycle removal), append them
        remaining = [n for n in g.nodes() if n not in set(result)]
        remaining.sort(key=lambda n: _sort_key(n))
        result.extend(remaining)

        return result

    @staticmethod
    def _time_to_seconds(time_str: str) -> int:
        """Convert 'M:SS' timestamp to total seconds."""
        if not time_str:
            return 0
        parts = time_str.split(":")
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            return 0
