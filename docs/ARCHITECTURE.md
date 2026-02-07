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

Awesome — now that it runs, your next step is to **understand the mental model** and then grow the codebase without turning it into spaghetti.

Here’s the “how it works” in plain terms, then a growth roadmap.

---

## The mental model of this project

### 1) You have 3 layers

**A) Data layer (`data/`)**

- Stores **artifacts** so you don’t rebuild everything each run:
  - `graph.gpickle` = canonical engine graph
  - `graph.graphml` = shareable graph
  - `nodes/edges.parquet` = tables for dashboards/DB
  - `results_*.parquet` = outputs

**B) Engine layer (`src/sxm_mobility/`)**

- Reusable library code:
  - build graph, assign flows, evaluate scenarios
- Should never depend on Streamlit or Django.

**C) Delivery layer (`scripts/`, later `streamlit`, later `django`)**

- Entry points that run the engine and write artifacts.
- Streamlit/Django will mostly **read results** + **trigger scenario runs**.

This separation is what lets you scale.

---

## What you’re actually doing (traffic-wise)

### Step 1 — Represent roads as a graph

- Nodes = intersections  
- Edges = road segments  
- Each edge gets attributes like:
  - `t0` free-flow travel time
  - `capacity`
  - `time` congested travel time (changes with flow)
  - `flow` vehicles/hour assigned

### Step 2 — Create demand (OD)

OD = “how many trips from origin to destination”  
This is the *cause* of traffic.

Without OD demand, you only have a road map, not “traffic”.

### Step 3 — Assign demand to routes (flow assignment)

You’re doing an iterative loop (MSA style):

1. Compute edge travel times from current flow (BPR)
2. For each OD pair:
   - find shortest path using current travel times
   - push OD demand along that path
3. Blend new flows into current flows and repeat

Output:

- flow per edge
- congested travel time per edge
- system KPIs (total travel time, total delay)

### Step 4 — Find bottlenecks / criticality

From the baseline results you can identify:

- edges with high `flow/capacity`
- edges with high total delay: `flow * (time - t0)`
- nodes with high “through-flow” importance

### Step 5 — Scenario testing

A “scenario” is just a graph modification:

- add edge
- change capacity
- close edge
- change direction

Then rerun assignment and compare KPIs:

- baseline delay vs scenario delay
- rank scenarios by improvement

That’s your “which links reduce traffic most?” engine.

---

## How to grow the codebase safely (rules)

### Rule 1: Keep the engine pure

In `src/sxm_mobility/`:

- no printing
- no reading from hardcoded paths
- accept inputs (graphs, OD tables, settings)
- return outputs (DataFrames, dict metrics)

Scripts handle I/O.

### Rule 2: Make everything data-driven

Avoid “magic constants” buried in code:

- store scenario configs, OD configs, parameters in YAML/JSON or Pydantic settings:
  - BPR alpha/beta
  - MSA iterations
  - OD volumes
  - scenario list

### Rule 3: Treat artifacts as contracts

Once you choose:

- `edges.parquet` schema
- `results_baseline.parquet` schema

…don’t break them casually. Add new columns instead of renaming.

This makes Streamlit/Django stable.

---

## A practical growth roadmap (what to build next)

### Phase 1 — Make the baseline “credible”

**Add these outputs:**

- Edge KPIs table:
  - `u,v,key, flow, capacity, v_c_ratio, t0, time, delay`
- Node KPIs table:
  - intersection importance proxy (sum incident delays)
- Map export:
  - top 20 bottleneck edges as GeoJSON (for quick visualization)

**Add validation checks:**

- graph connectedness report
- missing capacity or speed assumptions report

---

### Phase 2 — Improve OD generation (biggest realism jump)

Right now OD may be synthetic. Upgrade it by adding “zones”:

- Create zones: Airport, Simpson Bay, Philipsburg, Cole Bay, etc.
- Map nodes to zones (spatial join / bounding polygons)
- Build OD using:
  - population density proxies
  - POI density
  - or stakeholder-supplied weights

Deliverable:

- `od.parquet` + `zones.geojson`

---

### Phase 3 — Make scenario selection smart (not manual)

Instead of “try random edges”, generate candidates:

**Candidate generation ideas:**

- Connect pairs of zones that currently have long travel times
- Connect nodes near bottleneck corridors to create bypasses
- Identify “bridge edges” (high betweenness, high delay) and propose alternative paths around them

Then run top N candidates and rank.

This becomes your “we recommend building X and Y” feature.

---

### Phase 4 — Move from demo to product (Django + Streamlit)

**Streamlit = fast stakeholder demo**

- load results tables
- scenario picker dropdown
- map + KPI deltas

**Django = institutional platform**

- users/roles (VROMI, TEATT, Justice, consultants)
- scenario library (store scenario configs)
- audit log of runs
- export “consultation packs” (PDF summary)

