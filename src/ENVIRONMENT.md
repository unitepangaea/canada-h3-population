# Environment (Phase A1)

Recorded 2026-11-06.

| Component | Version |
|---|---|
| OS | macOS 27.3 (Darwin, arm64) |
| Python | 3.13.6 |
| h3 (h3-py) | 4.5.0 |
| geopandas | 1.2.0 |
| shapely | 2.2.0 |
| GEOS | 3.14.1 |
| pyogrio / GDAL | 0.13.0 / 3.12.4 |
| pyproj / PROJ | 3.8.0 / 9.8.1 |
| pandas / numpy / pyarrow | 3.1.1 / 2.5.4 / 26.0.1 |

Full pinned list: `requirements.txt`.

## Location of the virtual environment

The v2 layers were built in a virtual environment kept outside the synced project folder, so
that package files were not synced. An equivalent environment can be created with:

```bash
uv venv --python 3.13 ~/.venvs/hexpops_v2
VIRTUAL_ENV=~/.venvs/hexpops_v2 uv pip install -r src/requirements.txt
```

## H3 v4 reference values (protocol 2.2)

From `h3.average_hexagon_area(r, "km^2")` and `h3.average_hexagon_edge_length(r, "km")`, h3 4.5.0:

| r | Mean area (km²) | Mean edge (km) |
|---|---|---|
| 6 | 36.129 | 3.725 |
| 7 | 5.161 | 1.406 |
| 8 | 0.737 | 0.531 |
