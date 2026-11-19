# Agent notes

Work from the repository root.

```bash
python3 run_all.py
```

- Python 3.9+.
- Standard library only; do not add dependencies.
- `run_all.py` runs 57 tests and 8 examples.
- Expected final line: `SignalLab: 57 tests, 8 examples passed`.
- Outputs are deterministic for a fixed Python version.
- Do not edit or weaken `tests/` to make a failure disappear.
- If the environment writes bytecode caches, set `PYTHONDONTWRITEBYTECODE=1`.