---

## What to read in your code to understand it quickly

1. `scripts/build_graph.py`  
   → shows how artifacts are produced

2. `src/sxm_mobility/assignment/msa.py`  
   → this is the heart of traffic flow simulation

3. `src/sxm_mobility/scenarios/runner.py`  
   → how interventions are applied + evaluated

4. `scripts/run_baseline.py` and `scripts/run_scenarios.py`  
   → show “how engine outputs become artifacts”

---

## Quick exercise to confirm you understand it

Change **one thing** and see the impact:

- double capacity on a known corridor
- rerun baseline and scenarios
- confirm system delay drops and that corridor’s `v/c` improves

That’s the best way to build intuition.

---

If you paste your current folder tree (`tree -L 3`) and the names of your key modules (`msa.py`, `bpr.py`, `runner.py`), I’ll walk you through your code path like a “trace”:

**build_graph → export → od → msa loop → metrics → parquet outputs**

…and point to exactly where you should add:

- better capacities
- time-of-day demand
- zone-based OD
- candidate link generation

## Data Set  element meanings
That JSON object is **one road segment (one edge)** from your road network graph, exported to a table-friendly format.

Think of it as: **an edge from node `u` to node `v`**, with metadata pulled from OpenStreetMap.

Here’s what each field means:

---

## Identity / graph structure

- **`u: 250656239`**  
  The **start node ID** (an OSM node id for an intersection/point).

- **`v: 1033360634`**  
  The **end node ID**.

- **`key: 0`**  
  Because your graph is a **MultiDiGraph**, there can be multiple parallel edges between the same `u` and `v` (e.g., ramps, service lanes). `key` distinguishes them. `0` means “the first one”.

---

## Road source IDs and classification

- **`osmid: "550465100"`**  
  The OpenStreetMap way ID for this road segment.  
  It’s a **string** here because we normalized it for Parquet/Arrow compatibility (sometimes it’s a list when edges get merged).

- **`highway: "primary"`**  
  OSM road type. `"primary"` usually means a main arterial road.

- **`name: "Airport Road"`**  
  The road name from OSM.

---

## Directionality

- **`oneway: true`**  
  This edge is one-way **from `u` → `v`**.

- **`reversed: "False"`**  
  This is typically an OSMnx bookkeeping flag indicating whether the geometry was reversed relative to original OSM direction during processing.  
  It being a **string** `"False"` (not boolean `False`) is due to the same “make everything safe for parquet” conversion.

---

## Geometry / distance

- **`length: 19.160143489700733`**  
  Length of this edge in **meters** (OSMnx calculates this).

- **`geometry_wkt: "LINESTRING (...)"`**  
  The actual line geometry of the road segment in **WKT** format.  
  These coordinates are **(longitude, latitude)**:

  - `(-63.119977, 18.040484)` → `(-63.120091, 18.04051)` → `(-63.12015, 18.040535)`

  This lets you render it easily in:

  - GeoPandas/Shapely (parse WKT)
  - PostGIS
  - Plotly/Mapbox
  - Leaflet/Folium
  - QGIS

---

## Capacity-ish proxies (not yet “traffic-ready”)

- **`lanes: "1"`**  
  Lane count from OSM (often missing or string-typed).

- **`maxspeed: "nan"`**  
  Missing value. Same for:

  - **`bridge`**, **`junction`**, **`access`**  
    These were blank in OSM for this segment; they became `"nan"` strings during export.

---

## What this edge *doesn’t* include yet (for traffic simulation)

To simulate congestion and flow properly, you’ll typically add derived attributes like:

- **`speed_kph`** (from `maxspeed` or OSMnx defaults)
- **`t0`** free-flow travel time (seconds) = `length / speed`
- **`capacity`** vehicles/hour (estimated from `highway`, `lanes`, urban assumptions)
- **`flow`** assigned vehicles/hour (result of your OD assignment)
- **`time`** congested time after BPR function

Right now this row is mainly **network geometry + metadata**, which is correct for ingestion/export.

---

## Small quality note

You’ve got some fields as strings that ideally should be typed:

- `lanes` should be numeric (int)
- `reversed` should be boolean
- `"nan"` should be actual nulls

It’s not “wrong” — it’s the tradeoff we made to get Parquet exports stable. If you want, we can keep the table cleaner by:

- preserving `u,v,key` as ints,
- converting `lanes` to int when possible,
- leaving missing values as `None` instead of `"nan"`.

---

## How to render this visually (quick idea)

In Streamlit you can parse `geometry_wkt` and plot it on a map:

- Folium: convert to coordinate pairs and add as a PolyLine
- Plotly: add as a line trace on OpenStreetMap tiles

If you tell me whether you’re using **Folium** or **Plotly**, I’ll give you a short snippet that takes rows like this and renders them (including coloring by `delay` once your flows are non-zero).
