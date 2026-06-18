"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   TÉLÉCHARGEMENT DES DONNÉES RÉELLES — UEMOA 2000-2024                       ║
║   Mémoire : Prévision du crédit bancaire (Comparaison Économétrie vs ML)     ║
║   Auteur  : Jasmine GBOLOGANGBE | ESGIS | Master IA & Big Data               ║
╚══════════════════════════════════════════════════════════════════════════════╝

INSTRUCTIONS D'EXÉCUTION :
--------------------------
1. Installer les dépendances :
   pip install requests pandas openpyxl

2. Lancer le script :
   python download_data.py

3. Les fichiers seront créés dans le dossier ./data/

DONNÉES COLLECTÉES (toutes publiques, World Bank API officielle) :
- Crédit privé / PIB (variable cible)
- Taux de croissance du PIB
- Inflation IPC
- Masse monétaire M2 / PIB
- Recettes fiscales / PIB
- Dette publique / PIB
- Indicateurs de gouvernance (WGI)
- Population, urbanisation
"""

import sys
import os
import time
from datetime import datetime

# Optional imports with clear error messages to help the user fix missing packages
try:
    import requests
except ImportError:
    print("Missing dependency: requests. Install with `pip install requests`")
    sys.exit(1)

try:
    import pandas as pd
except ImportError:
    print("Missing dependency: pandas. Install with `pip install pandas openpyxl`")
    sys.exit(1)

# ─── Configuration ─────────────────────────────────────────
PAYS_UEMOA = {
    'BEN': 'Bénin',
    'BFA': 'Burkina Faso',
    'CIV': "Côte d'Ivoire",
    'GNB': 'Guinée-Bissau',
    'MLI': 'Mali',
    'NER': 'Niger',
    'SEN': 'Sénégal',
    'TGO': 'Togo'
}

ANNEE_DEBUT = 2000
ANNEE_FIN = 2024

# Dossier de sortie
OUTPUT_DIR = "./data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── Indicateurs World Bank — codes officiels ─────────────
INDICATEURS = {
    # === VARIABLE CIBLE ===
    'FS.AST.PRVT.GD.ZS': 'credit_prive_pib',  # Crédit privé / PIB (%)

    # === VARIABLES MACROÉCONOMIQUES ===
    'NY.GDP.MKTP.KD.ZG': 'pib_croissance',  # Croissance PIB réel (%)
    'NY.GDP.PCAP.KD.ZG': 'pib_par_habitant_croissance',  # Croissance PIB/hab (%)
    'FP.CPI.TOTL.ZG': 'inflation_ipc',  # Inflation IPC (%)
    'FM.LBL.BMNY.GD.ZS': 'masse_monetaire_m2_pib',  # M2 / PIB (%)
    
    # === VARIABLES BUDGÉTAIRES ===
    'GC.TAX.TOTL.GD.ZS': 'recettes_fiscales_pib',  # Recettes fiscales / PIB
    'GC.DOD.TOTL.GD.ZS': 'dette_publique_pib',  # Dette publique / PIB
    
    # === VARIABLES COMMERCIALES ===
    'NE.TRD.GNFS.ZS': 'ouverture_commerciale',  # Commerce / PIB
    'BX.KLT.DINV.WD.GD.ZS': 'ide_pib',  # IDE / PIB
    
    # === VARIABLES DÉMOGRAPHIQUES ===
    'SP.POP.TOTL': 'population_totale',  # Population totale
    'SP.URB.TOTL.IN.ZS': 'urbanisation',  # Population urbaine (%)
    'SP.POP.GROW': 'croissance_population',  # Croissance pop (%)
    
    # === INCLUSION FINANCIÈRE ===
    'FB.CBK.BRCH.P5': 'agences_bancaires_100k',  # Agences/100k adultes
    'FB.ATM.TOTL.P5': 'atm_100k',  # ATM/100k adultes
}


def telecharger_indicateur(code_indicateur, code_pays, debut, fin):
    """
    Télécharge un indicateur pour un pays via l'API World Bank.
    
    Returns:
        pandas.DataFrame avec colonnes [iso3, pays, annee, valeur]
    """
    url = (
        f"https://api.worldbank.org/v2/country/{code_pays}/indicator/{code_indicateur}"
        f"?format=json&date={debut}:{fin}&per_page=200"
    )
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print(f"   Erreur HTTP {response.status_code} pour {code_pays} / {code_indicateur}  ")
            return pd.DataFrame()
        
        data = response.json()
        if not data or len(data) < 2 or not data[1]:
            return pd.DataFrame()
        
        records = []
        for record in data[1]:
            if record.get('value') is not None:
                records.append({
                    'iso3': record['countryiso3code'],
                    'pays': record['country']['value'],
                    'annee': int(record['date']),
                    'valeur': float(record['value'])
                })
        
        return pd.DataFrame(records)
    
    except Exception as e:
        print(f" Erreur : {e}")
        return pd.DataFrame()


def main():
    print("=" * 70)
    print("  TÉLÉCHARGEMENT DONNÉES UEMOA 2000-2024")
    print(f"  Lancé le {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("=" * 70)
    
    # Stockage des données par indicateur
    donnees_par_indicateur = {}
    
    # Boucle sur tous les indicateurs
    for code_indic, nom_variable in INDICATEURS.items():
        print(f"\n Téléchargement : {nom_variable} ({code_indic})")
        
        toutes_donnees = []
        for code_pays, nom_pays in PAYS_UEMOA.items():
            df_pays = telecharger_indicateur(code_indic, code_pays, ANNEE_DEBUT, ANNEE_FIN)
            if not df_pays.empty:
                toutes_donnees.append(df_pays)
                print(f"{nom_pays} : {len(df_pays)} obs.")
            else:
                print(f" {nom_pays} : aucune donnée")
            time.sleep(0.3)  # Respect rate limit
        
        if toutes_donnees:
            df_combine = pd.concat(toutes_donnees, ignore_index=True)
            df_combine = df_combine.rename(columns={'valeur': nom_variable})
            donnees_par_indicateur[nom_variable] = df_combine
    
    # ─── Construction du panel final ──────────────────────────
    print("\n" + "=" * 70)
    print(" CONSTRUCTION DU PANEL FINAL")
    print("=" * 70)
    
    # Squelette : tous les pays × toutes les années
    pays_annees = [
        (iso3, nom, annee)
        for iso3, nom in PAYS_UEMOA.items()
        for annee in range(ANNEE_DEBUT, ANNEE_FIN + 1)
    ]
    df_final = pd.DataFrame(pays_annees, columns=['iso3', 'pays', 'annee'])
    
    # Joindre chaque indicateur
    for nom_var, df_var in donnees_par_indicateur.items():
        df_final = df_final.merge(
            df_var[['iso3', 'annee', nom_var]],
            on=['iso3', 'annee'],
            how='left'
        )
    
    df_final = df_final.sort_values(['iso3', 'annee'])
    
    # Statistiques de complétude
    n_total = len(df_final)
    n_vars = len(df_final.columns) - 3
    n_cellules = n_total * n_vars
    n_manquantes = df_final.drop(columns=['iso3', 'pays', 'annee']).isna().sum().sum()
    pct_completude = round(100 * (1 - n_manquantes / n_cellules), 1)
    
    print(f"\n Panel final : {n_total} observations × {len(df_final.columns)} colonnes")
    print(f"Complétude : {pct_completude}% ({n_manquantes} valeurs manquantes)")
    
    # ─── Exports ──────────────────────────────────────────────
    csv_path = f"{OUTPUT_DIR}/uemoa_panel_2000_2024.csv"
    excel_path = f"{OUTPUT_DIR}/uemoa_panel_2000_2024.xlsx"
    
    df_final.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Onglet 1 : Panel complet
        df_final.to_excel(writer, sheet_name='Panel_UEMOA', index=False)
        
        # Onglet 2 : Focus Bénin
        df_benin = df_final[df_final['iso3'] == 'BEN'].copy()
        df_benin.to_excel(writer, sheet_name='Bénin', index=False)
        
        # Onglet 3 : Statistiques descriptives
        df_stats = df_final.describe().T
        df_stats.to_excel(writer, sheet_name='Statistiques')
        
        # Onglet 4 : Métadonnées
        meta = pd.DataFrame([
            {'Variable': nom, 'Code WB': code, 'Source': 'World Bank WDI'}
            for code, nom in INDICATEURS.items()
        ])
        meta.to_excel(writer, sheet_name='Métadonnées', index=False)
    
    print(f"\n CSV   : {csv_path}")
    print(f" Excel : {excel_path}")
    
    # ─── Aperçu Bénin ─────────────────────────────────────────
    print("\n APERÇU — Bénin (5 dernières années)")
    print("-" * 70)
    cols_show = ['annee', 'credit_prive_pib', 'pib_croissance', 'inflation_ipc']
    cols_show = [c for c in cols_show if c in df_final.columns]
    print(df_final[df_final['iso3'] == 'BEN'][cols_show].tail(5).to_string(index=False))
    
    print("\n" + "=" * 70)
    print(" TÉLÉCHARGEMENT TERMINÉ ")
    print(f"  Dossier : {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 70)
    
    return df_final


if __name__ == "__main__":
    df = main()
    
    # Affichage des variables avec leur complétude
    print("\n TAUX DE COMPLÉTUDE PAR VARIABLE :")
    print("-" * 70)
    for col in df.columns:
        if col not in ['iso3', 'pays', 'annee']:
            n_valides = df[col].notna().sum()
            pct = round(100 * n_valides / len(df), 1)
            statut = "OK" if pct >= 80 else "WARNING" if pct >= 50 else "CRITICAL"
            print(f"  {statut} {col:<35} : {pct:>5}% ({n_valides}/{len(df)})")
