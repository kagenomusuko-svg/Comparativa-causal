"""Fragmentos de Legal idioms (Lagnado, Fenton y Neil, 2012, §§3.1–3.5)."""
from collections import defaultdict

from ..core import fields, label, labels, require
from ..core.graph import separated

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
        fields(pattern, "id kind roles provenance")
        name, kind = pattern["id"], pattern["kind"]
        require(label(name) and name not in seen and label(kind) and kind in PATTERNS, "Patrón inválido")
        seen.add(name)
        required, optional, section = PATTERNS[kind]
        roles = fields(pattern["roles"], required, optional)
        require(all(label(value) and value in states for value in roles.values()), "Variable de patrón desconocida")
        require(len(set(roles.values())) == len(roles), "Los roles del patrón deben corresponder a nodos distintos")
        labels(pattern["provenance"], nonempty=True)
        if kind == "opportunity_motive":
            edges = [(key, "hypothesis") for key in ("opportunity", "motive") if key in roles]
            require(bool(edges), "Se requiere oportunidad o motivo")
        elif kind == "alibi":
            edges = [("opportunity", "hypothesis"), ("opportunity", "report"),
                     ("hypothesis", "veracity"), ("veracity", "report")]
        else:
            edges = [(key, "report") for key in sorted(roles) if key != "report"]
        links = [[roles[parent], roles[child]] for parent, child in edges]
        for parent, child in links:
            added[child].add(parent)
        certificates.append(pattern | {"edges": links, "source": SOURCE, "section": section})
    return added, certificates


def verify(certificates, parents, budget):
    for item in certificates:
        if item["kind"] == "evidence_reliability":
            roles = item["roles"]
            require(separated(roles["target"], roles["reliability"], (), parents, budget),
                    "El patrón de fiabilidad simple exige independencia marginal entre objetivo y fiabilidad")
