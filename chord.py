from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import simpy


def is_in_interval(value: int, start: int, end: int, modulo: int, *, inclusive_end: bool = False) -> bool:
    if start == end:
        return True
    if start < end:
        return start < value <= end if inclusive_end else start < value < end
    if inclusive_end:
        return value > start or value <= end
    return value > start or value < end


@dataclass
class Node:
    node_id: int
    m_bits: int
    successor: Optional[int] = None
    predecessor: Optional[int] = None
    finger_table: List[int] = field(default_factory=list)

    @property
    def keyspace_size(self) -> int:
        return 2**self.m_bits

    def finger_starts(self) -> List[int]:
        return [(self.node_id + 2**i) % self.keyspace_size for i in range(self.m_bits)]


@dataclass
class LookupResult:
    key: int
    start_node: int
    owner_node: int
    path: List[int]
    latency: float
    events: List[Dict[str, float | int | str]]

    @property
    def hop_count(self) -> int:
        return max(0, len(self.path) - 1)


class ChordNetwork:
    def __init__(self, m_bits: int, node_ids: Sequence[int], hop_latency: float = 1.0):
        self.m_bits = m_bits
        self.keyspace_size = 2**m_bits
        self.hop_latency = hop_latency
        unique_ids = sorted({node_id % self.keyspace_size for node_id in node_ids})
        if not unique_ids:
            raise ValueError("Chord network needs at least one node.")
        self.nodes: Dict[int, Node] = {node_id: Node(node_id=node_id, m_bits=m_bits) for node_id in unique_ids}
        self.rebuild()

    @classmethod
    def evenly_spaced(cls, node_count: int, m_bits: int, hop_latency: float = 1.0) -> "ChordNetwork":
        keyspace_size = 2**m_bits
        if node_count > keyspace_size:
            raise ValueError("Node count cannot exceed the key space size.")
        step = max(1, keyspace_size // node_count)
        node_ids: List[int] = []
        candidate = 0
        while len(node_ids) < node_count:
            node_id = candidate % keyspace_size
            if node_id not in node_ids:
                node_ids.append(node_id)
            candidate += step
        return cls(m_bits=m_bits, node_ids=node_ids, hop_latency=hop_latency)

    def sorted_node_ids(self) -> List[int]:
        return sorted(self.nodes)

    def rebuild(self) -> None:
        ids = self.sorted_node_ids()
        for index, node_id in enumerate(ids):
            node = self.nodes[node_id]
            node.successor = ids[(index + 1) % len(ids)]
            node.predecessor = ids[(index - 1) % len(ids)]
            node.finger_table = [self.find_successor(start) for start in node.finger_starts()]

    def add_node(self, node_id: int) -> None:
        node_id %= self.keyspace_size
        if node_id in self.nodes:
            return
        self.nodes[node_id] = Node(node_id=node_id, m_bits=self.m_bits)
        self.rebuild()

    def remove_node(self, node_id: int) -> None:
        if len(self.nodes) <= 1:
            return
        self.nodes.pop(node_id, None)
        self.rebuild()

    def find_successor(self, key: int) -> int:
        key %= self.keyspace_size
        ids = self.sorted_node_ids()
        for node_id in ids:
            if key <= node_id:
                return node_id
        return ids[0]

    def owner_of_key(self, key: int) -> int:
        return self.find_successor(key)

    def closest_preceding_finger(self, current_id: int, key: int) -> int:
        current = self.nodes[current_id]
        for finger in reversed(current.finger_table):
            if finger == current_id:
                continue
            if is_in_interval(finger, current_id, key, self.keyspace_size):
                return finger
        return current.successor if current.successor is not None else current_id

    def route_lookup(self, start_node: int, key: int, env: simpy.Environment) -> LookupResult:
        if start_node not in self.nodes:
            raise KeyError(f"Unknown start node: {start_node}")

        path = [start_node]
        events: List[Dict[str, float | int | str]] = []
        current_id = start_node
        key %= self.keyspace_size

        while True:
            current = self.nodes[current_id]
            successor = current.successor if current.successor is not None else current_id

            if current_id == successor or is_in_interval(key, current_id, successor, self.keyspace_size, inclusive_end=True):
                owner = successor
                break

            next_hop = self.closest_preceding_finger(current_id, key)
            if next_hop == current_id:
                owner = successor
                break

            hop_start = env.now
            yield env.timeout(self.hop_latency)
            events.append(
                {
                    "from": current_id,
                    "to": next_hop,
                    "start": hop_start,
                    "end": env.now,
                    "label": f"{current_id} -> {next_hop}",
                }
            )
            current_id = next_hop
            path.append(current_id)

        if path[-1] != owner:
            hop_start = env.now
            yield env.timeout(self.hop_latency)
            events.append(
                {
                    "from": current_id,
                    "to": owner,
                    "start": hop_start,
                    "end": env.now,
                    "label": f"{current_id} -> {owner}",
                }
            )
            path.append(owner)

        return LookupResult(
            key=key,
            start_node=start_node,
            owner_node=owner,
            path=path,
            latency=env.now,
            events=events,
        )

    def simulate_lookup(self, start_node: int, key: int) -> LookupResult:
        env = simpy.Environment()
        result_box: Dict[str, LookupResult] = {}

        def runner() -> simpy.events.Event:
            result = yield env.process(self.route_lookup(start_node, key, env))
            result_box["lookup"] = result

        env.process(runner())
        env.run()
        return result_box["lookup"]

    def simulate_lookup_with_churn(
        self,
        start_node: int,
        key: int,
        churn_events: Sequence[Dict[str, int | float | str]],
        stabilization_delay: float = 0.5,
    ) -> LookupResult:
        env = simpy.Environment()
        result_box: Dict[str, LookupResult] = {}

        def churn_worker() -> simpy.events.Event:
            for event in sorted(churn_events, key=lambda item: float(item["time"])):
                wait = float(event["time"]) - env.now
                if wait > 0:
                    yield env.timeout(wait)
                action = str(event["action"])
                node_id = int(event["node_id"])
                if action == "join":
                    self.add_node(node_id)
                elif action == "leave":
                    self.remove_node(node_id)
                yield env.timeout(stabilization_delay)

        def runner() -> simpy.events.Event:
            result = yield env.process(self.route_lookup(start_node, key, env))
            result_box["lookup"] = result

        env.process(churn_worker())
        env.process(runner())
        env.run()
        return result_box["lookup"]

    def benchmark_scaling(self, lookup_count: int = 32) -> List[Dict[str, float | int]]:
        sizes = [4, 8, 16, 32, 64]
        results: List[Dict[str, float | int]] = []
        for size in sizes:
            if size > self.keyspace_size:
                continue
            network = ChordNetwork.evenly_spaced(node_count=size, m_bits=self.m_bits, hop_latency=self.hop_latency)
            ids = network.sorted_node_ids()
            total_hops = 0
            total_latency = 0.0
            for lookup_index in range(lookup_count):
                start_node = ids[lookup_index % len(ids)]
                key = (lookup_index * 7 + 3) % network.keyspace_size
                result = network.simulate_lookup(start_node=start_node, key=key)
                total_hops += result.hop_count
                total_latency += result.latency
            results.append(
                {
                    "nodes": size,
                    "avg_hops": total_hops / lookup_count,
                    "avg_latency": total_latency / lookup_count,
                    "log2_nodes": size.bit_length() - 1,
                }
            )
        return results

    def finger_table_rows(self, node_id: int) -> List[Dict[str, int]]:
        node = self.nodes[node_id]
        return [
            {"entry": index + 1, "start": start, "successor": successor}
            for index, (start, successor) in enumerate(zip(node.finger_starts(), node.finger_table))
        ]

    def ring_edges(self) -> List[tuple[int, int]]:
        edges: List[tuple[int, int]] = []
        for node_id in self.sorted_node_ids():
            successor = self.nodes[node_id].successor
            if successor is not None:
                edges.append((node_id, successor))
        return edges
