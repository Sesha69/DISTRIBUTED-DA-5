# Chord Lookup Protocol Simulation Report

## Title

Discrete-Event Simulation of the Chord Peer-to-Peer Lookup Protocol using SimPy and Streamlit

## Objective

To model a Chord Distributed Hash Table with `N` active peers, simulate hop-by-hop key lookups, study lookup latency as the network scales, and visualize routing behavior under stable conditions and under churn.

## Tools Used

- Python
- SimPy
- Streamlit
- Pandas
- Matplotlib

## Implementation Summary

The simulator represents a Chord ring in an `m`-bit identifier space. Each node stores:

- its identifier
- its predecessor and successor
- a finger table with `m` entries

For each finger entry `i`, the start value is:

`(n + 2^(i-1)) mod 2^m`

The simulator resolves each finger entry to the successor of that start value. A lookup begins at a chosen node and is forwarded hop-by-hop using the closest preceding finger rule until the key's owner is reached.

`SimPy` is used to model time. Every routing hop incurs a configurable latency, which lets the app measure end-to-end lookup time. Optional churn is modeled through scheduled join and leave events with a short stabilization delay.

## Visualizations

The Streamlit interface includes:

- a ring topology view of the Chord network
- an animated path of the message hops for a selected lookup
- a finger-table viewer for any selected node
- a scaling graph comparing average hop count with `log2(N)`
- a churn view showing lookup behavior while nodes join or leave

## Result

The scaling experiment shows that the average number of lookup hops grows much more slowly than the number of nodes and tracks the expected `O(log N)` behavior of Chord.

## How To Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## GitHub Repository URL

Add your GitHub repository link here after pushing the project:

`PASTE_GITHUB_REPOSITORY_URL_HERE`

## Submission Notes

1. Record a screen walkthrough while explaining the code and running the app.
2. Push the project to GitHub and replace the placeholder URL above.
3. Export this markdown file to PDF and upload that PDF to VTOP.
