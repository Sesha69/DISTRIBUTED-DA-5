from chord_sim import ChordNetwork


def main() -> None:
    network = ChordNetwork.evenly_spaced(node_count=16, m_bits=6, hop_latency=1.0)
    result = network.simulate_lookup(start_node=0, key=37)
    print("Path:", result.path)
    print("Owner:", result.owner_node)
    print("Hops:", result.hop_count)
    print("Latency:", result.latency)
    print("Scaling sample:", network.benchmark_scaling(lookup_count=8))


if __name__ == "__main__":
    main()
