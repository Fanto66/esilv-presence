# ESILV/PULV Notifier

Script Python qui surveille l'ouverture de l'appel sur my.devinci.fr, et envoie une notification lorsque qu'il est ouvert.

## Fonctionnement

Le script :
1. se connecte avec les identifiants définis dans `.env`
2. charge les cours du jour, tous les jours à minuit
3. vérifie l'état de chaque appel de facon régulière à partir de 15min avant le début du cours, et jusqu'à sa fin
4. notifie via ntfy quand l'appel est ouvert
5. est réglé pour ne pas faire de checks inutiles

Toute la logique horaire est basée sur le fuseau **Europe/Paris**.

## Prérequis

- Python 3.11+
- Windows, macOS ou Linux
- Un compte étudiant my.devinci.fr valide

## Installation

### 1) Cloner le projet

```bash
git clone https://github.com/Fanto66/esilv-presence
cd esilv-presence
```

### 2) Créer et activer un environnement virtuel

#### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Installer les dépendances

```bash
pip install playwright python-dotenv requests
python -m playwright install chromium
```


## Configuration

1. Renommer `.env-example` en `.env`
2. Remplir vos identifiants
3. Ajouter votre [sujet NTFY](https://ntfy.sh/)


## Lancement

```bash
python main.py
```


## Limites actuelles

- Seul un utilisateur par instance du script
- Le script suppose la structure HTML actuelle du portail my.devinci.fr (pourrait casser le script si elle change)