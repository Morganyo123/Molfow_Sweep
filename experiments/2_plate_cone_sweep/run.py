import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))   # repo root

from molflow_sweep import FacetRef, SweepConfig, MolflowSweep

PLATE = ["plate_front", "plate_back"]


#cone has 36 facets, plus front and back, so 38 in total
CONE = ["cfront","cback","c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10","c11", "c12", "c13", "c14", "c15", "c16", "c17", "c18", "c19", "c20","c21", "c22", "c23", "c24", "c25", "c26", "c27", "c28", "c29", "c30", "c31", "c32", "c33", "c34", "c35", "c36"]

cfg = SweepConfig(
    molflow_exe=r"C:\Users\morga\Documents\molflow_win_2.11.1\molflow_win_2.11.1\molflowCLI.exe",
    base_geometry="geometries\\simplified_target_baseplate_cone.xml",
    out_dir=str(Path(__file__).resolve().parent / "sweep_runs"),

    facets={
        "plate_front": FacetRef("plate_front", xml_id=175, csv_id=176), #plate facet changed in this geometry
        "plate_back":  FacetRef("plate_back",  xml_id=176, csv_id=177),
        "deflector":   FacetRef("deflector",   xml_id=252, csv_id=253),
        "cfront":      FacetRef("cfront",      xml_id=255, csv_id=256),
        "cback":       FacetRef("cback",       xml_id=256, csv_id=257),
        "c1":          FacetRef("c1", xml_id=257, csv_id=258),
        "c2":          FacetRef("c2", xml_id=258, csv_id=259),
        "c3":          FacetRef("c3", xml_id=259, csv_id=260),
        "c4":          FacetRef("c4", xml_id=260, csv_id=261),
        "c5":          FacetRef("c5", xml_id=261, csv_id=262),
        "c6":          FacetRef("c6", xml_id=262, csv_id=263),
        "c7":          FacetRef("c7", xml_id=263, csv_id=264),
        "c8":          FacetRef("c8", xml_id=264, csv_id=265),
        "c9":          FacetRef("c9", xml_id=265, csv_id=266),
        "c10":         FacetRef("c10", xml_id=266, csv_id=267),
        "c11":         FacetRef("c11", xml_id=267, csv_id=268),
        "c12":         FacetRef("c12", xml_id=268, csv_id=269),
        "c13":         FacetRef("c13", xml_id=269, csv_id=270),
        "c14":         FacetRef("c14", xml_id=270, csv_id=271),
        "c15":         FacetRef("c15", xml_id=271, csv_id=272),
        "c16":         FacetRef("c16", xml_id=272, csv_id=273),
        "c17":         FacetRef("c17", xml_id=273, csv_id=274),
        "c18":         FacetRef("c18", xml_id=274, csv_id=275),
        "c19":         FacetRef("c19", xml_id=275, csv_id=276),
        "c20":         FacetRef("c20", xml_id=276, csv_id=277),
        "c21":         FacetRef("c21", xml_id=277, csv_id=278),
        "c22":         FacetRef("c22", xml_id=278, csv_id=279),
        "c23":         FacetRef("c23", xml_id=279, csv_id=280),
        "c24":         FacetRef("c24", xml_id=280, csv_id=281),
        "c25":         FacetRef("c25", xml_id=281, csv_id=282),
        "c26":         FacetRef("c26", xml_id=282, csv_id=283),
        "c27":         FacetRef("c27", xml_id=283, csv_id=284),
        "c28":         FacetRef("c28", xml_id=284, csv_id=285),
        "c29":         FacetRef("c29", xml_id=285, csv_id=286),
        "c30":         FacetRef("c30", xml_id=286, csv_id=287),
        "c31":         FacetRef("c31", xml_id=287, csv_id=288),
        "c32":         FacetRef("c32", xml_id=288, csv_id=289),
        "c33":         FacetRef("c33", xml_id=289, csv_id=290),
        "c34":         FacetRef("c34", xml_id=290, csv_id=291),
        "c35":         FacetRef("c35", xml_id=291, csv_id=292),
        "c36":         FacetRef("c36", xml_id=292, csv_id=293),
    },
    move_facets= CONE,                  # moved together
    result_facets=PLATE + CONE + ["deflector"],   # saved to summary

    axis=0,                       # 0=x, 1=y, 2=z
    ndes="1e5",
    threads="8",
    
)

sweep = MolflowSweep(cfg)

results = []


#sweep 10 plate positions, and for each plate position sweep 5 cone positions
#start geometry has plate and cone both offset from deflector by 0.5cm

for i in range(0,11):

    for j in range(0,5):

        plate_off = 0.5*i #steps of 0.5 cm for the plate
        
        #steps of 0.25 cm for the cone, starting at -0.25 cm relative to the plate 
        #to capture what happens if the plate is within the cone
        cone_off = plate_off + 0.25*j -0.25 

        row = sweep.evaluate(
        moves=[(PLATE, 0, plate_off),   # facets, axis, offset
               (CONE, 0, cone_off)],
        run_id=f"Plate_{plate_off}_Cone_{cone_off}")
        
        results.append(row)


print(f"Results: {results}")


sweep.write_summary(results, cfg.out_dir / "summary.csv")