"""NetworkX dependency graph helpers."""

from __future__ import annotations

from functools import lru_cache

import networkx as nx
from django.db.models import Prefetch

from api.models import Asset, Dependency


def build_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    for asset in Asset.objects.all().only("external_id", "asset_type", "lat", "lon"):
        g.add_node(
            asset.external_id,
            asset_type=asset.asset_type,
            lat=asset.lat,
            lon=asset.lon,
        )
    for dep in Dependency.objects.select_related("parent", "child"):
        g.add_edge(dep.parent.external_id, dep.child.external_id)
    return g


@lru_cache(maxsize=1)
def cached_graph() -> nx.DiGraph:
    return build_graph()


def clear_graph_cache() -> None:
    cached_graph.cache_clear()


def downstream_impact(asset_id: str, graph: nx.DiGraph | None = None) -> tuple[int, list[str]]:
    g = graph or cached_graph()
    if asset_id not in g:
        return 0, []
    descendants = nx.descendants(g, asset_id)
    ids = sorted(descendants)
    return len(ids), ids


def hospital_linked_ids(graph: nx.DiGraph | None = None) -> set[str]:
    """Assets that can reach a Hospital node (or are hospitals)."""
    g = graph or cached_graph()
    hospitals = {n for n, d in g.nodes(data=True) if d.get("asset_type") == "Hospital"}
    linked: set[str] = set(hospitals)
    for node in g.nodes:
        if hospitals & nx.descendants(g, node):
            linked.add(node)
    return linked
