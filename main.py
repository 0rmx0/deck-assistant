#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MTG Deck Builder – Commandeur (Refactorisé)
Version 26.02.01
Version avec séparation des responsabilités et élimination de duplication.
"""

import sys
import csv
import requests
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QPushButton,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QHeaderView,
    QSizePolicy,
    QProgressBar,
)
from PySide6.QtCore import Qt, QThread, Signal


# ========== CONSTANTES ==========

VERSION = "26.02.01"

COLOR_SYMBOLS = {
    "W": "⚪",  # Blanc
    "U": "🔵",  # Bleu
    "B": "⚫",  # Noir
    "R": "🔴",  # Rouge
    "G": "🟢",  # Vert
    "C": "⭕",  # Incolore
}

CSV_MAPPING = {
    "Card Name": "nom",
    "Set Code": "set_code",
    "Set Name": "set_name",
    "Collector Number": "collector_number",
    "Rarity": "rarity",
    "Language": "language",
    "Quantity": "quantity",
    "Condition": "condition",
    "Finish": "finish",
    "Altered": "altered",
    "Signed": "signed",
    "Misprint": "misprint",
    "Price (USD)": "price_usd",
    "Price (EUR)": "price_eur",
    "Price (USD Foil)": "price_usd_foil",
    "Price (EUR Foil)": "price_eur_foil",
    "Price (USD Etched)": "price_usd_etched",
    "Price (EUR Etched)": "price_eur_etched",
    "Scryfall ID": "scryfall_id",
    "Container Type": "container_type",
    "Container Name": "container_name",
}

NUMERIC_FIELDS = [
    "quantity",
    "price_usd",
    "price_eur",
    "price_usd_foil",
    "price_eur_foil",
    "price_usd_etched",
    "price_eur_etched",
]

# Scores de synergie
MAX_SYNERGY_SCORE = 6


# ========== CLASSES MÉTIER ==========

@dataclass
class Carte:
    """Représente une carte Magic."""
    nom: str
    couleur: List[str]
    type: str
    cout_mana: str
    oracle_text_en: str
    oracle_text_fr: str
    scryfall_id: str = ""
    quantity: float = 1.0
    
    def est_legendaire(self) -> bool:
        return "Legendary" in self.type
    
    def est_incolore(self) -> bool:
        return not self.couleur


class ClientScryfall:
    """Interface pour l'API Scryfall."""
    
    BASE_URL = "https://api.scryfall.com/cards"
    TIMEOUT = 10
    
    @classmethod
    def par_nom_fuzzy(cls, nom: str) -> Dict[str, Any]:
        """Récupère une carte par nom fuzzy."""
        try:
            url = f"{cls.BASE_URL}/named?fuzzy={nom}"
            resp = requests.get(url, timeout=cls.TIMEOUT)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}
    
    @classmethod
    def par_id(cls, scryfall_id: str) -> Dict[str, Any]:
        """Récupère une carte par ID."""
        try:
            url = f"{cls.BASE_URL}/{scryfall_id}"
            resp = requests.get(url, timeout=cls.TIMEOUT)
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}
    
    @classmethod
    def _extraire_oracle_text_fr(cls, data: Dict[str, Any], oracle_en: str) -> str:
        """Extrait le texte Oracle en français (sans traduction automatique)."""
        prints_uri = data.get("prints_search_uri")
        if prints_uri:
            try:
                r = requests.get(prints_uri, timeout=8)
                if r.status_code == 200:
                    for print_data in r.json().get("data", []):
                        if print_data.get("lang") == "fr" and print_data.get("oracle_text"):
                            return print_data.get("oracle_text")
            except Exception:
                pass
        
        return ""
    
    @classmethod
    def enrichir_carte(cls, carte: Dict[str, Any]) -> None:
        """Enrichit une carte avec les données Scryfall (mutation sur place)."""
        if carte.get("scryfall_id"):
            data = cls.par_id(carte["scryfall_id"])
        else:
            data = cls.par_nom_fuzzy(carte.get("nom", ""))

        if data:
            oracle_en = data.get("oracle_text", "")
            oracle_fr = cls._extraire_oracle_text_fr(data, oracle_en)
            
            carte.update({
                "scryfall_id": data.get("id", ""),
                "couleur": data.get("color_identity", []),
                "type": data.get("type_line", ""),
                "cout_mana": data.get("mana_cost", ""),
                "oracle_text_en": oracle_en,
                "oracle_text_fr": oracle_fr,
            })


