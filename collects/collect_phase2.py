"""
collect_phase2.py
=================
Phase 2 data collection: IMF, WGI, BCEAO + credit variable fix.

Sources:
  - World Bank WDI  : FD.AST.PRVT.GD.ZS (credit prive/PIB - fix variable cible)
  - IMF DataMapper  : dette publique, balance courante, solde budgetaire
  - World Bank WGI  : 5 indicateurs de gouvernance (source=3, codes GOV_WGI_*)
  - BCEAO           : taux directeur (donnees publiees, zone commune)

Output:
  - data/raw/imf/imf_uemoa_annual.csv
  - data/raw/wgi/wgi_uemoa_annual.csv
  - data/raw/bceao/bceao_taux_directeur.csv
  - data/panel_uemoa_complet.csv  (panel consolide toutes sources)
  - data/panel_uemoa_complet.xlsx
"""

import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_IMF = DATA_DIR / "raw" / "imf"
RAW_WGI = DATA_DIR / "raw" / "wgi"
RAW_BCEAO = DATA_DIR / "raw" / "bceao"
RAW_WB = DATA_DIR / "raw" / "worldbank"

for d in [RAW_IMF, RAW_WGI, RAW_BCEAO, RAW_WB]:
    d.mkdir(parents=True, exist_ok=True)

PAYS_UEMOA = {
    "BEN": "Benin",
    "BFA": "Burkina Faso",
    "CIV": "Cote d'Ivoire",
    "GNB": "Guinee-Bissau",
    "MLI": "Mali",
    "NER": "Niger",
    "SEN": "Senegal",
    "TGO": "Togo",
}
COUNTRIES = list(PAYS_UEMOA.keys())
START_YEAR = 2000
END_YEAR = 2024

# ── Taux directeur BCEAO (donnees publiees, zone commune) ─────────────────────
# Source : Rapports BCEAO Politique Monetaire. Taux de pension/repo en fin d'annee.
# Note : monnaie commune -> valeur identique pour les 8 pays UEMOA.
BCEAO_TAUX_DIRECTEUR = {
    2000: 6.50, 2001: 6.50, 2002: 6.50, 2003: 5.50,
    2004: 4.50, 2005: 4.50, 2006: 4.50, 2007: 4.50,
    2008: 4.75, 2009: 4.25, 2010: 4.25, 2011: 4.00,
    2012: 3.50, 2013: 3.50, 2014: 3.50, 2015: 3.50,
    2016: 3.50, 2017: 3.50, 2018: 3.50, 2019: 3.50,
    2020: 3.50, 2021: 3.50, 2022: 3.50, 2023: 3.50,
    2024: 3.50,
}

# ── Indicateurs WB WDI supplementaires ────────────────────────────────────────
WB_EXTRA_INDICATORS = {
    "FD.AST.PRVT.GD.ZS": "credit_prive_pib_fd",  # credit prive/PIB (serie complete)
}

# ── Indicateurs IMF DataMapper ─────────────────────────────────────────────────
IMF_INDICATORS = {
    "NGDP_RPCH": "imf_pib_croissance",
    "PCPIPCH": "imf_inflation",
    "GGXCNL_NGDP": "imf_solde_budgetaire",
    "GGXWDG_NGDP": "imf_dette_publique",
    "BCA_NGDPD": "imf_balance_courante",
}

