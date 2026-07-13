from molflow_sweep import FacetRef, SweepConfig, MolflowSweep

cfg = SweepConfig(
    molflow_exe=r"C:\Users\morga\Documents\molflow_win_2.11.1\molflow_win_2.11.1\molflowCLI.exe",
    base_geometry="simplified_target_baseplate.xml",
    out_dir="sweep_runs",

    facets={
        "plate_front": FacetRef("plate_front", xml_id=211, csv_id=212),
        "plate_back":  FacetRef("plate_back",  xml_id=212, csv_id=213),
        "deflector":   FacetRef("deflector",   xml_id=288, csv_id=289),
    },
    move_facets=["plate_front", "plate_back"],                  # moved together
    result_facets=["plate_front", "plate_back", "deflector"],   # saved to summary

    axis=0,                       # 0=x, 1=y, 2=z
    ndes="1e6",
    threads="8",
)

sweep = MolflowSweep(cfg)

#--- Simple 1D grid sweep ---------------------------------------------------
positions = [i * 0.5 for i in range(21)]        # 0.0 ... 10.0 cm
sweep.run_grid(positions)





