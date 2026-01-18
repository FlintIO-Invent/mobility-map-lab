# Architecture notes

## Core modeling loop

1. Ingest graph (OSMnx) → NetworkX MultiDiGraph
2. Add baseline edge attributes: `t0`, `capacity`
3. Generate OD demand (synthetic v1 → zones + calibrated v2)
4. Traffic assignment (BPR + MSA)
5. Compute metrics (delay, bottlenecks, fragility)
6. Scenario runner (apply change → re-assign → compare deltas)
7. Visualize + export

## Why MultiDiGraph?
Road networks can have parallel edges (e.g., divided roads, ramps). MultiDiGraph preserves this.

## MSA

**Method of Successive Approximations (MSA)** iteratively assigns traffic flows until user travel times stabilize, reaching equilibrium. Convergence means the system finds the best routes given congestion; researchers often plot the **relative gap** to show how quickly (or slowly) it converges.

### Key components and formula

**Formula (BPR volume–delay function):**

\[
T = T_{0}\times \left[1+\alpha \times \left(\frac{V}{C}\right)^{\beta}\right]
\]

**Where:**
- \(T\) — **Congested travel time**: actual time to traverse a road segment under current traffic.
- \(T_{0}\) — **Free-flow travel time**: time to traverse the segment with no traffic.
- \(V\) — **Volume**: observed traffic flow.
- \(C\) — **Capacity**: maximum flow the road can handle.
- \(\alpha\) — **Scaling parameter** (often \(0.15\)).
- \(\beta\) — **Shape parameter** (often \(4\)); higher values mean a sharper rise in congestion.

### How it works (congestion effect)

- **Low flow (\(V<C\))**: \(\left(\frac{V}{C}\right)^{\beta}\) is small, so \(T \approx T_{0}\).
- **Approaching capacity (\(V\rightarrow C\))**: \(\frac{V}{C}\rightarrow 1\), and \(T\) increases noticeably above \(T_{0}\).
- **Over capacity (\(V>C\))**: the function keeps increasing \(T\), representing severe congestion (even though real-world capacity has practical limits).

### Why it matters in traffic modeling

- **Route choice**: makes travel time (cost) sensitive to volume, influencing route decisions in assignment models.
- **Network performance**: helps evaluate infrastructure, signal timing, and demand management by showing how congestion affects travel times.
- **Calibration**: \(\alpha\) and \(\beta\) can be calibrated for specific road types/cities for better accuracy (even though standard defaults exist).

---

## BRP

The **BPR (Bureau of Public Roads) travel time function** is a widely used **volume–delay** function in traffic modeling. It calculates increased travel time as traffic volume approaches road capacity:

\[
T = T_{0}\times \left[1+\alpha \times \left(\frac{V}{C}\right)^{\beta}\right]
\]

**Where:**
- \(T\) is congested travel time,
- \(T_{0}\) is free-flow travel time,
- \(V\) is volume,
- \(C\) is capacity,
- \(\alpha\) (commonly \(0.15\)) and \(\beta\) (commonly \(4\)) control how quickly congestion “kicks in”.

It’s crucial for urban planning and traffic assignment because it links **traffic flow** to **travel cost**, enabling models to represent route choice and congestion impacts realistically.