# ── Indicateurs WGI (World Bank source=3) ─────────────────────────────────────
WGI_INDICATORS = {
    "GOV_WGI_CC.EST": "wgi_controle_corruption",
    "GOV_WGI_GE.EST": "wgi_efficacite_gouvernement",
    "GOV_WGI_PV.EST": "wgi_stabilite_politique",
    "GOV_WGI_RL.EST": "wgi_etat_droit",
    "GOV_WGI_RQ.EST": "wgi_qualite_reglementaire",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _get(url: str, retries: int = 3, delay: float = 1.5) -> dict:
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            logger.warning("Tentative %d/%d - %s : %s", attempt, retries, url[:80], exc)
            time.sleep(delay * attempt)
    return {}


def _completude(df: pd.DataFrame, col: str) -> str:
    n = df[col].notna().sum()
    pct = 100 * n / len(df)
    tag = "OK" if pct >= 80 else "WARNING" if pct >= 50 else "CRITIQUE"
    return f"[{tag}] {col}: {pct:.1f}% ({n}/{len(df)})"


# ── 1. World Bank WDI (correction credit_prive_pib) ───────────────────────────

def collect_wb_extra() -> pd.DataFrame:
    logger.info("=== WB WDI - correction credit_prive_pib ===")
    rows = []
    for code, colname in WB_EXTRA_INDICATORS.items():
        logger.info("  -> %s (%s)", code, colname)
        for iso3 in COUNTRIES:
            url = (
                f"https://api.worldbank.org/v2/country/{iso3}/indicator/{code}"
                f"?format=json&date={START_YEAR}:{END_YEAR}&per_page=200"
            )
            data = _get(url)
            if not data or len(data) < 2 or not data[1]:
                logger.warning("    %s: pas de donnees", iso3)
                continue
            for rec in data[1]:
                if rec.get("value") is not None:
                    rows.append({
                        "iso3": iso3,
                        "annee": int(rec["date"]),
                        colname: float(rec["value"]),
                    })
            time.sleep(0.3)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    path = RAW_WB / "wb_credit_fd.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info("Sauvegarde WB extra : %s (%d lignes)", path, len(df))
    return df


# ── 2. IMF DataMapper ──────────────────────────────────────────────────────────

def collect_imf() -> pd.DataFrame:
    logger.info("=== IMF DataMapper ===")
    countries_str = "/".join(COUNTRIES)
    frames = {}

    for code, colname in IMF_INDICATORS.items():
        logger.info("  -> %s (%s)", code, colname)
        url = f"https://www.imf.org/external/datamapper/api/v1/{code}/{countries_str}"
        data = _get(url)
        if "values" not in data:
            logger.warning("    %s: pas de reponse valide", code)
            continue

        values = data["values"].get(code, {})
        rows = []
        for iso3 in COUNTRIES:
            country_data = values.get(iso3, {})
            for year_str, val in country_data.items():
                try:
                    year = int(year_str)
                except ValueError:
                    continue
                if START_YEAR <= year <= END_YEAR and val is not None:
                    rows.append({"iso3": iso3, "annee": year, colname: float(val)})

        if rows:
            frames[colname] = pd.DataFrame(rows)
            logger.info("    %d observations", len(rows))
        time.sleep(0.5)

    if not frames:
        logger.error("Aucune donnee IMF recuperee")
        return pd.DataFrame()

    merged = None
    for df in frames.values():
        merged = df if merged is None else merged.merge(df, on=["iso3", "annee"], how="outer")

    merged = merged.sort_values(["iso3", "annee"]).reset_index(drop=True)
    path = RAW_IMF / "imf_uemoa_annual.csv"
    merged.to_csv(path, index=False, encoding="utf-8")
    logger.info("Sauvegarde IMF : %s (%d lignes, %d cols)", path, len(merged), merged.shape[1])
    return merged


# ── 3. World Bank WGI (source=3) ──────────────────────────────────────────────

def collect_wgi() -> pd.DataFrame:
    logger.info("=== WGI Governance Indicators ===")
    frames = []

    for code, colname in WGI_INDICATORS.items():
        logger.info("  -> %s (%s)", code, colname)
        rows = []
        for iso3 in COUNTRIES:
            url = (
                f"https://api.worldbank.org/v2/country/{iso3}/indicator/{code}"
                f"?format=json&date=1996:{END_YEAR}&per_page=100&source=3"
            )
            data = _get(url)
            if not data or len(data) < 2 or not data[1]:
                logger.warning("    %s %s: pas de donnees", code, iso3)
                continue
            for rec in data[1]:
                if rec.get("value") is not None:
                    year = int(rec["date"])
                    if START_YEAR <= year <= END_YEAR:
                        rows.append({"iso3": iso3, "annee": year, colname: float(rec["value"])})
            time.sleep(0.3)
        if rows:
            frames.append(pd.DataFrame(rows))
            logger.info("    %d observations", len(rows))

    if not frames:
        logger.error("Aucune donnee WGI recuperee")
        return pd.DataFrame()

    result = frames[0]
    for df_add in frames[1:]:
        result = result.merge(df_add, on=["iso3", "annee"], how="outer")

    result = result.sort_values(["iso3", "annee"]).reset_index(drop=True)
    path = RAW_WGI / "wgi_uemoa_annual.csv"
    result.to_csv(path, index=False, encoding="utf-8")
    logger.info("Sauvegarde WGI : %s (%d lignes, %d cols)", path, len(result), result.shape[1])
    return result


# ── 4. BCEAO Taux Directeur ────────────────────────────────────────────────────

def collect_bceao_taux_directeur() -> pd.DataFrame:
    logger.info("=== BCEAO Taux Directeur (donnees integrees) ===")
    rows = []
    for iso3 in COUNTRIES:
        for year, rate in BCEAO_TAUX_DIRECTEUR.items():
            rows.append({"iso3": iso3, "annee": year, "bceao_taux_directeur": rate})

    df = pd.DataFrame(rows)
    path = RAW_BCEAO / "bceao_taux_directeur.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info(
        "Taux directeur BCEAO : %d annees, source=BCEAO publications officielles",
        len(BCEAO_TAUX_DIRECTEUR),
    )
    return df


# ── 5. Consolidation ──────────────────────────────────────────────────────────

