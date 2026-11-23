"""Fragmentos de Legal idioms (Lagnado, Fenton y Neil, 2012, §§3.1–3.5)."""
from collections import defaultdict

from ..core import fields, label, labels, require
from ..core.graph import separated

from . import legal_2013

SOURCE = "10.1080/19462166.2012.682656"
PATTERNS = {
    "evidence": ("target report", "", "3.1"),
    "evidence_reliability": ("target report reliability", "", "3.2"),
    "opportunity_motive": ("hypothesis", "opportunity motive", "3.3"),
    "testimony_components": ("target report sensitivity objectivity veracity", "", "3.4"),
    "alibi": ("opportunity hypothesis veracity report", "", "3.5"),
}


def expand(patterns, states, budget):
    require(type(patterns) is list, "idioms debe ser una lista")
    added = defaultdict(set)
    certificates = []
    seen = set()
    for pattern in patterns:
        budget.tick()
        fields(pattern, "id kind roles provenance", "settings")
        name, kind = pattern["id"], pattern["kind"]
        require(label(name) and name not in seen and label(kind) and kind in (PATTERNS.keys() | legal_2013.PATTERNS.keys()), "Patrón inválido")
        seen.add(name)
        if kind in legal_2013.PATTERNS:
            required, optional, section, edges = legal_2013.PATTERNS[kind]
            source = legal_2013.DOI
        else:
            required, optional, section = PATTERNS[kind]
            source = SOURCE
        roles = fields(pattern["roles"], required, optional)
        names = legal_2013.role_nodes(roles)
        require(all(label(value) and value in states for value in names), "Variable de patrón desconocida")
        require(len(set(names)) == len(names), "Los roles del patrón deben corresponder a nodos distintos")
        labels(pattern["provenance"], nonempty=True)
        settings = legal_2013.settings_for(kind, pattern.get("settings", {}), roles, states)
        if source == legal_2013.DOI:
            if kind == "dependent_evidence" and "dependency" in roles:
                edges = edges + [("dependency", "second_report")]
        elif kind == "opportunity_motive":
            edges = [(key, "hypothesis") for key in ("opportunity", "motive") if key in roles]
            require(bool(edges), "Se requiere oportunidad o motivo")
        elif kind == "alibi":
            edges = [("opportunity", "hypothesis"), ("opportunity", "report"),
                     ("hypothesis", "veracity"), ("veracity", "report")]
        else:
            edges = [(key, "report") for key in sorted(roles) if key != "report"]
        links = legal_2013.links_for(kind, roles, edges)
        for parent, child in links:
            added[child].add(parent)
        certificates.append(pattern | {"edges": links, "source": source, "section": section, "settings": settings})
    return added, certificates


def verify(certificates, parents, budget):
    legal_2013.validate_graph(certificates, parents, budget)
    for item in certificates:
        if item["kind"] == "evidence_reliability":
            roles = item["roles"]
            require(separated(roles["target"], roles["reliability"], (), parents, budget),
                    "El patrón de fiabilidad simple exige independencia marginal entre objetivo y fiabilidad")
