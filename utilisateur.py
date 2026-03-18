from email.mime import message
import time
import random
from datetime import datetime
import logging
from zoneinfo import ZoneInfo
logging.basicConfig(level=logging.INFO)

import requests
from cours import Cours

PARIS_TZ = ZoneInfo("Europe/Paris")

def human_delay(min_sec=1, max_sec=3):
    time.sleep(random.uniform(min_sec, max_sec))

class Utilisateur:
    def __init__(self, email):
        self.email = email
        self.planning = [] #on commence avec un planning vide
        self.browser_context = None
        self.page = None
        self.derniere_maj = None

    def maj_cours_du_jour(self): #Récupère les cours du jour et les ajoute au planning
        if not self.page:
            logging.error("Erreur : L'utilisateur doit être connecté pour récupérer les cours.")
            return
        
        logging.info(f"Suppression des cours de {self.email}...")

        self.planning.clear() #on vide le planning

        logging.info(f"Récupération des cours pour {self.email}...")

        self.page.goto("https://my.devinci.fr/student/presences/")

        # Vérification de la présence de cours ajd
        self.page.wait_for_selector("body")
        contenu = self.page.inner_text("body").lower()
        if "Pas de cours de prévu" in contenu:
            logging.info(f"Aucun cours prévu aujourd'hui pour {self.email}.")
            self.derniere_maj = datetime.now(PARIS_TZ)
            return

        #sinon
        self.page.wait_for_selector("#body_presences")
        rows = self.page.query_selector_all("#body_presences tr")
        for row in rows:
            cols = row.query_selector_all("td")

            if len(cols) == 0: #si la ligne ne contient pas de cours, on ignore
                continue

            # On suppose que les colonnes sont : [0] Horaires du cours, [1] Nom du cours, [2] Intervenant, [3] Présence
            horaires = cols[0].inner_text().strip()
            horaires2 = " ".join(horaires.split()) #pour enlever les espaces en trop
            heure_debut, heure_fin = horaires2.split("-")
            heure_debut = heure_debut.strip()
            heure_fin = heure_fin.strip()
            today = datetime.now(PARIS_TZ).date()
            heure_debut_dt = datetime.combine(today, datetime.strptime(heure_debut, "%H:%M").time(), tzinfo=PARIS_TZ)
            heure_fin_dt = datetime.combine(today, datetime.strptime(heure_fin, "%H:%M").time(), tzinfo=PARIS_TZ)

            nom_cours = cols[1].inner_text().strip()

            intervenant = cols[2].inner_text().strip()

            presence_link = None
            presence = cols[3].query_selector("a")
            if presence:
                presence_link = presence.get_attribute("href")
            logging.info(f"{nom_cours} ({horaires}) par {intervenant}) lu pour {self.email}")

            self.planning.append(Cours(
                identifiant=presence_link.split("/")[-1] if presence_link else None,
                utilisateur=self,
                denomination=nom_cours,
                heure_debut=heure_debut_dt,
                heure_fin=heure_fin_dt
            ))
        
        self.derniere_maj = datetime.now(PARIS_TZ)

    
    def se_connecter(self, playwright_instance, mot_de_passe):
        logging.info(f"Connexion de {self.email}...")
        browser = playwright_instance.chromium.launch(headless=False)
        self.browser_context = browser.new_context()
        self.page = self.browser_context.new_page()

        self.page.goto("https://my.devinci.fr/")

        self.page.type("#login", self.email, delay=random.randint(50, 150))
        human_delay()
        self.page.click("#btn_next")

        self.page.wait_for_url("**adfs.devinci.fr**")

        self.page.type("#passwordInput", mot_de_passe, delay=random.randint(70, 180))
        human_delay()
        self.page.click("#submitButton")

        self.page.wait_for_url("https://my.devinci.fr/**")

        logging.info(f"{self.email} connecté avec succès !")

    def notifier(self, message):
        url = "https://ntfy.sh/esilv_attendance_romain"
        requests.post(url, data=message)
        logging.info(f"Notification pour {self.email}: {message}")