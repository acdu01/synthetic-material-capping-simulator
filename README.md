# Synthetic Material Capping Simulation

`synthetic_material_capping_sim.py` is a small Python model for testing policy scenarios around capping synthetic material use in apparel. It reads stakeholder requirements from `requirements_table.csv`, simulates outcomes over time, and reports which targets look met or at risk.

## Files

- `synthetic_material_capping_sim.py`: simulation logic, CLI, and Tkinter dashboard
- `requirements_table.csv`: stakeholder requirements and target ranges used by the model

## Run

Use Python 3.10+.

```bash
python3 synthetic_material_capping_sim.py
```

Useful options:

```bash
python3 synthetic_material_capping_sim.py --scenario aggressive
python3 synthetic_material_capping_sim.py --years 5 --show-yearly
python3 synthetic_material_capping_sim.py --gui
```

Available scenarios:

- `balanced`
- `aggressive`
- `market-light`

## Output

The script prints:

- a short policy summary
- a 5 to 10 year outlook for key metrics
- a requirement pass rate
- a list of missed or at-risk stakeholder targets

If you pass `--show-yearly`, it also prints a compact year-by-year table. If you pass `--gui`, it opens a Tkinter dashboard with sliders for tuning the policy inputs.
