"""Operaciones gráficas finitas compartidas por modelos DAG."""

def ancestors(seeds, parents, budget):
    closure = set(seeds)
    pending = sorted(closure)
    while pending:
        budget.tick()
        for parent in parents[pending.pop()]:
            if parent not in closure:
                closure.add(parent)
                pending.append(parent)
    return closure


def separated(left, right, given, parents, budget):
    """Criterio de separación en el grafo ancestral moralizado."""
    relevant = ancestors({left, right} | set(given), parents, budget)
    neighbors = {name: set() for name in relevant}
    for node in sorted(relevant):
        family = [node, *parents[node]]
        for index, member in enumerate(family):
            for peer in family[index + 1:]:
                budget.tick()
                neighbors[member].add(peer)
                neighbors[peer].add(member)
    visited = set(given) | {left}
    pending = [left]
    while pending:
        budget.tick()
        node = pending.pop()
        if node == right:
            return False
        unseen = neighbors[node] - visited
        visited.update(unseen)
        pending.extend(sorted(unseen))
    return True
