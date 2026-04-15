# Chord Peer-to-Peer Lookup Protocol Simulator

This project builds a discrete-event simulation of the Chord Distributed Hash Table using `SimPy` and visualizes it with `Streamlit`.

## Features

- Models an `N`-node Chord ring inside an `m`-bit identifier space
- Builds successor links and finger tables for every node
- Simulates hop-by-hop key lookups with per-hop latency using `SimPy`
- Visualizes the Chord ring topology and animates the route taken by a lookup
- Displays the finger table for any selected node
- Compares lookup behavior with and without node join/departure churn
- Benchmarks average hop count as the network grows and shows its `O(log N)` trend

## Project Structure

- `app.py` - Streamlit dashboard
- `chord_sim/chord.py` - Chord data structures and SimPy simulation logic
- `REPORT.md` - Submission-ready markdown report
- `requirements.txt` - Python dependencies

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## What To Show In The Walkthrough

1. Explain how the ring is built and how successors and finger tables are computed.
2. Show a lookup from a chosen start node to a key owner.
3. Toggle churn on to show the impact of joins/departures.
4. Scroll to the scaling chart and explain why the average hop count follows `O(log N)`.

## Notes

- The app uses evenly spaced node identifiers to keep the topology easy to interpret.
- Churn is modeled as scheduled join/leave events plus a small stabilization delay.
- The scaling experiment runs repeated lookups across increasing ring sizes.
