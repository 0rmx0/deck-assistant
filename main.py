#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MTG Deck Builder – Commandeur (Refactorisé)
Version 26.02.01
Version avec séparation des responsabilités et élimination de duplication.
"""

import sys
import csv
import sqlite3
import requests
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json

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
    QMenuBar,
    QMenu,
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

class GestionnaireBD:
    """Gère la persistance des données via SQLite."""
    
    def __init__(self, chemin_bd: str = "deck_collection.db"):
        self.chemin_bd = chemin_bd
        self._initialiser_bd()
    
    def _initialiser_bd(self) -> None:
        """Crée la table si elle n'existe pas."""
        with sqlite3.connect(self.chemin_bd) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cartes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT NOT NULL,
                    couleur TEXT,
                    type TEXT,
                    cout_mana TEXT,
                    oracle_text_en TEXT,
                    oracle_text_fr TEXT,
                    scryfall_id TEXT UNIQUE,
                    quantity REAL,
                    set_code TEXT,
                    set_name TEXT,
                    collector_number TEXT,
                    rarity TEXT,
                    language TEXT,
                    condition TEXT,
                    finish TEXT,
                    altered BOOLEAN,
                    signed BOOLEAN,
                    misprint BOOLEAN,
                    price_usd REAL,
                    price_eur REAL,
                    price_usd_foil REAL,
                    price_eur_foil REAL,
                    price_usd_etched REAL,
                    price_eur_etched REAL,
                    container_type TEXT,
                    container_name TEXT
                )
            ''')
            conn.commit()
    
    def sauvegarder_cartes(self, cartes: List[Dict[str, Any]]) -> None:
        """Sauvegarde les cartes dans la BD."""
        with sqlite3.connect(self.chemin_bd) as conn:
            cursor = conn.cursor()
            for carte in cartes:
                try:
                    # Convertir les listes en JSON
                    couleur = json.dumps(carte.get("couleur", []))
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO cartes (
                            nom, couleur, type, cout_mana, oracle_text_en, oracle_text_fr,
                            scryfall_id, quantity, set_code, set_name, collector_number,
                            rarity, language, condition, finish, altered, signed, misprint,
                            price_usd, price_eur, price_usd_foil, price_eur_foil,
                            price_usd_etched, price_eur_etched, container_type, container_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        carte.get("nom", ""),
                        couleur,
                        carte.get("type", ""),
                        carte.get("cout_mana", ""),
                        carte.get("oracle_text_en", ""),
                        carte.get("oracle_text_fr", ""),
                        carte.get("scryfall_id", ""),
                        carte.get("quantity", 1.0),
                        carte.get("set_code", ""),
                        carte.get("set_name", ""),
                        carte.get("collector_number", ""),
                        carte.get("rarity", ""),
                        carte.get("language", ""),
                        carte.get("condition", ""),
                        carte.get("finish", ""),
                        carte.get("altered", False),
                        carte.get("signed", False),
                        carte.get("misprint", False),
                        carte.get("price_usd", 0.0),
                        carte.get("price_eur", 0.0),
                        carte.get("price_usd_foil", 0.0),
                        carte.get("price_eur_foil", 0.0),
                        carte.get("price_usd_etched", 0.0),
                        carte.get("price_eur_etched", 0.0),
                        carte.get("container_type", ""),
                        carte.get("container_name", ""),
                    ))
                except sqlite3.IntegrityError:
                    pass  # Ignorer les doublons
            conn.commit()
    
    def charger_toutes_cartes(self) -> List[Dict[str, Any]]:
        """Charge toutes les cartes de la BD."""
        cartes = []
        with sqlite3.connect(self.chemin_bd) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cartes")
            
            for row in cursor.fetchall():
                carte = dict(row)
                # Reconvertir JSON en liste
                try:
                    carte["couleur"] = json.loads(carte.get("couleur", "[]"))
                except (json.JSONDecodeError, TypeError):
                    carte["couleur"] = []
                cartes.append(carte)
        
        return cartes
    
    def vider_bd(self) -> None:
        """Vide complètement la BD."""
        with sqlite3.connect(self.chemin_bd) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cartes")
            conn.commit()


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
    
    MAX_STARS = 5  # Nombre maximum d'étoiles
    STAR_SYMBOL = "⭐"  # Symbole d'étoile
    
    @staticmethod
    def calculer(carte: Dict[str, Any], commandeur: Dict[str, Any]) -> int:
        """Retourne un score de synergie en nombre d'étoiles (0-5)."""
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
        
        # Convertir en nombre d'étoiles (0-5)
        pourcentage = (score / MAX_SYNERGY_SCORE) * 100
        nb_etoiles = round((pourcentage / 100) * CalculatriceSynergie.MAX_STARS)
        return max(0, min(nb_etoiles, CalculatriceSynergie.MAX_STARS))
    
    @staticmethod
    def afficher_synergie(nb_etoiles: int) -> str:
        """Convertit le nombre d'étoiles en affichage."""
        return CalculatriceSynergie.STAR_SYMBOL * nb_etoiles


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
            # Étape 1 : charger le CSV (0-100%)
            collection = ChargeurCSV.charger(
                self.chemin_fichier,
                lambda pct: self.progression.emit(pct)
            )
            
            # Étape 2 : enrichir via Scryfall (0-100%)
            self.progression.emit(0)  # Reset à 0%
            total = len(collection)
            for idx, carte in enumerate(collection, start=1):
                ClientScryfall.enrichir_carte(carte)
                pct = int((idx / total) * 100)
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

        # Gestionnaire de BD
        self.bd = None
        self.chemin_bd_actuel = None

        self.collection: List[Dict[str, Any]] = []
        self._combo_to_nom: Dict[str, str] = {}
        self.sens_tri: Dict[int, int] = {}

        self._creer_menu()
        self._creer_widgets()
        self._creer_layout()
    
    def _creer_menu(self) -> None:
        """Crée la barre de menu."""
        menubar = self.menuBar()
        
        # Menu Fichier
        menu_fichier = menubar.addMenu("Fichier")
        
        action_ouvrir_bd = menu_fichier.addAction("Ouvrir une base de données")
        action_ouvrir_bd.triggered.connect(self.ouvrir_base_donnees)
        
        menu_fichier.addSeparator()
        
        action_importer = menu_fichier.addAction("Importer un CSV")
        action_importer.triggered.connect(self.importer_collection)
        
        menu_fichier.addSeparator()
        
        action_quitter = menu_fichier.addAction("Quitter")
        action_quitter.triggered.connect(self.close)

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

    def ouvrir_base_donnees(self) -> None:
        """Ouvre une base de données existante."""
        fichier, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir une base de données", "", "Fichiers SQLite (*.db)"
        )
        if not fichier:
            return
        
        try:
            self.bd = GestionnaireBD(fichier)
            self.chemin_bd_actuel = fichier
            self.collection = self.bd.charger_toutes_cartes()
            
            if not self.collection:
                QMessageBox.warning(self, "Avertissement", "La base de données est vide.")
                return
            
            self.setWindowTitle(f"MTG Deck Builder - Commandeur v{VERSION} - {Path(fichier).name}")
            self.mettre_a_jour_liste_commandeurs()
            self.mettre_a_jour_tableau(self.combo_commandeur.currentText())
            QMessageBox.information(self, "Succès", f"Base de données chargée : {len(self.collection)} cartes")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Impossible d'ouvrir la base : {e}")

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
        
        # Proposer de créer/utiliser une BD
        if not self.bd:
            reponse = QMessageBox.question(
                self, 
                "Créer une base de données ?", 
                "Voulez-vous créer une base de données pour sauvegarder cette collection ?"
            )
            if reponse == QMessageBox.Yes:
                fichier, _ = QFileDialog.getSaveFileName(
                    self, "Créer une base de données", "", "Fichiers SQLite (*.db)"
                )
                if fichier:
                    # S'assurer que le fichier se termine par .db
                    if not fichier.lower().endswith('.db'):
                        fichier = fichier + '.db'
                    self.bd = GestionnaireBD(fichier)
                    self.chemin_bd_actuel = fichier
                    self.setWindowTitle(f"MTG Deck Builder - Commandeur v{VERSION} - {Path(fichier).name}")
        
        # Sauvegarder dans la BD
        if self.bd:
            self.bd.sauvegarder_cartes(self.collection)
            QMessageBox.information(self, "Succès", f"Collection sauvegardée : {len(self.collection)} cartes")
        
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
            synergie_etoiles = CalculatriceSynergie.calculer(carte, commandeur)
            affichage = CalculatriceSynergie.afficher_synergie(synergie_etoiles)
            self.tableau_cartes.setItem(i, 4, QTableWidgetItem(affichage))
            
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
