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
    ndes="1e2",
    threads="8",
)

sweep = MolflowSweep(cfg)

test_mode = 'grid' #change to 'multi' or 'optuna' to test other modes



#Simple 1D grid sweep 

if test_mode == 'grid':
    positions = [i * 0.5 for i in range(5)]        # 0.0 ... 10.0 cm
    sweep.run_grid(positions)



# Multi-facet search: evaluate() accepts any combination of moves, so you can
# place different facets independently in one trial:

if test_mode == 'multi':

    result = sweep.evaluate(
        moves=[(cfg.move_facets, 0, 1.5),
                (["deflector"], 2, -0.3)],
        run_id="plate1.5_defl-0.3",
    )
    print(result)   # dict of raw values, ready for Optuna or any other search loop
    results = [result]  # list of dicts, one per trial

    sweep.write_summary(results, path= cfg.out_dir / "position_sweep_summary.csv")   # append to summary CSV




# Optimisation (e.g. Optuna): evaluate() returns raw values immediately, so it
# works directly as an objective:

if test_mode == 'optuna':
    import optuna
    
    def objective(trial):
        off = trial.suggest_float("offset", 0.0, 10.0)
        r = sweep.evaluate([(cfg.move_facets, cfg.axis, off)],
                            run_id=f"opt_{trial.number}")
        return (r["plate_front_mc_hits"] + r["plate_back_mc_hits"]) / r["total_des"]

    study = optuna.create_study(direction="maximize",
                            sampler=optuna.samplers.TPESampler())
    study.optimize(objective, n_trials=30)
