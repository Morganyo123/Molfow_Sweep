"""
molflow_sweep — a small library for Molflow+ position sweeps.

What it does (and all it does):
  1. Move facets in a geometry XML and save the shifted file.
  2. Run molflowCLI on that file.
  3. Extract raw values from facet_details.csv into a summary CSV.

Derived metrics, plots, and analysis belong in your notebook, not here.

Typical use — see run_sweep_example.py:

    cfg   = SweepConfig(...)
    sweep = MolflowSweep(cfg)
    sweep.run_grid([0.0, 0.5, 1.0, ...])       # simple 1D sweep

Advanced use (multi-facet search / optimisation): call `evaluate()`
directly with any combination of moves:

    row = sweep.evaluate(
        moves=[(["plate_front", "plate_back"], 0, 1.5),   # facets, axis, offset
               (["deflector"],                 2, -0.3)],
        run_id="trial_007",
    )

`evaluate()` returns a plain dict of raw values, so it plugs straight into
an Optuna objective or any other search loop.
"""

import csv
import os
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Molflow geometry XML structure (fixed by the file format — do not edit):
#   <Geometry><Vertices><Vertex id= x= y= z=/></Vertices>
#             <Facets><Facet id=...><Indices><Indice vertex=.../></Indices>
# ---------------------------------------------------------------------------
VERTEX_TAG, VERTEX_ID = "Vertex", "id"
AXIS_KEYS             = ("x", "y", "z")
FACET_TAG, FACET_ID   = "Facet", "id"
INDICE_TAG, INDICE_V  = "Indice", "vertex"


@dataclass(frozen=True)
class FacetRef:
    """One facet, identified in BOTH numbering systems Molflow uses.

    xml_id: the <Facet id="..."> value in the geometry XML
    csv_id: the '#' column value in facet_details.csv
    (These differ — usually by 1. Conflating them causes silent bugs.)
    """
    name: str
    xml_id: int
    csv_id: int


@dataclass
class SweepConfig:
    """Everything you need to edit to run a sweep on YOUR geometry."""

    molflow_exe: Path            # full path to molflowCLI.exe
    base_geometry: Path          # your geometry XML file
    out_dir: Path                # where runs and the summary CSV go

    facets: dict                 # {name: FacetRef} — every facet you move or measure
    move_facets: list            # names moved together in run_grid()
    result_facets: list          # names whose values go into the summary CSV

    axis: int = 0                # 0=x, 1=y, 2=z — sweep axis for run_grid()
    ndes: str = "1e6"            # number of desorbed test particles
    threads: str = "8"

    # Which facet_details.csv columns to save, {short_name: exact CSV header}.
    # To track another quantity, add one line here — nothing else changes.
    columns: dict = field(default_factory=lambda: {
        "mc_hits":     "MC Hits",
        "equiv_abs":   "Equiv.abs.",
        "imping_rate": "Imping.rate",
    })

    def __post_init__(self):
        self.molflow_exe = Path(self.molflow_exe)
        self.base_geometry = Path(self.base_geometry)
        self.out_dir = Path(self.out_dir)
        if not self.molflow_exe.exists():
            raise FileNotFoundError(f"molflowCLI not found: {self.molflow_exe}")
        if not self.base_geometry.exists():
            raise FileNotFoundError(f"Geometry file not found: {self.base_geometry}")
        for name in list(self.move_facets) + list(self.result_facets):
            if name not in self.facets:
                raise ValueError(f"'{name}' is not defined in facets={list(self.facets)}")
        if self.axis not in (0, 1, 2):
            raise ValueError("axis must be 0 (x), 1 (y) or 2 (z)")


