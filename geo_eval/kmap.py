"""Knowledge map: the entity, what is known about it, and how far each fact is from it.

A map is a JSON file:

{
  "entity": {"name": "Min Cai", "aliases": ["蔡旻"], "url": "https://example.github.io/"},
  "nodes": [
    {"id": "affiliation", "hop": 0, "kind": "fact",
     "terms": ["University of Alberta"], "fact": "Min Cai is a PhD student at the University of Alberta."},
    {"id": "strategist", "hop": 1, "kind": "paper", "terms": ["Strategist"],
     "fact": "...", "url": "https://arxiv.org/abs/2408.10635", "venue": "ICLR 2025"},
    {"id": "social-deduction-games", "hop": 2, "kind": "topic", "terms": ["social deduction games"], "via": ["strategist"]}
  ],
  "questions": [{"id": "q-affiliation", "node": "affiliation", "q": "...", "answer_terms": ["University of Alberta"]}],
  "probes": [{"query": "Min Cai University of Alberta", "hop": 0}],
  "forbidden": [{"text": "Beijing, China", "reason": "stale location"}],
  "limits": {"max_visible_chars": 20000}
}

hop 0 = core identity (name, affiliation, advisor), hop 1 = directly connected
(papers, research areas, venues), hop 2 = the wider topics where the entity
should surface. Nodes may name the nodes they hang off with "via".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HOP_WEIGHTS = {0: 3.0, 1: 2.0, 2: 1.0}


class MapError(ValueError):
    pass


@dataclass
class Node:
    id: str
    hop: int
    terms: list[str]
    kind: str = "fact"
    fact: str = ""
    url: str | None = None
    venue: str | None = None
    via: list[str] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)

    @property
    def weight(self) -> float:
        return HOP_WEIGHTS.get(self.hop, 1.0)


@dataclass
class Question:
    id: str
    q: str
    answer_terms: list[str]
    node: str | None = None
    hop: int = 0


@dataclass
class KnowledgeMap:
    name: str
    aliases: list[str]
    url: str | None
    nodes: list[Node]
    questions: list[Question]
    probes: list[dict[str, Any]]
    forbidden: list[dict[str, str]]
    limits: dict[str, Any]
    scoring: dict[str, float] = field(default_factory=dict)

    @property
    def identity_terms(self) -> list[str]:
        return [self.name, *self.aliases]

    def node(self, node_id: str) -> Node | None:
        return next((node for node in self.nodes if node.id == node_id), None)

    def papers(self) -> list[Node]:
        return [node for node in self.nodes if node.kind == "paper"]

    def by_hop(self, hop: int) -> list[Node]:
        return [node for node in self.nodes if node.hop == hop]

    def queries_for(self, node: Node) -> list[str]:
        """Search queries that should surface the entity for this node.

        Core facts are searched together with the name ("Min Cai University of
        Alberta"); outer hops are searched on their own, because the point is to
        surface for the topic without already knowing the name.
        """
        if node.queries:
            return node.queries
        if node.hop == 0:
            return [f"{self.name} {node.terms[0]}"]
        return [node.terms[0]]


def load_map(path: str | Path) -> KnowledgeMap:
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise MapError(f"cannot read knowledge map {path}: {exc}") from exc
    return parse_map(raw)


def parse_map(raw: dict[str, Any]) -> KnowledgeMap:
    entity = raw.get("entity") or {}
    if not entity.get("name"):
        raise MapError("knowledge map needs entity.name")

    nodes: list[Node] = []
    seen: set[str] = set()
    for item in raw.get("nodes", []):
        node_id = item.get("id")
        if not node_id or node_id in seen:
            raise MapError(f"node ids must be present and unique (got {node_id!r})")
        seen.add(node_id)
        hop = int(item.get("hop", 1))
        if hop not in HOP_WEIGHTS:
            raise MapError(f"node {node_id}: hop must be 0, 1 or 2")
        terms = [term for term in item.get("terms", []) if term]
        if not terms:
            raise MapError(f"node {node_id}: needs at least one term")
        nodes.append(
            Node(
                id=node_id,
                hop=hop,
                terms=terms,
                kind=item.get("kind", "fact"),
                fact=item.get("fact", ""),
                url=item.get("url"),
                venue=item.get("venue"),
                via=list(item.get("via", [])),
                queries=list(item.get("queries", [])),
            )
        )
    for node in nodes:
        missing = [ref for ref in node.via if ref not in seen]
        if missing:
            raise MapError(f"node {node.id}: unknown via {missing}")

    questions: list[Question] = []
    for index, item in enumerate(raw.get("questions", [])):
        if not item.get("q") or not item.get("answer_terms"):
            raise MapError(f"question {index}: needs q and answer_terms")
        node_ref = item.get("node")
        if node_ref and node_ref not in seen:
            raise MapError(f"question {index}: unknown node {node_ref}")
        hop = item.get("hop")
        if hop is None:
            hop = next((n.hop for n in nodes if n.id == node_ref), 0)
        questions.append(
            Question(
                id=item.get("id") or f"q{index + 1}",
                q=item["q"],
                answer_terms=list(item["answer_terms"]),
                node=node_ref,
                hop=int(hop),
            )
        )

    return KnowledgeMap(
        name=entity["name"],
        aliases=list(entity.get("aliases", [])),
        url=entity.get("url"),
        nodes=nodes,
        questions=questions,
        probes=list(raw.get("probes", [])),
        forbidden=list(raw.get("forbidden", [])),
        limits=dict(raw.get("limits", {})),
        scoring={key: float(value) for key, value in raw.get("scoring", {}).items()},
    )


def normalize(text: str) -> str:
    """Lowercase and collapse whitespace/dashes so term matching is forgiving."""
    text = text.lower()
    for dash in ("–", "—", "‐", "‑", "‒"):
        text = text.replace(dash, "-")
    return " ".join(text.split())


def contains_term(text: str, term: str) -> bool:
    return normalize(term) in normalize(text)


def contains_any(text: str, terms: list[str]) -> bool:
    return any(contains_term(text, term) for term in terms)
