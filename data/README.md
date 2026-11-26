# data/ - SYNTHETIC DATA

**Everything in this folder is synthetic.** No real company, customer or SAP system is involved.

- `raw/` - CSV extracts in SAP S/4HANA SD table structures (KNA1, MARA, MAKT, VBAK, VBAP, LIKP,
  LIPS, VBRK, VBRP, BSAD, RETURNS), written by `src/generate.py`. Gitignored because it is fully
  reproducible: `python -m src.generate` (or the whole pipeline, `python -m src.pipeline`).
- `raw/_dq_injected.json` - the data-quality issues that were planted on purpose.
- `retaillens.db` - the local SQLite database used when `DATABASE_URL` is not set (gitignored).

Field meanings, simulated patterns and the injected issues: [`docs/data_dictionary.md`](../docs/data_dictionary.md).