class ChargeurCSV:
    """Gère le chargement et la normalisation des fichiers CSV."""
    
    @staticmethod
    def valider_colonnes(fieldnames: List[str]) -> None:
        """Lève une exception si des colonnes manquent."""
        manquantes = [col for col in CSV_MAPPING.keys() if col not in fieldnames]
        if manquantes:
            raise ValueError(f"Colonnes manquantes : {', '.join(manquantes)}")
    
    @staticmethod
    def normaliser_ligne(ligne: Dict[str, str]) -> Dict[str, Any]:
        """Normalise une ligne CSV."""
        carte: Dict[str, Any] = {
            interne: ligne[externe].strip()
            for externe, interne in CSV_MAPPING.items()
        }

        for champ in NUMERIC_FIELDS:
            try:
                carte[champ] = float(carte[champ]) if carte[champ] else 0.0
            except ValueError:
                carte[champ] = 0.0

        return carte
    
    @staticmethod
    def charger(chemin: str, callback_progression) -> List[Dict[str, Any]]:
        """Charge et normalise le CSV."""
        collection: List[Dict[str, Any]] = []

        with open(chemin, mode="r", encoding="utf-8") as f:
            lecteur = csv.DictReader(f)
            ChargeurCSV.valider_colonnes(lecteur.fieldnames)

            lignes = list(lecteur)
            if not lignes:
                raise ValueError("Le fichier CSV est vide.")

            for idx, ligne in enumerate(lignes, start=1):
                carte = ChargeurCSV.normaliser_ligne(ligne)
                collection.append(carte)
                callback_progression(int((idx / len(lignes)) * 100))

        return collection


class CalculatriceSynergie:
    """Calcule la synergie entre une carte et un commandant."""
    
    @staticmethod
    def calculer(carte: Dict[str, Any], commandeur: Dict[str, Any]) -> float:
        """Retourne un score de synergie en pourcentage (0-100)."""
        score = 0
        
        # Bonus légendaire
        if "Legendary" in carte.get("type", ""):
            score += 3
        
        # Bonus incolore
        if not carte.get("couleur"):
            score += 1
        
        # Bonus couleurs compatibles
        couleurs_carte = set(carte.get("couleur", []))
        couleurs_commandeur = set(commandeur.get("couleur", []))
        if couleurs_carte.issubset(couleurs_commandeur):
            score += 2
        
        return round((score / MAX_SYNERGY_SCORE) * 100, 1)


class GestionnairesCouleurs:
    """Gère les conversions et symboles de couleurs."""
    
    @staticmethod
    def couleurs_a_symboles(couleurs: List[str]) -> str:
        """Convertit les lettres de couleur en symboles."""
        if not couleurs:
            return COLOR_SYMBOLS["C"]
        return "".join(COLOR_SYMBOLS.get(c, c) for c in couleurs)
    
    @staticmethod
    def filtrer_par_couleurs(
        collection: List[Dict[str, Any]],
        couleurs_autorisees: List[str],
    ) -> List[Dict[str, Any]]:
        """Filtre les cartes par identité couleur."""
        if not couleurs_autorisees:
            return collection

        couleurs_set = set(couleurs_autorisees)
        
        def valide(carte: Dict[str, Any]) -> bool:
            if not carte.get("couleur"):  # incolore
                return True
            return set(carte["couleur"]).issubset(couleurs_set)
        
        return [c for c in collection if valide(c)]


