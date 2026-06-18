# Prévision du crédit bancaire dans la zone UEMOA (2000–2024)

**Mémoire de Master 2 IA & Big Data — ESGIS, 2025-2026**
Auteure : Akoua Robertine Jasmine GBOLOGANGBE

## Titre

> Évaluation comparative de modèles économétriques et de machine learning pour la prévision du crédit bancaire dans la zone UEMOA : application au cas du Bénin (2000–2024)

## Structure du projet

```
uemoa_credit_forecast/
├── collects/
│   ├── download_data.py        # Collecte World Bank WDI
│   └── collect_phase2.py       # Collecte IMF + WGI + BCEAO
├── data/
│   ├── panel_uemoa_complet.csv # Panel principal (8 pays × 25 ans × 28 vars)
│   └── raw/                    # Données brutes par source
├── figures/
│   ├── memoire/                # Figures 300 DPI pour le mémoire
│   └── *.png                   # Figures analyses
└── notebooks/
    ├── 01_exploration.ipynb            # Stats descriptives, corrélations
    ├── 02_tests_statistiques.ipynb     # Tests ADF/KPSS, Mundlak, Breusch-Pagan
    ├── 03_modeles_econometriques.ipynb # ARDL (Bénin) + Panel FE (UEMOA)
    ├── 04_ml_models.ipynb              # Random Forest + XGBoost + SHAP
    ├── 05_comparaison_finale.ipynb     # Tableau comparatif + interprétation
    └── 06_dashboard.ipynb              # Dashboard + exports mémoire
```

## Modèles

| Modèle | Périmètre | RMSE test | R² test |
|--------|-----------|-----------|---------|
| ARDL | Bénin (T=24) | 3.07 | -3.44 |
| Panel FE | UEMOA N=8 | 2.42 | 0.877 |
| **Random Forest** | **UEMOA N=8** | **1.83** | **0.930** |
| XGBoost | UEMOA N=8 | 2.01 | 0.915 |

## Environnement

```bash
conda activate uemoa
jupyter notebook
```

Packages clés : `statsmodels 0.14`, `linearmodels 7.0`, `scikit-learn 1.9`, `xgboost 3.2`, `shap 0.51`

## Sources des données

- **World Bank WDI** : crédit privé/PIB, M2/PIB, ouverture commerciale, IDE
- **IMF WEO** : PIB, inflation, dette publique, solde budgétaire
- **World Bank WGI** : indicateurs de gouvernance (source=3, codes `GOV_WGI_*.EST`)
- **BCEAO** : taux directeur (zone commune)
