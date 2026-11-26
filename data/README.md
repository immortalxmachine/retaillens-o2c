# data/ - real Olist data (case study)

**Source:** [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce),
Kaggle `olistbr/brazilian-ecommerce`, by Olist. **Licence: CC BY-NC-SA 4.0**: attribution,
**non-commercial** use only, share-alike. These are real, anonymised orders from Brazilian
marketplaces (2016-2018). In this project they are used as a case study and mapped to SAP S/4HANA
SD structures (`docs/sap_mapping.md`).

- `raw/` holds the full Kaggle download (9 CSVs, about 120 MB). It is gitignored. Download it with
  `python -m src.download`, which uses the Kaggle CLI and your own Kaggle credentials; this
  project never stores them.
- `sample/` is committed. It is a small, deterministic slice of the **real** data (every order whose
  id starts with `0`, about 1/16 of all orders, plus all related rows). Review comment texts are
  blanked. CI and the tests use it, so CI needs no Kaggle credentials. Rebuild it with
  `python -m src.make_sample`.
- `retaillens.db` is the local SQLite database used when `DATABASE_URL` is not set (gitignored).
