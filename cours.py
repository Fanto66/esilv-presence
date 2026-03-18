import time
import logging
logging.basicConfig(level=logging.INFO)

class Cours:
    def __init__(self, utilisateur, identifiant, denomination, heure_debut, heure_fin):
        self.utilisateur = utilisateur
        self.identifiant = identifiant
        self.denomination = denomination
        self.heure_debut = heure_debut
        self.heure_fin = heure_fin
        self.deja_notifie = False
    
    def type_appel(self):
        url_appel = f"https://my.devinci.fr/student/presences/{self.identifiant}"
        logging.info(f"Vérification de l'ouverture de l'appel pour l'URL : {url_appel}")

        for _ in range(3): # Essayer jusqu'à 3 fois en cas de problème de chargement
            self.utilisateur.page.goto(url_appel)
            if url_appel in self.utilisateur.page.url:
                break
            time.sleep(2)

        #Vérifier si on a deja été noté présent (au cas où le script se relance pendant un cours par exemple)
        deja_present = self.utilisateur.page.locator("text=Vous avez été noté présent le")
        if deja_present.count() > 0 and deja_present.is_visible(timeout=0):
            logging.info(f"Le cours {self.identifiant} - {self.denomination} a déjà été noté présent pour {self.utilisateur.email}.")
            return "deja_present"

        # On vérifie la présence du bouton "Marquer ma présence"
        bouton_validation = self.utilisateur.page.locator("span:has-text('Valider la présence'):visible")
        if bouton_validation.count() > 0:
            logging.info(f"Le cours {self.identifiant} - {self.denomination} est ouvert pour {self.utilisateur.email}.")
            return "open"
        
        return "closed"
