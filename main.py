#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MTG Deck Builder – Commandeur
Version complète avec :
* Import CSV + barre de progression
* Affichage du nom du commandant suivi de ses couleurs
* Tri alterné (ascendant ↔ descendant) en cliquant sur les en‑têtes
* Redimensionnement du tableau suivant la taille de la fenêtre
* Synergie affichée en pourcentage
"""

import sys
import csv
import requests
from typing import List, Dict, Any

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
    QFileDialog,
    QMessageBox,
    QHeaderView,
    QSizePolicy,
    QProgressBar,                # <-- barre de progression
)
from PySide6.QtCore import Qt, QThread, Signal


# ----------------------------------------------------------------------
# Worker thread pour charger et enrichir la collection sans bloquer l’UI
# ----------------------------------------------------------------------
class ImportWorker(QThread):
    """
    Charge le CSV, enrichit chaque ligne via Scryfall et émet des signaux
    pour mettre à jour la barre de progression.
    """
    progression = Signal(int)          # valeur 0‑100
    fini = Signal(list)                # renvoie la collection complète
    erreur = Signal(str)               # message d’erreur

    def __init__(self, chemin_fichier: str):
        super().__init__()
        self.chemin_fichier = chemin_fichier

    # ------------------------------------------------------------------
    def run(self) -> None:
        try:
            collection = self._charger_et_enrichir(self.chemin_fichier)
            self.fini.emit(collection)
        except Exception as exc:
            self.erreur.emit(str(exc))

    # ------------------------------------------------------------------
    def _charger_et_enrichir(self, fichier: str) -> List[Dict[str, Any]]:
        """
        Lit le CSV, normalise les colonnes, enrichit chaque carte via Scryfall
        et met à jour la progression.
        """
        # Mapping des en‑têtes du CSV → clés internes
        mapping = {
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

        collection: List[Dict[str, Any]] = []

        with open(fichier, mode="r", encoding="utf-8") as f:
            lecteur = csv.DictReader(f)

            # Vérifier la présence des colonnes attendues
            colonnes_manquantes = [
                col for col in mapping.keys() if col not in lecteur.fieldnames
            ]
            if colonnes_manquantes:
                raise ValueError(
                    f"Colonnes manquantes dans le CSV : {', '.join(colonnes_manquantes)}"
                )

            lignes = list(lecteur)                     # on lit tout d’abord pour connaître le total
            total = len(lignes)
            if total == 0:
                raise ValueError("Le fichier CSV est vide.")

            for idx, ligne in enumerate(lignes, start=1):
                # -------- Normalisation des clés ----------
                carte: Dict[str, Any] = {
                    interne: ligne[externe].strip()
                    for externe, interne in mapping.items()
                }

                # -------- Conversion numérique ----------
                for champ_num in [
                    "quantity",
                    "price_usd",
                    "price_eur",
                    "price_usd_foil",
                    "price_eur_foil",
                    "price_usd_etched",
                    "price_eur_etched",
                ]:
                    try:
                        carte[champ_num] = (
                            float(carte[champ_num]) if carte[champ_num] else 0.0
                        )
                    except ValueError:
                        carte[champ_num] = 0.0

                # -------- Enrichissement Scryfall ----------
                if not carte["scryfall_id"]:
                    infos = self._enrichir_via_api(carte["nom"])
                    carte.update(infos)
                else:
                    infos = self._recuperer_par_id(carte["scryfall_id"])
                    carte.update(infos)

                collection.append(carte)

                # ----- mise à jour de la barre de progression -----
                pourcentage = int((idx / total) * 100)
                self.progression.emit(pourcentage)

        return collection

    # ------------------------------------------------------------------
    @staticmethod
    def _enrichir_via_api(nom_carte: str) -> Dict[str, Any]:
        """Interroge Scryfall avec le paramètre fuzzy."""
        try:
            url = f"https://api.scryfall.com/cards/named?fuzzy={nom_carte}"
            réponse = requests.get(url, timeout=10)
            if réponse.status_code != 200:
                return {}
            data = réponse.json()
            return {
                "scryfall_id": data.get("id", ""),
                "couleur": data.get("color_identity", []),   # liste de lettres
                "type": data.get("type_line", ""),
                "cout_mana": data.get("mana_cost", ""),
                "oracle_text": data.get("oracle_text", ""),
            }
        except Exception:
            return {}

    @staticmethod
    def _recuperer_par_id(scryfall_id: str) -> Dict[str, Any]:
        """Récupère les mêmes champs à partir d’un ID déjà connu."""
        try:
            url = f"https://api.scryfall.com/cards/{scryfall_id}"
            réponse = requests.get(url, timeout=10)
            if réponse.status_code != 200:
                return {}
            data = réponse.json()
            return {
                "couleur": data.get("color_identity", []),
                "type": data.get("type_line", ""),
                "cout_mana": data.get("mana_cost", ""),
                "oracle_text": data.get("oracle_text", ""),
            }
        except Exception:
            return {}


# ----------------------------------------------------------------------
# Application principale
# ----------------------------------------------------------------------
class DeckBuilderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MTG Deck Builder - Commandeur")
        self.setGeometry(100, 100, 950, 650)

        # ------------------------------------------------------------------
        # Widgets
        # ------------------------------------------------------------------
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

        # ----- Gestion du tri alterné -----
        self.sens_tri: dict[int, int] = {}
        header = self.tableau_cartes.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.trier_tableau_alterne)
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.tableau_cartes.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.tableau_cartes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ----- Barre de progression (cachée tant qu’on n’importe pas) -----
        self.barre_progression = QProgressBar()
        self.barre_progression.setVisible(False)
        self.barre_progression.setMaximum(100)

        # ------------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------------
        layout = QVBoxLayout()
        layout.addWidget(self.label_commandeur)
        layout.addWidget(self.combo_commandeur)
        layout.addWidget(self.bouton_importer)
        layout.addWidget(self.barre_progression)   # placée juste au dessus du tableau
        layout.addWidget(self.tableau_cartes)

        widget_central = QWidget()
        widget_central.setLayout(layout)
        self.setCentralWidget(widget_central)

        # ------------------------------------------------------------------
        # Données internes
        # ------------------------------------------------------------------
        self.collection: List[Dict[str, Any]] = []
        # Dictionnaire qui lie le texte affiché dans le combo au vrai nom de la carte
        self._combo_to_nom: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Méthodes utilitaires
    # ------------------------------------------------------------------
    def _nom_du_combo(self, texte_combo: str) -> str:
        """Retourne le vrai nom de la carte à partir du texte du combo."""
        return self._combo_to_nom.get(texte_combo, texte_combo)

    # ------------------------------------------------------------------
    # Importation du CSV (avec worker thread)
    # ------------------------------------------------------------------
    def importer_collection(self):
        fichier, _ = QFileDialog.getOpenFileName(
            self,
            "Importer une collection",
            "",
            "Fichiers CSV (*.csv)",
        )
        if not fichier:
            return

        # Afficher la barre de progression et désactiver le bouton d’import
        self.barre_progression.setValue(0)
        self.barre_progression.setVisible(True)
        self.bouton_importer.setEnabled(False)

        # Créer et lancer le worker
        self.worker = ImportWorker(fichier)
        self.worker.progression.connect(self.barre_progression.setValue)
        self.worker.fini.connect(self._import_termine)
        self.worker.erreur.connect(self._import_erreur)
        self.worker.start()

    def _import_termine(self, collection: List[Dict[str, Any]]):
        """Callback appelé quand le worker a fini son travail."""
        self.collection = collection
        self.barre_progression.setVisible(False)
        self.bouton_importer.setEnabled(True)

        if not self.collection:
            QMessageBox.warning(self, "Erreur", "Le CSV est vide ou mal formaté.")
            return

        self.mettre_a_jour_liste_commandeurs()
        self.mettre_a_jour_tableau(self.combo_commandeur.currentText())

    def _import_erreur(self, message: str):
        """Callback appelé en cas d’erreur pendant l’import."""
        self.barre_progression.setVisible(False)
        self.bouton_importer.setEnabled(True)
        QMessageBox.critical(self, "Erreur d’import", f"Impossible de charger le fichier : {message}")

    # ------------------------------------------------------------------
    # Construction du combo (nom + couleur)
    # ------------------------------------------------------------------
    def mettre_a_jour_liste_commandeurs(self):
        """Construit la liste des commandants légendaires avec leurs couleurs."""
        self.combo_commandeur.clear()
        self._combo_to_nom.clear()

        commandeurs = [
            carte for carte in self.collection
            if "Legendary" in carte.get("type", "")
        ]

        if not commandeurs:
            QMessageBox.warning(self, "Avertissement", "Aucun commandant légendaire trouvé.")
            return

        items_affiches = []
        for carte in commandeurs:
            nom = carte["nom"]
            couleurs = carte.get("couleur", [])
            couleur_str = "C" if not couleurs else "".join(couleurs)   # C = incolore
            texte_combo = f"{nom} [{couleur_str}]"
            items_affiches.append(texte_combo)
            self._combo_to_nom[texte_combo] = nom

        self.combo_commandeur.addItems(items_affiches)
        print(f"Commandants affichés : {items_affiches}")

    # ------------------------------------------------------------------
    # Recherche des couleurs du commandant choisi
    # ------------------------------------------------------------------
    def get_couleurs_commandeur(self, commandant: str) -> List[str]:
        """Renvoie la liste de couleurs du commandant (ex. ['W','U'])."""
        for carte in self.collection:
            if carte["nom"] == commandant:
                return carte.get("couleur", [])
        return []

    # ------------------------------------------------------------------
    # Filtrage par couleur
    # ------------------------------------------------------------------
    def filtrer_par_couleurs(
        self,
        collection: List[Dict[str, Any]],
        couleurs_commandeur: List[str],
    ) -> List[Dict[str, Any]]:
        """Conserve les cartes dont l’identité couleur est incluse dans celle du commandant."""
        if not couleurs_commandeur:
            return collection

        couleurs_autorisees = set(couleurs_commandeur)

        def couleur_valide(carte: Dict[str, Any]) -> bool:
            # Carte incolore → toujours valide
            if not carte.get("couleur"):
                return True
            # Toutes les couleurs de la carte doivent appartenir aux couleurs autorisées
            return set(carte["couleur"]).issubset(couleurs_autorisees)

        return [c for c in collection if couleur_valide(c)]

    # ------------------------------------------------------------------
    # Mise à jour du tableau
    # ------------------------------------------------------------------
    def mettre_a_jour_tableau(self, texte_combo: str):
        """Actualise le tableau en fonction du commandant sélectionné."""
        if not self.collection:
            return

        commandant = self._nom_du_combo(texte_combo)
        couleurs = self.get_couleurs_commandeur(commandant)
        cartes_filtrees = self.filtrer_par_couleurs(self.collection, couleurs)
        self.remplir_tableau(cartes_filtrees)

    def remplir_tableau(self, cartes: List[Dict[str, Any]]):
        """Affiche les cartes dans le QTableWidget."""
        self.tableau_cartes.setRowCount(len(cartes))
        for i, carte in enumerate(cartes):
            self.tableau_cartes.setItem(i, 0, QTableWidgetItem(carte["nom"]))
            self.tableau_cartes.setItem(
                i, 1, QTableWidgetItem(",".join(carte.get("couleur", [])))
            )
            self.tableau_cartes.setItem(i, 2, QTableWidgetItem(carte.get("type", "")))
            self.tableau_cartes.setItem(i, 3, QTableWidgetItem(carte.get("cout_mana", "")))

            # Synergie en pourcentage
            synergie_pct = self.calculer_synergie(carte, self.combo_commandeur.currentText())
            self.tableau_cartes.setItem(i, 4, QTableWidgetItem(f"{synergie_pct}%"))

            texte = carte.get("oracle_text", "")
            self.tableau_cartes.setItem(
                i, 5, QTableWidgetItem(texte[:100] + ("…" if len(texte) > 100 else ""))
            )
        self.tableau_cartes.resizeColumnsToContents()

    # ------------------------------------------------------------------
    # Tri alterné (clic sur l’en‑tête)
    # ------------------------------------------------------------------
    def trier_tableau_alterne(self, indice_colonne: int):
        """
        Alterne le sens de tri pour la colonne cliquée :
        - première fois → ascendant
        - deuxième fois → descendant
        - troisième fois → revient à ascendant, etc.
        """
        sens_actuel = self.sens_tri.get(indice_colonne, 0)   # 0 = jamais trié
        nouveau_sens = -1 if sens_actuel == 1 else 1       # bascule 1 ↔ -1
        self.sens_tri[indice_colonne] = nouveau_sens

        ordre = Qt.AscendingOrder if nouveau_sens == 1 else Qt.DescendingOrder
        self.tableau_cartes.sortItems(indice_colonne, ordre)

        # Affiche la flèche dans l’en‑tête
        header = self.tableau_cartes.horizontalHeader()
        header.setSortIndicatorShown(True)
        header.setSortIndicator(indice_colonne, ordre)

    # ------------------------------------------------------------------
    # Calcul de la synergie (renvoie un pourcentage)
    # ------------------------------------------------------------------
    def calculer_synergie(self, carte: Dict[str, Any], texte_combo: str) -> float:
        """
        Calcule la synergie d’une carte avec le commandant choisi
        et renvoie un pourcentage (0 % – 100 %).
        """
        commandant = self._nom_du_combo(texte_combo)

        # ----- Score brut (identique à la version précédente) -----
        score_brut = 0
        if "Legendary" in carte.get("type", ""):
            score_brut += 3
        if not carte.get("couleur"):          # incolore
            score_brut += 1
        if set(carte.get("couleur", [])).issubset(
            set(self.get_couleurs_commandeur(commandant))
        ):
            score_brut += 2

        # ----- Score maximal possible -----
        score_max = 6  # 3 + 1 + 2

        # ----- Conversion en pourcentage -----
        pourcentage = (score_brut / score_max) * 100.0
        return round(pourcentage, 1)


# ----------------------------------------------------------------------
# Point d’entrée
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    fenetre = DeckBuilderApp()
    fenetre.show()
    sys.exit(app.exec())