class MolflowSweep:
    """Runs Molflow simulations at shifted facet positions and collects results."""

    def __init__(self, config: SweepConfig):
        self.cfg = config

    # -- 1. GEOMETRY --------------------------------------------------------

    def write_shifted_geometry(self, out_path, moves):
        """Apply `moves` to the base geometry and save it to `out_path`.

        moves: list of (facet_names, axis, offset).
        Each move translates the union of vertices used by those facets;
        every vertex is shifted exactly once even if facets share vertices.
        """
        tree = ET.parse(self.cfg.base_geometry)
        root = tree.getroot()
        for facet_names, axis, offset in moves:
            vids = set()
            for name in facet_names:
                vids |= self._vertex_ids_of_facet(root, self.cfg.facets[name].xml_id)
            key = AXIS_KEYS[axis]
            for v in root.iter(VERTEX_TAG):
                if int(v.get(VERTEX_ID)) in vids:
                    v.set(key, f"{float(v.get(key)) + offset:.10g}")
        tree.write(out_path)

    @staticmethod
    def _vertex_ids_of_facet(root, xml_id):
        for facet in root.iter(FACET_TAG):
            if int(facet.get(FACET_ID)) == xml_id:
                return {int(i.get(INDICE_V)) for i in facet.iter(INDICE_TAG)}
        raise ValueError(f"XML facet id={xml_id} not found in geometry")

    # -- 2. SIMULATION ------------------------------------------------------

    def run_cli(self, geom_path, run_dir):
        """Run molflowCLI on `geom_path`; return path to facet_details.csv."""
        run_dir.mkdir(parents=True, exist_ok=True)
        cmd = [os.path.abspath(self.cfg.molflow_exe),
               "-f", os.path.abspath(geom_path),
               "-d", self.cfg.ndes, "-j", self.cfg.threads,
               "--reset", "--outputPath", "results",
               "--writeFacetDetails", "--noProgress"]
        print("  $", " ".join(cmd))
        subprocess.run(cmd, cwd=run_dir, check=True)
        return run_dir / "results" / "facet_details.csv"

    # -- 3. RESULTS ---------------------------------------------------------

    def extract(self, csv_path):
        """Read one facet_details.csv -> flat dict of raw values.

        Returns total_des (summed over all facets) plus, for every facet in
        result_facets, one entry per column in cfg.columns,
        e.g. 'plate_front_mc_hits'.
        """
        with open(csv_path, newline="") as f:
            rows = list(csv.DictReader(f))

        out = {"total_des": sum(_num(r["Des."]) for r in rows)}
        for name in self.cfg.result_facets:
            row = self._facet_row(rows, self.cfg.facets[name])
            for short, header in self.cfg.columns.items():
                if header not in row:
                    raise KeyError(f"Column '{header}' not in CSV. "
                                   f"Available: {list(row.keys())}")
                out[f"{name}_{short}"] = _num(row[header])
        return out

    @staticmethod
    def _facet_row(rows, facet):
        for r in rows:
            if int(float(r["#"])) == facet.csv_id:
                return r
        raise ValueError(f"{facet.name} (csv_id={facet.csv_id}) not found in "
                         f"{len(rows)}-row CSV")

    # -- ONE FULL TRIAL: geometry -> CLI -> results --------------------------

    def evaluate(self, moves, run_id):
        """Run one simulation with facets moved as specified.

        moves:  list of (facet_names, axis, offset) — see write_shifted_geometry
        run_id: any string/number unique to this trial (names the run folder)

        Returns a flat dict of raw values. This is the building block for
        grid sweeps, multi-facet searches, and optimisation loops alike.
        """
        run_dir = self.cfg.out_dir / f"run_{run_id}"
        geom = self.cfg.out_dir / f"geom_{run_id}.xml"
        self.cfg.out_dir.mkdir(parents=True, exist_ok=True)

        self.write_shifted_geometry(geom, moves)
        csv_path = self.run_cli(geom, run_dir)
        result = self.extract(csv_path)
        self._log_run(run_id, moves, str(run_dir))
        return result

    def _log_run(self, run_id, moves, run_dir):
        """Append to run_index.csv so saved runs can be re-analysed later."""
        index = self.cfg.out_dir / "run_index.csv"
        new = not index.exists()
        with open(index, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["run_id", "moves", "run_dir"])
            w.writerow([run_id, repr(moves), run_dir])

    # -- DRIVER: simple 1D grid sweep ----------------------------------------

    def run_grid(self, positions):
        """Sweep cfg.move_facets along cfg.axis over `positions` (list of
        offsets). Failed runs are recorded, not fatal. Writes summary CSV
        and returns the results as a list of dicts."""
        results = []
        for i, off in enumerate(positions):
            print(f"[{i + 1}/{len(positions)}] offset {off:+.3f}")
            row = {"offset": off, "error": None}
            try:
                row.update(self.evaluate([(self.cfg.move_facets, self.cfg.axis, off)],
                                         run_id=i))
            except Exception as e:
                row["error"] = str(e)
                print(f"    FAILED: {e}")
            results.append(row)

        self.write_summary(results, self.cfg.out_dir / "position_sweep_summary.csv")
        return results

    def write_summary(self, results, path):
        """Write list-of-dicts to CSV. Columns adapt to whatever keys exist."""
        keys = set()
        for r in results:
            keys.update(r.keys())
        first = [k for k in ("offset", "run_id") if k in keys]
        ordered = first + sorted(keys - set(first) - {"error"}) + ["error"]
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=ordered)
            w.writeheader()
            w.writerows(results)
        print(f"\nSummary written to {path}")


def _num(val):
    """CSV cell -> float, blank -> 0.0."""
    return float(val) if val not in (None, "") else 0.0