# ========== WORKER THREAD ==========

class ImportWorker(QThread):
    """Worker pour charger le CSV et enrichir via Scryfall."""
    
    progression = Signal(int)
    fini = Signal(list)
    erreur = Signal(str)

    def __init__(self, chemin_fichier: str):
        super().__init__()
        self.chemin_fichier = chemin_fichier

    def run(self) -> None:
        try:
            # Étape 1 : charger le CSV
            collection = ChargeurCSV.charger(
                self.chemin_fichier,
                lambda pct: self.progression.emit(pct // 2)
            )
            
            # Étape 2 : enrichir via Scryfall
            total = len(collection)
            for idx, carte in enumerate(collection, start=1):
                ClientScryfall.enrichir_carte(carte)
                pct = 50 + int((idx / total) * 50)
                self.progression.emit(pct)
            
            self.fini.emit(collection)
        except Exception as exc:
            self.erreur.emit(str(exc))


# ========== APPLICATION PRINCIPALE ==========

class DeckBuilderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"MTG Deck Builder - Commandeur v{VERSION}")
        self.setGeometry(100, 100, 950, 650)

        self.collection: List[Dict[str, Any]] = []
        self._combo_to_nom: Dict[str, str] = {}
        self.sens_tri: Dict[int, int] = {}

        self._creer_widgets()
        self._creer_layout()

    def _creer_widgets(self) -> None:
        """Crée les widgets de l'interface."""
        self.label_commandeur = QLabel("Sélectionnez un commandant :")
        self.combo_commandeur = QComboBox()
        self.combo_commandeur.currentTextChanged.connect(self.mettre_a_jour_tableau)

        self.bouton_importer = QPushButton("Importer une collection (CSV)")
        self.bouton_importer.clicked.connect(self.importer_collection)

        self.tableau_cartes = QTableWidget()
        self.tableau_cartes.setColumnCount(6)
        self.tableau_cartes.setHorizontalHeaderLabels(
            ["Nom", "Couleur", "Type", "Coût", "Synergie", "Détails"]
        )
        self.tableau_cartes.setEditTriggers(QTableWidget.NoEditTriggers)

        # Configuration du tri
        header = self.tableau_cartes.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.trier_tableau_alterne)
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.tableau_cartes.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tableau_cartes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.barre_progression = QProgressBar()
        self.barre_progression.setVisible(False)
        self.barre_progression.setMaximum(100)

    def _creer_layout(self) -> None:
        """Crée le layout principal."""
        layout = QVBoxLayout()
        layout.addWidget(self.label_commandeur)
        layout.addWidget(self.combo_commandeur)
        layout.addWidget(self.bouton_importer)
        layout.addWidget(self.barre_progression)
        layout.addWidget(self.tableau_cartes)

        widget_central = QWidget()
        widget_central.setLayout(layout)
        self.setCentralWidget(widget_central)

    def importer_collection(self) -> None:
        """Lance l'import d'une collection CSV."""
        fichier, _ = QFileDialog.getOpenFileName(
            self, "Importer une collection", "", "Fichiers CSV (*.csv)"
        )
        if not fichier:
            return

        self.barre_progression.setValue(0)
        self.barre_progression.setVisible(True)
        self.bouton_importer.setEnabled(False)

        self.worker = ImportWorker(fichier)
        self.worker.progression.connect(self.barre_progression.setValue)
        self.worker.fini.connect(self._import_termine)
        self.worker.erreur.connect(self._import_erreur)
        self.worker.start()

    def _import_termine(self, collection: List[Dict[str, Any]]) -> None:
        """Callback quand l'import est fini."""
        self.collection = collection
        self.barre_progression.setVisible(False)
        self.bouton_importer.setEnabled(True)

        if not self.collection:
            QMessageBox.warning(self, "Erreur", "Le CSV est vide ou mal formaté.")
            return

        self.mettre_a_jour_liste_commandeurs()
        self.mettre_a_jour_tableau(self.combo_commandeur.currentText())

    def _import_erreur(self, message: str) -> None:
        """Callback en cas d'erreur."""
        self.barre_progression.setVisible(False)
        self.bouton_importer.setEnabled(True)
        QMessageBox.critical(self, "Erreur d'import", f"Erreur : {message}")

    def mettre_a_jour_liste_commandeurs(self) -> None:
        """Met à jour la liste des commandants légendaires."""
        self.combo_commandeur.clear()
        self._combo_to_nom.clear()

        commandeurs = [
            carte for carte in self.collection
            if "Legendary" in carte.get("type", "")
        ]

        if not commandeurs:
            QMessageBox.warning(self, "Avertissement", "Aucun commandant trouvé.")
            return

        for carte in commandeurs:
            nom = carte["nom"]
            couleurs = carte.get("couleur", [])
            symboles = GestionnairesCouleurs.couleurs_a_symboles(couleurs)
            texte = f"{nom} [{symboles}]"
            self.combo_commandeur.addItem(texte)
            self._combo_to_nom[texte] = nom

    def mettre_a_jour_tableau(self, texte_combo: str) -> None:
        """Actualise le tableau."""
        if not self.collection or not texte_combo:
            return

        nom_commandeur = self._combo_to_nom.get(texte_combo, texte_combo)
        commandeur = next(
            (c for c in self.collection if c["nom"] == nom_commandeur),
            None
        )

        if not commandeur:
            return

        couleurs = commandeur.get("couleur", [])
        cartes = GestionnairesCouleurs.filtrer_par_couleurs(self.collection, couleurs)
        self.remplir_tableau(cartes, commandeur)

    def remplir_tableau(self, cartes: List[Dict[str, Any]], commandeur: Dict[str, Any]) -> None:
        """Affiche les cartes dans le tableau."""
        self.tableau_cartes.setRowCount(len(cartes))
        
        for i, carte in enumerate(cartes):
            # Colonne : Nom
            self.tableau_cartes.setItem(i, 0, QTableWidgetItem(carte["nom"]))
            
            # Colonne : Couleur
            symboles = GestionnairesCouleurs.couleurs_a_symboles(carte.get("couleur", []))
            self.tableau_cartes.setItem(i, 1, QTableWidgetItem(symboles))
            
            # Colonne : Type
            self.tableau_cartes.setItem(i, 2, QTableWidgetItem(carte.get("type", "")))
            
            # Colonne : Coût
            self.tableau_cartes.setItem(i, 3, QTableWidgetItem(carte.get("cout_mana", "")))
            
            # Colonne : Synergie
            synergie = CalculatriceSynergie.calculer(carte, commandeur)
            self.tableau_cartes.setItem(i, 4, QTableWidgetItem(f"{synergie}%"))
            
            # Colonne : Détails
            texte = carte.get("oracle_text_en") or carte.get("oracle_text", "")
            court = texte[:100] + ("…" if len(texte) > 100 else "") if texte else ""
            self.tableau_cartes.setItem(i, 5, QTableWidgetItem(court))

    def trier_tableau_alterne(self, indice_colonne: int) -> None:
        """Alterne le sens de tri."""
        sens = self.sens_tri.get(indice_colonne, 0)
        nouveau_sens = -1 if sens == 1 else 1
        self.sens_tri[indice_colonne] = nouveau_sens

        ordre = Qt.AscendingOrder if nouveau_sens == 1 else Qt.DescendingOrder
        self.tableau_cartes.sortItems(indice_colonne, ordre)

        header = self.tableau_cartes.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSortIndicator(indice_colonne, ordre)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    fenetre = DeckBuilderApp()
    fenetre.show()
    sys.exit(app.exec())
