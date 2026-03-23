from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
import datetime
import time
import logging
from zoneinfo import ZoneInfo
logging.basicConfig(level=logging.INFO)

from utilisateur import Utilisateur

load_dotenv()

PARIS_TZ = ZoneInfo("Europe/Paris")

users = [
    {
        "email": os.getenv("EMAIL_1"),
        "password": os.getenv("PASSWORD_1")
    }
]


def now_in_paris():
    return datetime.datetime.now(PARIS_TZ)

def main():
    last_date = now_in_paris().date()
    with sync_playwright() as p:
        # Initialisation des utilisateurs
        utilisateurs = []
        logging.info("Initialisation des utilisateurs...")
        for user_info in users:
            # Création de l'utilisateur et connexion
            utilisateur = Utilisateur(user_info["email"], user_info["password"])
            utilisateur.se_connecter(p)

            # Récupération des cours du jour pour l'utilisateur
            utilisateur.maj_cours_du_jour()

            utilisateurs.append(utilisateur)

        logging.info(f"{len(utilisateurs)} utilisateur(s) initialisé(s).")

        # boucle principale
        while True:

            #si on est passé à une nouvelle journée, on met à jour les cours pour tous les utilisateurs
            today_date = now_in_paris().date()
            logging.info(f"last_date: {last_date}, today_date: {today_date}")
            if last_date != today_date:
                logging.info("Nouvelle journée détectée, mise à jour des cours...")
                for utilisateur in utilisateurs:
                    utilisateur.maj_cours_du_jour()
                last_date = today_date

            delais = [] # liste de delais pour prendre le plus court
            prochains_debuts = [] #permet de calculer le delai jusqu'au prochain cours pour éviter de faire des checks trop souvent

            #for utilisateur in utilisateurs:
            utilisateur = utilisateurs[0] #on n'a qu'un utilisateur pour l'instant

            logging.info(f"Vérification des cours pour {utilisateur.email}...")
            for cours in utilisateur.planning:
                logging.info(f"Vérification du cours {cours.identifiant} pour {utilisateur.email}...")
                if cours.deja_notifie:
                    logging.info(f"Le cours {cours.identifiant} a déjà été notifié pour {utilisateur.email}, on passe au suivant.")
                    continue

                # vérifier si l'horaire pour le cours est bon
                now = now_in_paris()

                # Fenetre 15 minutes avant 15 minutes après le début
                if cours.heure_debut - datetime.timedelta(minutes=15) <= now <= cours.heure_debut + datetime.timedelta(minutes=15):
                    logging.info(f"Le cours {cours.identifiant} est dans la fenêtre 1 de notification pour {utilisateur.email}.")
                    etat_appel = cours.type_appel()
                    if etat_appel == "open":
                        utilisateur.notifier(f"Le cours {cours.identifiant} - {cours.denomination} est ouvert !")
                        cours.deja_notifie = True
                    elif etat_appel == "deja_present":
                        logging.info(f"Le cours {cours.identifiant} - {cours.denomination} est déjà noté présent pour {utilisateur.email}.")
                        cours.deja_notifie = True
                    elif etat_appel == "closed":
                        logging.info(f"Le cours {cours.identifiant} - {cours.denomination} n'est pas encore ouvert pour {utilisateur.email}.")
                        delais.append(60) #recheck dans 1 minute
                        
                # Fenetre 15 minutes apres jusqu'à la fin
                elif cours.heure_debut + datetime.timedelta(minutes=15) < now <= cours.heure_fin:
                    logging.info(f"Le cours {cours.identifiant} - {cours.denomination} est dans la fenêtre 2 de notification pour {utilisateur.email}.")
                    etat_appel = cours.type_appel()
                    if etat_appel == "open":
                        utilisateur.notifier(f"Le cours {cours.identifiant} - {cours.denomination} est ouvert !")
                        cours.deja_notifie = True
                    elif etat_appel == "deja_present":
                        logging.info(f"Le cours {cours.identifiant} - {cours.denomination} est déjà noté présent pour {utilisateur.email}.")
                        cours.deja_notifie = True
                    elif etat_appel == "closed":
                        logging.info(f"Le cours {cours.identifiant} - {cours.denomination} n'est pas encore ouvert pour {utilisateur.email}.")
                        delais.append(120) #recheck dans 2 minutes

                # Sinon on passe au cours suivant car pas dans la fenetre
                else:
                    logging.info(f"Le cours {cours.identifiant} - {cours.denomination} n'est pas dans une fenêtre de notification pour {utilisateur.email}, on passe au suivant.")
                    fenetre_debut = cours.heure_debut - datetime.timedelta(minutes=15)
                    if fenetre_debut > now:
                        prochains_debuts.append(fenetre_debut)

            if delais:
                attente = min(delais)
            elif prochains_debuts:
                prochain = min(prochains_debuts)
                now = now_in_paris()
                attente = max(1, (prochain - now).total_seconds())

                prochain_check = now + datetime.timedelta(seconds=attente)

                logging.info(
                    f"Prochain cours dans {attente:.0f} secondes. "
                    f"Prochain check à {prochain_check.strftime('%Y-%m-%d %H:%M:%S')}."
                    f"Il est actuellement {now.strftime('%Y-%m-%d %H:%M:%S')}."
                )
            else:
                now = now_in_paris()
                minuit = datetime.datetime.combine(
                    now.date() + datetime.timedelta(days=1),
                    datetime.time.min,
                    tzinfo=PARIS_TZ,
                )
                attente = max(1, (minuit - now).total_seconds())
                logging.info(f"Aucun cours à vérifier dans les prochaines heures, on attend jusqu'à minuit ({attente:.0f} secondes) avant de vérifier à nouveau.")

            time.sleep(attente) #si aucun cours n'est dans la fenetre, on attend 1 minute avant de vérifier à nouveau
                    
if __name__ == "__main__":
    main()