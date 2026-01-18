# SXM Mobility Graph Lab - SXM Mobility Graph Lab

**SXM Mobility Graph Lab** is a practical decision-support initiative that transforms Sint Maarten’s road system into a **NetworkX-powered mobility model**. Using open road network data and locally available inputs (counts, observations, stakeholder feedback), the project simulates traffic flows, measures congestion and network fragility, and pinpoints the **intersections and corridors that most influence island-wide travel time and safety outcomes**.

The lab then runs “what-if” scenarios—such as new connector roads, direction changes, capacity upgrades, incident/closure tests, and safety-focused redesigns—to produce a ranked list of **short-term actions** and **longer-term infrastructure priorities**, supported by consultation-ready maps and visuals that the public and partners can understand and validate.

### What it produces (quick bullets)

- **Baseline congestion map** + top bottlenecks (edges) and critical intersections (nodes)
- **Scenario ranking**: which new links/route changes reduce delay the most
- **Resilience tests**: what happens if a key road is blocked (accident/works)
- **Safety overlay**: risk-priority corridors near schools, crossings, high-conflict junctions
- **Consultation visuals**: simple maps + “before/after” impact summaries for stakeholders


## Dependency “extras” (install only what you need)

- **geo** → osmnx, geopandas, shapely, pyproj *(OSM network + spatial)*
- **viz** → plotly, folium *(maps/plots)*
- **dashboard** → streamlit *(UI)*
- **api** → fastapi, uvicorn *(scenario API)*
- **jobs** → celery, redis *(async runs later)*
- **db** → sqlalchemy, psycopg *(Postgres/PostGIS later)*
- **dev** → ruff, black, pytest, pre-commit, mypy *(tooling)*

---

## Repo structure (already created)

### `src/sxm_mobility/` modules
- **network/** *(build/simplify/edge attributes)*
- **demand/** *(OD generation)*
- **assignment/** *(BPR + MSA + metrics)*
- **scenarios/** *(catalog/runner/evaluator)*
- **viz/** *(mapping helpers)*
- **api/** *(FastAPI app scaffold)*

### `scripts/` runnable entry points
- **build_graph.py** *(OSMnx → GraphML)*
- **run_baseline.py** *(bottlenecks + fragility)*
- **run_scenarios.py** *(example scenario ranking)*
- **streamlit_app.py** *(starter dashboard)*

### Tests + docs
- **tests/** *(basic unit tests for assignment + metrics)*
- **docs/ARCHITECTURE.md** *(quick overview)*


## Quick start (uv)

```bash
# 1) Create venv + install core + dev tools
uv sync --extra dev --extra geo --extra viz --extra dashboard


# 2) Run tests
uv run pytest

# Build graph + exports
# Baseline KPIs + bottlenecks
# Scenario ranking outputs
uv run python scripts/build_graph.py
uv run python scripts/run_baseline.py
uv run python scripts/run_scenarios.py

# Optional dashboard
uv run streamlit run scripts/streamlit_app.py

# 4) (Optional) Run API
uv sync --extra api
uv run uvicorn sxm_mobility.api.app:app --reload
```

## Dependency groups (pick what you need)

- **core**: network + assignment primitives
- **geo**: OSMnx + GeoPandas stack
- **viz**: Plotly/Folium mapping helpers
- **dashboard**: Streamlit app
- **api**: FastAPI server
- **jobs**: Celery + Redis for long-running scenario runs
- **db**: Postgres/PostGIS connectivity
- **dev**: ruff, black, pytest, pre-commit, mypy


Install extras via:

```bash
uv sync --extra geo --extra viz --extra dev
```

## Repo layout

```text
sxm-mobility-graph-lab/
  data/                  # local datasets (ignored by git)
  docs/                  # notes, architecture, decisions
  notebooks/             # exploration
  scripts/               # runnable entrypoints
  src/sxm_mobility/      # library code
  tests/                 # tests
```

## Suggested first prototype steps

1. `scripts/build_graph.py` → download OSM road network and save to `data/processed/`.
2. `scripts/run_baseline.py` → run baseline metrics + fragility checks.
3. `scripts/run_scenarios.py` → generate candidate interventions and rank impacts.

## License

MIT (adjust as needed).
