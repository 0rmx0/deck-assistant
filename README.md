# MTG Deck Builder – Commandeur

Un outil pour construire et analyser des decks **Magic: The Gathering** avec une interface graphique intuitive.

---

## 📌 Fonctionnalités

- **Import de decks** depuis des fichiers CSV.
- **Affichage du commandant** et de ses couleurs.
- **Tri dynamique** des cartes (ascendant/descendant).
- **Redimensionnement automatique** du tableau.
- **Calcul des synergies** entre les cartes (en %).

---

## 🛠 Prérequis

- Python 3.8+
- PySide6 (`pip install pyside6`)
- Bibliothèques standard : `csv`, `requests`, `typing`

---

## 🚀 Installation

1. Clonez ce dépôt :
   ```bash
   git clone https://github.com/votre-utilisateur/mtg-deck-builder.git
   ```

2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

3. Lancez l'application :
   ```bash
   python main.py
   ```

---

## 📂 Structure du projet

- `main.py` : Point d'entrée de l'application.
- `deck_assistant/` : Module principal contenant la logique de l'application.

---

## 🎯 Utilisation

1. Importez un fichier CSV contenant votre deck.
2. Sélectionnez votre commandant.
3. Analysez les synergies et optimisez votre deck !

---

## 📜 Licence

Ce projet est sous licence [MIT](LICENSE).