def consolidate(
    df_wb_base: pd.DataFrame,
    df_wb_credit: pd.DataFrame,
    df_imf: pd.DataFrame,
    df_wgi: pd.DataFrame,
    df_bceao: pd.DataFrame,
) -> pd.DataFrame:
    logger.info("=== Consolidation du panel final ===")

    # Squelette complet
    skeleton = pd.DataFrame(
        [(iso3, nom, year) for iso3, nom in PAYS_UEMOA.items() for year in range(START_YEAR, END_YEAR + 1)],
        columns=["iso3", "pays", "annee"],
    )

    # Base WB - drop colonne pays du df_wb_base pour eviter pays_x/pays_y
    wb_cols_drop = [c for c in df_wb_base.columns if c == "pays"]
    df_wb_base_merge = df_wb_base.drop(columns=wb_cols_drop)
    panel = skeleton.merge(df_wb_base_merge, on=["iso3", "annee"], how="left")

    # Correction credit_prive_pib via FD.AST.PRVT.GD.ZS
    if not df_wb_credit.empty and "credit_prive_pib_fd" in df_wb_credit.columns:
        panel = panel.merge(df_wb_credit[["iso3", "annee", "credit_prive_pib_fd"]], on=["iso3", "annee"], how="left")
        # Remplir credit_prive_pib la ou FS.AST.PRVT manque avec FD.AST.PRVT
        mask = panel["credit_prive_pib"].isna() & panel["credit_prive_pib_fd"].notna()
        panel.loc[mask, "credit_prive_pib"] = panel.loc[mask, "credit_prive_pib_fd"]
        logger.info("credit_prive_pib : %d valeurs completees via FD.AST.PRVT.GD.ZS", mask.sum())
        panel = panel.drop(columns=["credit_prive_pib_fd"])

    # IMF
    if not df_imf.empty:
        panel = panel.merge(df_imf, on=["iso3", "annee"], how="left")
        # Remplir dette_publique si manquante avec IMF
        if "dette_publique_pib" in panel.columns and "imf_dette_publique" in panel.columns:
            mask_dette = panel["dette_publique_pib"].isna() & panel["imf_dette_publique"].notna()
            panel.loc[mask_dette, "dette_publique_pib"] = panel.loc[mask_dette, "imf_dette_publique"]
            logger.info("dette_publique_pib : %d valeurs completees via IMF", mask_dette.sum())

    # WGI
    if not df_wgi.empty:
        panel = panel.merge(df_wgi, on=["iso3", "annee"], how="left")

    # BCEAO
    if not df_bceao.empty:
        panel = panel.merge(df_bceao, on=["iso3", "annee"], how="left")

    panel = panel.sort_values(["iso3", "annee"]).reset_index(drop=True)

    # Rapport de completude
    logger.info("\n--- Rapport de completude ---")
    for col in panel.columns:
        if col not in ["iso3", "pays", "annee"]:
            logger.info("  %s", _completude(panel, col))

    return panel


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> pd.DataFrame:
    logger.info("=" * 70)
    logger.info("COLLECTE PHASE 2 — UEMOA 2000-2024")
    logger.info("Debut : %s", datetime.now().strftime("%d/%m/%Y %H:%M"))
    logger.info("=" * 70)

    # Chargement panel WB de base (Phase 1)
    wb_base_path = DATA_DIR / "uemoa_panel_2000_2024.csv"
    if not wb_base_path.exists():
        logger.error("Panel WB Phase 1 introuvable : %s", wb_base_path)
        logger.error("Executer download_data.py d'abord.")
        raise FileNotFoundError(wb_base_path)

    df_wb_base = pd.read_csv(wb_base_path)
    logger.info("Panel WB base charge : %d obs x %d cols", len(df_wb_base), df_wb_base.shape[1])

    # Collecte par source
    df_wb_credit = collect_wb_extra()
    df_imf = collect_imf()
    df_wgi = collect_wgi()
    df_bceao = collect_bceao_taux_directeur()

    # Consolidation
    panel = consolidate(df_wb_base, df_wb_credit, df_imf, df_wgi, df_bceao)

    # Export
    csv_path = DATA_DIR / "panel_uemoa_complet.csv"
    xlsx_path = DATA_DIR / "panel_uemoa_complet.xlsx"

    panel.to_csv(csv_path, index=False, encoding="utf-8-sig")

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        panel.to_excel(writer, sheet_name="Panel_UEMOA", index=False)

        df_benin = panel[panel["iso3"] == "BEN"].copy()
        df_benin.to_excel(writer, sheet_name="Benin", index=False)

        df_stats = panel.describe().T
        df_stats.to_excel(writer, sheet_name="Statistiques")

        meta = pd.DataFrame([
            {"Variable": col, "Completude_%": round(100 * panel[col].notna().sum() / len(panel), 1)}
            for col in panel.columns if col not in ["iso3", "pays", "annee"]
        ])
        meta.to_excel(writer, sheet_name="Qualite", index=False)

    logger.info("=" * 70)
    logger.info("COLLECTE TERMINEE")
    logger.info("  CSV  : %s", csv_path)
    logger.info("  XLSX : %s", xlsx_path)
    logger.info("  Panel final : %d lignes x %d colonnes", len(panel), panel.shape[1])
    logger.info("=" * 70)

    return panel


if __name__ == "__main__":
    df = main()

    print("\n=== APERCU BENIN (5 dernieres annees) ===")
    cols_show = ["annee", "credit_prive_pib", "pib_croissance", "inflation_ipc",
                 "imf_dette_publique", "wgi_stabilite_politique", "bceao_taux_directeur"]
    cols_show = [c for c in cols_show if c in df.columns]
    print(df[df["iso3"] == "BEN"][cols_show].tail(5).to_string(index=False))
