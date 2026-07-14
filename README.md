# Molflow Sweep

Runs Molflow position sweeps. Has functionality to move facets in a geometry xml, runs a Molflow simulation using the CLI at each position, and then extract results to a csv.

Tested witn MolflowCLI 2.11.1 and Python 3.12 (standard libraries)


## Usage

### Config

To set up a sweep edit/ create a SweepConfig. 

```python\n
cfg = SweepConfig(
    molflow_exe=r"C:\path\to\molflowCLI.exe",
    base_geometry="my_geometry.xml",
    out_dir="sweep_runs",
    facets={
        "plate":     FacetRef("plate",     xml_id=211, csv_id=212),
        "deflector": FacetRef("deflector", xml_id=288, csv_id=289),
    },
    move_facets=["plate"],                  # gets moved during the sweep
    result_facets=["plate", "deflector"],   # gets saved to the summary
    axis=0,                                 # 0=x, 1=y, 2=z
    ndes: str = "1e6"            # number of desorbed test particles
    threads: str = "8"

    # Which facet_details.csv columns to save, {short_name: exact CSV header}.
    columns{
        "mc_hits":     "MC Hits",
        "equiv_abs":   "Equiv.abs.",
        "imping_rate": "Imping.rate",
    })

```

- molflow_exe: path to your molflowCLI.exe
- base_geometry: path to the original geometry you want to peform the sweep on
- out_dir: where you want results to be saved
- facets: dict of facets that will be involved in the simulation. This is where you assign a label to a facet, and match it with the ID in Molflow. Note that the csv_id matches the label in molflow gui, whilst the xml_id is one less (but worth checking).

- move_facets: list of the labels of facets you want to be swept together (only relevant for a single grid sweep, doesn't matter for custom sweeps)

- result_facets: list of the facets you want to save quantaties about. Note, in principle every facet detail is saved, but only facets you specify here get extracted to a sumarry file.

- axis: Which direction to sweep (0=x, 1=y, 2=z). (Again only relevant for a grid sweep)

- ndes: number of desorptions to run in the simulation ie how many particles to simulate.

- columns: a dictionary of facet properties you want to save, and what they are saved as.


Then create an instance with ```sweep = MolflowSweep(cfg)```

### Grid Sweep

A simple, one facet, grid sweep can be done by calling ```sweep.run_grid(positions) ```, where positions is a list of offsets to apply. 

#### Ouput

- position_sweep_summary.csv: a file containing the properties in columns for each facet in results_facets
- index.csv: a file containing which offsets were applied to each facet for each run
- run_*/results/facet_details.csv: full Molflow ouput for each run.

Furthermore, each mutated geometry is saved as geom_{run_id}.xml


### Multi Facet/ Custom Sweep

A custom sweep over multiple facets, can be implememted using ```sweep.evaluate(moves = (['plate'],0,0.5),run_id = "plate_x_0.5")``` . Pass a tuple with the label of the facet, the direction (0,1,2 for x,y,z) and the offset. This could then be put in you own loop. This returns a dict of raw values which can be stored in a list, and then saved with ```sweep.write_summarry()```. This returned dict can also then be used as an objective in an optomisation algorithm. 
