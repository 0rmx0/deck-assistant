# 📦 Guide de Déploiement - CI/CD GitHub Actions

Ce projet est configuré pour **compiler automatiquement** des exécutables pour **Windows, macOS et Linux** via GitHub Actions.

---

## 🚀 Comment activer les builds automatiques

### Option 1 : Créer une Release (Recommandé)
1. Allez sur votre dépôt GitHub
2. Cliquez sur **"Releases"** dans la barre latérale droite
3. Cliquez sur **"Create a new release"**
4. Entrez un tag comme `v1.0.0` (doit commencer par `v`)
5. Cliquez sur **"Publish release"**

→ Les exécutables seront **compilés automatiquement** et **attachés à la release**

### Option 2 : Déclencher manuellement
1. Allez dans **"Actions"** onglet
2. Sélectionnez **"Build & Release"** dans la liste
3. Cliquez sur **"Run workflow"**
4. Cliquez sur **"Run workflow"** (bouton bleu)

→ Les exécutables seront disponibles sous **"Artifacts"**

---

## 📥 Récupérer les exécutables

### Via une Release
- Les fichiers compilés sont directement disponibles dans la page de la release
- Trois versions (`linux`, `windows`, `macos`)

### Via Artifacts
1. Allez dans **"Actions"** 
2. Cliquez sur le workflow le plus récent
3. Scroll down pour voir les **Artifacts**
4. Téléchargez l'exécutable pour votre OS

---

## 🔧 Fichiers de configuration

- **`.github/workflows/build.yml`** - Configuration des builds automatiques
- **`requirements.txt`** - Dépendances Python
- **`setup.py`** - Configuration du package

---

## 📋 Spécifications des builds

| Platform | Exécutable | Format |
|----------|-----------|--------|
| **Windows** | `mtg-deck-builder-windows.exe` | Standalone `.exe` |
| **macOS** | `mtg-deck-builder-macos` | Exécutable Mach-O |
| **Linux** | `mtg-deck-builder-linux` | Exécutable ELF |

---

## ⚙️ Modification des builds

Pour modifier le processus de build :
1. Éditez `.github/workflows/build.yml`
2. Modifiez les options PyInstaller (voir [documentation PyInstaller](https://pyinstaller.org/))
3. Committez et poussez vos changements
4. Les prochains builds utiliseront la configuration mise à jour

---

## ✅ Gestion des versions

Utilisez [Semantic Versioning](https://semver.org/) :
- **v1.0.0** - Release majeure
- **v1.0.1** - Patch / bugfix
- **v1.1.0** - Nouvelle feature mineure

Taggez vos releases : `git tag -a v1.0.0 -m "Version 1.0.0"` puis `git push origin v1.0.0`

