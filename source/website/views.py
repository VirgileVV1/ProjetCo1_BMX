from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
import sqlalchemy
from datetime import datetime
import random
from math import ceil
import numpy as np

import xlrd

from .__init__ import db
from .models import User, Titulaire, Club, Sexe, Championnat, Championnat_type, Etape, Categorie_type, Participant_etape, Race_type, Couloir, Race, Participant_race, Manche, Participant_manche, Categorie, Participant_categorie

views = Blueprint("views", __name__)


def get_titulaires_dict(titulaires) :
    """Fonction de création d'un dictionnaire de titulaires

    Certaines fonction nécessite une structure de données particulière, cette fonction la créée.

    Returns:
        Dict: dictionnaire de titulaires

    """

    to_return = []

    for titulaire in titulaires :

        club = Club.query.filter_by(id=titulaire.club_id).first()
        sexe = Sexe.query.filter_by(id=titulaire.sexe_id).first()

        to_return.append({
            "id": titulaire.id,
            "nom": titulaire.nom,
            "prenom": titulaire.prenom,
            "date_naissance": titulaire.date_naissance.strftime("%d/%m/%Y"),
            "club": club.ville[0].upper() + club.ville[1:],
            "sexe": sexe.denomination,
            "plaque": club.initiales.upper() + " " + str(titulaire.numero_plaque),
        })

    return to_return

def check_titulaire_number(titulaires, number) :
    """Fonction de vérification de l'unicité de la plaque

    Fonction vérifiant si le numéro de plaque voulu n'existe pas déjà dans le club

    Returns:
        bool: vrai ou faux

    """

    for titulaire in titulaires :

        if titulaire.numero_plaque == number :

            return False
    return True


def get_championnats_dict() :
    """Fonction de création d'un dictionnaire de championnats

    Certaines fonction nécessite une structure de données particulière, cette fonction la créée.

    Returns:
        Dict: dictionnaire de championnats

    """

    championnats_list = Championnat.query.order_by(Championnat.annee.desc()).all()
    championnats = []

    for championnat in championnats_list :

        championnats.append({
            'id': championnat.id,
            'type': Championnat_type.query.filter_by(id=championnat.championnat_type_id).first().type,
            'annee': championnat.annee,
            'nb_etapes_max': str(Championnat_type.query.filter_by(id=championnat.championnat_type_id).first().nb_etapes_max),
            'nb_etapes_courant': str(len(championnat.etapes))
        })

    return championnats

def get_etapes_dict(championnat) :
    """Fonction de création d'un dictionnaire de étapes

    Certaines fonction nécessite une structure de données particulière, cette fonction la créée.

    Returns:
        Dict: dictionnaire de l'étapes

    """

    etapes_list = championnat.etapes
    etapes = []

    for etape in etapes_list :
        etapes.append({
            'id': etape.id,
            'club': Club.query.filter_by(id=etape.lieu_id).first().ville,
            'participants': len(Participant_etape.query.filter_by(etape_id=etape.id).all()),
            'nb_titulaires': len(Titulaire.query.all())
        })

    return etapes

def calcul_points_race(races) :
    """Fonction de calcul des points d'un race

    Fonction qui calcul les points en fonction de l'orde d'arrivé des pilotes à une manche

    Returns:
        Dict: dictionnaire ordonné par ordre croissant des points reçus aux races d'une manche

    """
    resultats = {}
    for race in races :
        for manche in race.manches :
            for participation in manche.participations :
                if participation.titulaire_id in resultats :
                    resultats[participation.titulaire_id] += participation.resultat
                else :
                    resultats[participation.titulaire_id] = participation.resultat
        for participation in race.participations :
            participation.resultat = resultats[participation.titulaire_id]


@views.route("/")
@login_required
def home() :
    """Fonction liée au end-point "/"

    Fonction affichant la page d'acceuil.

    Returns:
        Template: template logged.html

    """

    return render_template("logged.html")

#Fonction affichant la liste des titulaires
@views.route("/titulaires/")
@login_required
def titulaires() :
    """Fonction liée au end-point "/titulaires/"

    Fonction affichant la liste des titulaires.

    Returns:
        Template: template titulaire.html

    """

    #Récupération des données nécessaires à l'affichage de la page
    titulaires = get_titulaires_dict(Titulaire.query.all())
    clubs = Club.query.all()
    sexes = Sexe.query.all()

    #Retour de la page populer des valeurs passées en argument
    return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes)

@views.route('/titulaires/<club_ville>/')
@login_required
def titulaires_by_ville(club_ville) :
    """Fonction liée au end-point "/titulaires/<club_ville>/"

    Fonction affichant la liste des titulaires d'un club.

    Args:
        club_ville (str): Nom de la ville du club

    Returns:
        Template: template titulaires.html

    """

    club = Club.query.filter_by(ville=club_ville).first()
    titulaires = get_titulaires_dict(Titulaire.query.filter_by(club_id = club.id).all())
    clubs = Club.query.all()
    sexes = Sexe.query.all()

    return render_template("titulaires.html", title=club.ville[0].upper() + club.ville[1:], titulaires=titulaires, clubs=clubs, sexes=sexes)

@views.route("/titulaires/", methods=['POST'])
@login_required
def add_titulaire() :
    """Fonction liée au end-point "/titulaires/ en method POST"

    Fonction ajoutant un titulaire

    Returns:
        Redirect: redirection vers views.titulaire

    """

    nom = request.form.get('name')
    if nom is None or nom == "" :
        titulaires = Titulaire.query.all()
        clubs = Club.query.all()
        sexes = Sexe.query.all()
        return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes, name=True)

    prenom = request.form.get('surname')
    if prenom is None or prenom == "" :
        titulaires = Titulaire.query.all()
        clubs = Club.query.all()
        sexes = Sexe.query.all()
        return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes, surname=True)

    date_naissance = request.form.get('birthDate')
    if date_naissance is None or date_naissance == "" or len(date_naissance.split("-")) != 3 or len(date_naissance.split("-")[2]) <= 0 or len(date_naissance.split("-")[2]) > 2 or len(date_naissance.split("-")[1]) <= 0 or len(date_naissance.split("-")[1]) > 2 or len(date_naissance.split("-")[0]) < 4:
        titulaires = Titulaire.query.all()
        clubs = Club.query.all()
        sexes = Sexe.query.all()
        return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes, birthDate=True)

    club_id = request.form.get('clubId')
    if club_id is None or club_id == "" or Club.query.filter_by(id=club_id).first() is None :
        titulaires = Titulaire.query.all()
        clubs = Club.query.all()
        sexes = Sexe.query.all()
        return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes, clubId=True)

    numero_plaque = request.form.get('plaqueNb')
    if numero_plaque is None or numero_plaque == "" or not check_titulaire_number( Club.query.filter_by(id=club_id).first().titulaires, numero_plaque) is not None or int(numero_plaque)>=100 :
        titulaires = Titulaire.query.all()
        clubs = Club.query.all()
        sexes = Sexe.query.all()
        return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes, plaqueNb=True)

    sexe_id = request.form.get('sexeId')
    if sexe_id is None or sexe_id == "" or Sexe.query.filter_by(id=sexe_id).first() is None :
        titulaires = Titulaire.query.all()
        clubs = Club.query.all()
        sexes = Sexe.query.all()
        return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes, sexeId=True)
    print("oui")
    print(sexe_id)

    date_naissance = datetime.strptime(date_naissance, '%Y-%m-%d')
    if len(numero_plaque) < 2 :
        numero_plaque = "0" + numero_plaque


    print("test une personne")
    print(nom)
    print(prenom)
    print(date_naissance)
    print(club_id)
    print(numero_plaque)
    print(sexe_id)
    new_titulaire = Titulaire(nom=nom.upper(), prenom=prenom, date_naissance=date_naissance, club_id=club_id, numero_plaque=numero_plaque, sexe_id=sexe_id)
    db.session.add(new_titulaire)
    db.session.commit()

    return redirect(url_for('views.titulaires'))

@views.route("/add_titulaires/", methods=['GET','POST'])
@login_required
def add_titulaires() :
    """Fonction liée au end-point "/titulaires/"

    Fonction ajoutant des titulaires via un fichier xls

    Returns:
        Redirect: redirection vers views.titulaire

    """
    if request.method == 'POST':
        """TEST DEBUGER SUR L OBJET FILE"""
        """print("test")
        file = request.files['xls']
        print(file.read())
        lignes = file.readlines()"""

        uploaded_file = request.files['xls']
        if uploaded_file.filename != '':
            uploaded_file.save(uploaded_file.filename)

        files = xlrd.open_workbook(uploaded_file.filename)

        file = files.sheet_by_index(0)

        indiceFirstRow = file.nrows-1
        indiceFirstColumn = file.ncols-1

        """pour avoir la première colonne"""
        while(file.cell_value(indiceFirstRow,indiceFirstColumn) != '' and indiceFirstColumn != 0):
            indiceFirstColumn -= 1

        """se redécaler d'une colonne vers la droite"""
        if(file.cell_value(indiceFirstRow,indiceFirstColumn) == ''):
            indiceFirstColumn += 1

        while(file.cell_value(indiceFirstRow,indiceFirstColumn) != '' and indiceFirstRow != 0):
            indiceFirstRow -= 1

        """se redécaler de deux cases vers le haut (titre)"""
        if(file.cell_value(indiceFirstRow,indiceFirstColumn) == ''):
            indiceFirstRow += 2
        else:
            indiceFirstRow += 1

        np_nom = []
        np_dateNaissance = []
        np_club = []
        np_plaque = []
        np_sexe = []



        for i in range(indiceFirstRow, file.nrows):
            np_nom.append(file.cell_value(i, 0+indiceFirstColumn))
            np_dateNaissance.append(file.cell_value(i, 1+indiceFirstColumn))
            np_club.append(file.cell_value(i, 2+indiceFirstColumn))
            np_plaque.append(file.cell_value(i, 3+indiceFirstColumn))
            np_sexe.append(file.cell_value(i, 4+indiceFirstColumn))

        np_nom = np.array(np_nom)
        np_dateNaissance = np.array(np_dateNaissance)
        np_club = np.array(np_club)
        np_plaque = np.array(np_plaque)
        np_sexe = np.array(np_sexe)

        nom = np_nom[0]
        prenom = "LOUIS"
        date_naissance = np_dateNaissance[0]
        club_id = np_club[0]
        numero_plaque = np_plaque[0]
        sexe_id = np_sexe[0]

        "test fichier"
        print(nom)
        print(prenom)
        print(date_naissance)
        print(club_id)
        print(numero_plaque)
        print(sexe_id)


        """if nom is None or nom == "":
            titulaires = Titulaire.query.all()
            clubs = Club.query.all()
            sexes = Sexe.query.all()
            return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes,
                                   name=True)


        if prenom is None or prenom == "":
            titulaires = Titulaire.query.all()
            clubs = Club.query.all()
            sexes = Sexe.query.all()
            return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes,
                                   surname=True)

        if date_naissance is None or date_naissance == "" or len(date_naissance.split("-")) != 3 or len(
                date_naissance.split("-")[2]) <= 0 or len(date_naissance.split("-")[2]) > 2 or len(
                date_naissance.split("-")[1]) <= 0 or len(date_naissance.split("-")[1]) > 2 or len(
                date_naissance.split("-")[0]) < 4:
            titulaires = Titulaire.query.all()
            clubs = Club.query.all()
            sexes = Sexe.query.all()
            return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes,
                                   birthDate=True)


        if club_id is None or club_id == "" or Club.query.filter_by(id=club_id).first() is None:
            titulaires = Titulaire.query.all()
            clubs = Club.query.all()
            sexes = Sexe.query.all()
            return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes,
                                   clubId=True)


        if numero_plaque is None or numero_plaque == "" or not check_titulaire_number(
                Club.query.filter_by(id=club_id).first().titulaires, numero_plaque) is not None or int(
                numero_plaque) >= 100:
            titulaires = Titulaire.query.all()
            clubs = Club.query.all()
            sexes = Sexe.query.all()
            return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes,
                                   plaqueNb=True)

        if sexe_id is None or sexe_id == "" or Sexe.query.filter_by(id=sexe_id).first() is None:
            titulaires = Titulaire.query.all()
            clubs = Club.query.all()
            sexes = Sexe.query.all()
            return render_template("titulaires.html", title="tous", titulaires=titulaires, clubs=clubs, sexes=sexes,
                                   sexeId=True)
        print("oui")
        print(sexe_id)

        date_naissance = datetime.strptime(date_naissance, '%Y-%m-%d')
        if len(numero_plaque) < 2:
            numero_plaque = "0" + numero_plaque
"""
        new_titulaire = Titulaire(nom=nom.upper(), prenom=prenom, date_naissance=date_naissance, club_id=club_id,
                                  numero_plaque=numero_plaque, sexe_id=sexe_id)
        db.session.add(new_titulaire)
        db.session.commit()

        """for ligne in lignes:
            print(ligne)"""
        print("test")
        print(uploaded_file.filename)
        """for ligne in lignes:
            print(ligne)"""

        """data = file.read()
        print(data)
        
       file = request.files['xls']
        print("test")
        files = xlrd.open_workbook(file)"""
        """file = request.files['xls']"""
        """sheetRG = file.sheet_by_index(0)
        nom = []
        dateNaisssance = []
        club = []
        plaque = []
        sexe = []

        for i in range(1, sheetRG.ncols):
            nom.append(file.cell_value(0, i))
            dateNaisssance.append(file.cell_value(1, i))
            club.append(file.cell_value(2, i))
            plaque.append(file.cell_value(3, i))
            sexe.append(file.cell_value(4, i))

        nom = np.array(nom)
        dateNaisssance = np.array(dateNaisssance)
        club = np.array(club)
        plaque = np.array(plaque)
        sexe = np.array(sexe)

        for i in range(1, nom.size):
            print(nom[i])"""

    """file = request.files['file']"""
    """print(file.filename)"""
    """lignes = file.readlines()"""
    """for ligne in lignes:
        print(ligne)"""
    return redirect(url_for('views.titulaires'))
    """mettre nom, prenom,... ce que j'ai dans le fichier
    
    new_titulaire = Titulaire(nom=nom.upper(), prenom=prenom, date_naissance=date_naissance, club_id=club_id,
                              numero_plaque=numero_plaque, sexe_id=sexe_id)
    db.session.add(new_titulaire)
    db.session.commit()"""

    """return redirect(url_for('views.titulaires'))"""

@views.route("/titulaires/delete", methods=['POST'])
@login_required
def delete_titulaire() :
    """Fonction liée au end-point "/titulaires/delete en method POST"

    Fonction supprimant un titulaire, à utiliser en tant qu'API en JS

    Returns:
        Json: résultat de la suppression

    """

    titulaire_id = request.form.get('titulaire_id')
    if titulaire_id is not None :
        titulaire = Titulaire.query.filter_by(id=titulaire_id).first()
        if titulaire is not None :
            db.session.delete(titulaire)
            db.session.commit()

            return jsonify({'status': 'ok'})
        else :
            return jsonify({'status': 'error'})

@views.route("/clubs/")
@login_required
def clubs() :
    """Fonction liée au end-point "/clubs/"

    Fonction affichant la liste des clubs.

    Returns:
        Template: template clubs.html

    """

    clubs = Club.query.all()

    return render_template("clubs.html", clubs=clubs)


@views.route("/clubs/", methods=['POST'])
@login_required
def add_club() :
    """Fonction liée au end-point "/clubs/ en method POST"

    Fonction ajoutant un club.

    Returns:
        Redirect : redirection vers views.club

    """

    ville = request.form.get('city')

    if ville is None or ville == "" or Club.query.filter_by(ville=ville.lower()).first() is not None :
        clubs = Club.query.all()
        return render_template("clubs.html", clubs=clubs, ville=True)

    initiales = request.form.get('initiales')

    if initiales is None or initiales == "" or Club.query.filter_by(initiales=initiales).first() is not None :
        clubs = Club.query.all()
        return render_template("clubs.html", clubs=clubs, initiales=True)

    new_club = Club(ville=ville.lower(), initiales=initiales.upper())
    db.session.add(new_club)
    db.session.commit()

    return redirect(url_for('views.clubs'))

@views.route("/championnats/")
@login_required
def championnats() :
    """Fonction liée au end-point "/championnats/"

    Fonction affichant la liste des championnats

    Returns:
        Template: template championnats.html

    """

    championnat_types = Championnat_type.query.all()
    championnats = get_championnats_dict()


    return render_template("championnats.html", championnats=championnats, championnat_types=championnat_types)


@views.route("/championnats/", methods=['POST'])
@login_required
def add_championnat() :
    """Fonction liée au end-point "/championnats/ en method POST"

    Fonction ajoutant un championnat

    Returns:
        Redirect: redirection vers views.championnats

    """

    championnat_type = request.form.get('championnatTypeId')
    if championnat_type is None or championnat_type == 'none' or Championnat_type.query.filter_by(id=championnat_type).first() is None :
        championnat_types = Championnat_type.query.all()
        championnats = get_championnats_dict()

        return render_template("championnats.html", championnats=championnats, championnat_types=championnat_types, type=True)

    annee = request.form.get('annee')
    if annee is None or annee == "" or Championnat.query.filter_by(annee=annee, championnat_type_id=championnat_type).first() is not None :
        championnat_types = Championnat_type.query.all()
        championnats = get_championnats_dict()

        return render_template("championnats.html", championnats=championnats, championnat_types=championnat_types, annee=True)



    new_championnat = Championnat(championnat_type_id=championnat_type, annee=annee)
    db.session.add(new_championnat)
    db.session.commit()

    return redirect(url_for('views.championnats'))


@views.route("/championnat-<championnat_id>/etapes/")
@login_required
def etapes(championnat_id) :
    """Fonction liée au end-point "/championnat-<championnat_id>/etapes/"

    Fonction affichant la liste des étapes d'un championnat.

    Args:
        championnat_id (int): id du championnat

    Returns:
        Template: template etapes.html

    """

    championnat = Championnat.query.filter_by(id=championnat_id).first()

    if championnat is not None :
        championnat_type = Championnat_type.query.filter_by(id=championnat.championnat_type_id).first().type
        clubs = Club.query.all()
        etapes = get_etapes_dict(championnat)
        return render_template('etapes.html', championnat=championnat, championnat_type=championnat_type, clubs=clubs, etapes=etapes)


    return render_template('404.html'), 404

@views.route("/championnat-<championnat_id>/etapes/", methods=['POST'])
@login_required
def add_etape(championnat_id) :
    """Fonction liée au end-point "/championnat-<championnat_id>/etapes/ en method POST"

    Fonction ajoutant une étape à un championnat

    Args:
        championnat_id (int): id du championnat

    Returns:
        Redirect: redirection vers views.etapes

    """

    championnat = Championnat.query.filter_by(id=championnat_id).first()
    if championnat is not None :

        lieu_id = request.form.get('lieuId')

        if lieu_id is None or lieu_id == "none" or Club.query.filter_by(id=lieu_id).first() is None :

            championnat_type = Championnat_type.query.filter_by(id=championnat.championnat_type_id).first().type
            clubs = Club.query.all()
            etapes = get_etapes_dict(championnat)
            return render_template('etapes.html', championnat=championnat, championnat_type=championnat_type, clubs=clubs, etapes=etapes, lieu=True)

        nb_etapes_max = Championnat_type.query.filter_by(id=championnat.championnat_type_id).first().nb_etapes_max

        if nb_etapes_max > len(championnat.etapes) :
            new_etape = Etape(lieu_id=lieu_id, championnat_id=championnat_id)
            db.session.add(new_etape)
            db.session.commit()
        else :
            championnat_type = Championnat_type.query.filter_by(id=championnat.championnat_type_id).first().type
            clubs = Club.query.all()
            etapes = get_etapes_dict(championnat)
            return render_template('etapes.html', championnat=championnat, championnat_type=championnat_type, clubs=clubs, etapes=etapes, lieu=True)

    return redirect(url_for('views.etapes', championnat_id=championnat_id))

@views.route("/championnat-<championnat_id>/etape-<etape_id>/categories/")
@login_required
def etape(etape_id, championnat_id) :
    """Fonction liée au end-point "/championnat-<championnat_id>/etape-<etape_id>/categories/"

    Fonction affichant la liste des catégories d'une étape.

    Args:
        etape_id (int): id de l'étape
        championnat_id (int): id du championnat

    Returns:
        Template: template etape.html

    """

    etape = Etape.query.filter_by(id=etape_id).first()
    if etape is not None :

        participants = []

        titulaires_list = Titulaire.query.order_by(Titulaire.nom).all()
        titulaires = []
        for titulaire in titulaires_list :
            participate = False
            if Participant_etape.query.filter_by(etape_id=etape.id, titulaire_id=titulaire.id).first() is not None :
                participate = True

            if participate :
                participants.append(titulaire)

            titulaires.append({
                'id': titulaire.id,
                'name': titulaire.nom + " " + titulaire.prenom,
                'participate': participate,
            })

        categorie_types_list = Categorie_type.query.all()
        categorie_types = {}

        for categorie_type in categorie_types_list :

            categorie_types[categorie_type.name] = {
                'nb_participants': len(Participant_etape.query.filter_by(etape_id=etape.id, categorie_type_id=categorie_type.id).all()),
                'id': categorie_type.id
            }

        return render_template('etape.html', titulaires=titulaires, championnat_id=etape.championnat_id, categorie_types=categorie_types, etape=etape)

    return render_template('404.html'), 404


@views.route("/championnat-<championnat_id>/etape-<etape_id>/categories/", methods=['POST'])
@login_required
def etape_change_participants(etape_id, championnat_id) :
    """Fonction liée au end-point "/championnat-<championnat_id>/etape-<etape_id>/categories/" en method POST

    Fonction générant la liste des participants à une étape et la structure de courses nécessaire

    Args:
        etape_id (int): id de l'étape
        championnat_id (int): id du championnat

    Returns:
        Redirect: redirect vers views.etape

    """

    etape = Etape.query.filter_by(id=etape_id).first()
    if etape is not None :

        #nettoyage des anciennes données de l'etape
        participants_etape = Participant_etape.query.filter_by(etape_id=etape_id).all()
        for participant_etape in participants_etape :
            db.session.delete(participant_etape)

        for race in etape.races :

            for manche in race.manches :
                participants_manche = Participant_manche.query.filter_by(manche_id=manche.id).all()
                for participant_manche in participants_manche :
                    db.session.delete(participant_manche)
                db.session.delete(manche)

            participants_race = Participant_race.query.filter_by(race_id=race.id).all()
            for participant_race in participants_race :
                db.session.delete(participant_race)
            db.session.delete(race)

        for categorie in etape.categories :
            for participant_categorie in categorie.participations :
                db.session.delete(participant_categorie)
            db.session.delete(categorie)
        db.session.commit()

        for new_participant_id in request.form :
            if request.form.get(new_participant_id) == "on" :
                titulaire = Titulaire.query.filter_by(id=new_participant_id).first()
                if titulaire is not None :

                    year = Championnat.query.filter_by(id=etape.championnat_id).first().annee
                    participant_age = year - titulaire.date_naissance.year
                    for categorie_type in Categorie_type.query.all() :
                        if participant_age>=categorie_type.min_age and participant_age<=categorie_type.max_age :
                            new_participant = Participant_etape(etape_id=etape_id, titulaire_id=new_participant_id, categorie_type_id=categorie_type.id)
                            db.session.add(new_participant)

        db.session.commit()

        #creation de l'architecture des courses + phases de pool
        phase_pool = Race_type.query.filter_by(type="Pool").first()
        for categorie_type in Categorie_type.query.all() :
            participants_etape = Participant_etape.query.filter_by(etape_id=etape_id, categorie_type_id=categorie_type.id).all()
            random.shuffle(participants_etape)
            if participants_etape is not None :
                nb_participants = len(participants_etape)
                couloirs = Couloir.query.all()
                random.shuffle(couloirs)

                if nb_participants > 0 :
                    new_categorie = Categorie(etape_id=etape_id, categorie_type_id=categorie_type.id)
                    db.session.add(new_categorie)
                    db.session.commit()

                    for participant_etape in participants_etape :
                        new_participant_categorie = Participant_categorie(titulaire_id=participant_etape.titulaire_id, categorie_id=new_categorie.id)
                        db.session.add(new_participant_categorie)
                    db.session.commit()

                if nb_participants > 0 and nb_participants <= 8 :
                    race_a = Race(name="A", etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_pool.id, categorie_id=new_categorie.id)
                    db.session.add(race_a)
                    db.session.commit()

                    for index_participant, participant_etape in enumerate(participants_etape) :
                        new_participant_race = Participant_race(titulaire_id=participant_etape.titulaire_id, race_id=race_a.id, couloir_id=couloirs[index_participant].id)
                        db.session.add(new_participant_race)
                    db.session.commit()

                    participants_race = Participant_race.query.filter_by(race_id=race_a.id)
                    for i in range(5) :
                        new_manche = Manche(race_id=race_a.id)
                        db.session.add(new_manche)
                        db.session.commit()

                        for index_participant, participant_race in enumerate(participants_race) :
                            couloir = Couloir.query.filter_by(id=participant_race.couloir_id).first()
                            if i == 0 :
                                place_depart = couloir.couloir_1
                            elif i == 1 :
                                place_depart = couloir.couloir_2
                            elif i == 2 :
                                place_depart = couloir.couloir_3
                            elif i == 3 :
                                place_depart = couloir.couloir_4
                            elif i == 4 :
                                place_depart = couloir.couloir_5

                            new_participant_manche = Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=new_manche.id, place_depart=place_depart)
                            db.session.add(new_participant_manche)
                        db.session.commit()


                elif nb_participants >= 9 :
                    race_names = ['A', 'B', 'C', 'D', 'E', 'F']
                    nb_races = ceil(nb_participants/8)
                    participants_par_race = [0 for i in range(nb_races)]

                    for i in range(nb_participants) :
                        participants_par_race[i%nb_races] += 1

                    for index_race in range(nb_races) :
                        new_race = Race(name=race_names[index_race], etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_pool.id, categorie_id=new_categorie.id)
                        db.session.add(new_race)

                    races = Race.query.filter_by(etape_id=etape_id, categorie_type_id=categorie_type.id).all()
                    index_participant_etape = 0
                    for index_race, race in enumerate(races) :
                        nb_participants_race = participants_par_race[index_race]
                        for index_participant_race in range(nb_participants_race) :
                            new_participant_race =  Participant_race(titulaire_id=participants_etape[index_participant_etape].titulaire_id, race_id=race.id, couloir_id=couloirs[index_participant_race].id)
                            db.session.add(new_participant_race)
                            index_participant_etape += 1
                        db.session.commit()

                        participants_race = Participant_race.query.filter_by(race_id=race.id).all()
                        for i in range(3) :
                            new_manche = Manche(race_id=race.id)
                            db.session.add(new_manche)
                            db.session.commit()

                            for index_participant, participant_race in enumerate(participants_race) :
                                couloir = Couloir.query.filter_by(id=participant_race.couloir_id).first()
                                if i == 0 :
                                    place_depart = couloir.couloir_1
                                elif i == 1 :
                                    place_depart = couloir.couloir_2
                                elif i == 2 :
                                    place_depart = couloir.couloir_3


                                new_participant_manche = Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=new_manche.id, place_depart=place_depart)
                                db.session.add(new_participant_manche)
                            db.session.commit()

                    phase_final = Race_type.query.filter_by(type="Finale").first()
                    for index_race in range(nb_races) :
                        new_race = Race(name=race_names[index_race], etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_final.id, categorie_id=new_categorie.id)
                        db.session.add(new_race)
                    db.session.commit()

                    if nb_participants >= 17 :
                        phase_demi = Race_type.query.filter_by(type="1/2 Finale").first()
                        for index_race in range(2) :
                            new_race = Race(name=race_names[index_race], etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_demi.id, categorie_id=new_categorie.id)
                            db.session.add(new_race)
                        db.session.commit()

                        if nb_participants >= 33 :
                            phase_quart = Race_type.query.filter_by(type="1/4 Finale").first()
                            for index_race in range(4) :
                                new_race = Race(name=race_names[index_race], etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_demi.id, categorie_id=new_categorie.id)
                                db.session.add(new_race)
                            db.session.commit()




    return redirect(url_for('views.etape', etape_id=etape_id, championnat_id=Championnat.query.filter_by(id=etape.championnat_id).first().id))


@views.route("/championnat-<championnat_id>/etape-<etape_id>/categorie-<categorie_type_id>/races")
@login_required
def races(etape_id, championnat_id, categorie_type_id) :
    """Fonction liée au end-point "/championnat-<championnat_id>/etape-<etape_id>/categorie-<categorie_type_id>/races"

    Fonction affichant la liste des races d'une catégorie

    Args:
        etape_id (int): id de l'étape
        championnat_id (int): id du championnat
        categorie_type_id (int): id de la catégorie

    Returns:
        Template: template races.html

    """

    races = Race.query.filter_by(etape_id=etape_id, categorie_type_id=categorie_type_id).order_by(Race.name).all()
    etape = Etape.query.filter_by(id=etape_id).first()
    categorie_type = Categorie_type.query.filter_by(id=categorie_type_id).first()
    club = etape.club

    return render_template("races.html", championnat_id=championnat_id, races=races, categorie_type=categorie_type, etape=etape, club=club)

@views.route("/championnat-<championnat_id>/etape-<etape_id>/categorie-<categorie_type_id>/races", methods=['POST'])
@login_required
def genere_phase_suivante(etape_id, championnat_id, categorie_type_id) :
    """Fonction liée au end-point "/championnat-<championnat_id>/etape-<etape_id>/categorie-<categorie_type_id>/races" en methode POST

    Fonction générant la phase de course suivante (phase demi-finale, finale, etc ...)

    Args:
        etape_id (int): id de l'étape
        championnat_id (int): id du championnat
        categorie_type_id (int): id de la catégorie

    Returns:
        Redirect: redirection vers views.races

    """

    if etape_id == request.form.get('etape_id') :
        etape = Etape.query.filter_by(id=etape_id).first()
        categorie = Categorie.query.filter_by(etape_id=etape.id, categorie_type_id=categorie_type_id).first()
        nb_participants_categorie = len(categorie.participations)

        phase_pool = Race_type.query.filter_by(type="Pool").first()
        phase_finale = Race_type.query.filter_by(type="Finale").first()
        phase_demi = Race_type.query.filter_by(type="1/2 Finale").first()
        phase_quart = Race_type.query.filter_by(type="1/4 Finale").first()

        if categorie.pool_finie :
            calcul_points_race(Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id).all())
        if categorie.quart_finie :
            calcul_points_race(Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id).all())
        if categorie.demi_finie :
            calcul_points_race(Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id).all())
        if categorie.finale_finie :
            calcul_points_race(Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id).all())

        if categorie.pool_finie :

            if not categorie.quart_finie and not categorie.quart_genere :
                if nb_participants_categorie >= 33 :
                    pool_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="A").first()
                    pool_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="B").first()
                    pool_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="C").first()
                    pool_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="D").first()
                    pool_race_e = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="E").first()

                    quart_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="A").first()
                    quart_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="B").first()
                    quart_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="C").first()
                    quart_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="D").first()

                    db.session.add(Manche(race_id=quart_race_a.id))
                    db.session.add(Manche(race_id=quart_race_b.id))
                    db.session.add(Manche(race_id=quart_race_c.id))
                    db.session.add(Manche(race_id=quart_race_d.id))
                    db.session.commit()

                    couloirs = Couloir.query.all()

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=pool_race_a.participations[0].titulaire_id, race_id=quart_race_a.id, couloir_id=couloirs[0]))
                    db.session.add(Participant_race(titulaire_id=pool_race_b.participations[0].titulaire_id, race_id=quart_race_a.id, couloir_id=couloirs[1]))
                    db.session.add(Participant_race(titulaire_id=pool_race_c.participations[1].titulaire_id, race_id=quart_race_a.id, couloir_id=couloirs[2]))
                    db.session.add(Participant_race(titulaire_id=pool_race_b.participations[2].titulaire_id, race_id=quart_race_a.id, couloir_id=couloirs[3]))
                    db.session.add(Participant_race(titulaire_id=pool_race_c.participations[3].titulaire_id, race_id=quart_race_a.id, couloir_id=couloirs[4]))

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=pool_race_c.participations[0].titulaire_id, race_id=quart_race_b.id, couloir_id=couloirs[0]))
                    db.session.add(Participant_race(titulaire_id=pool_race_a.participations[1].titulaire_id, race_id=quart_race_b.id, couloir_id=couloirs[1]))
                    db.session.add(Participant_race(titulaire_id=pool_race_b.participations[1].titulaire_id, race_id=quart_race_b.id, couloir_id=couloirs[2]))
                    db.session.add(Participant_race(titulaire_id=pool_race_c.participations[2].titulaire_id, race_id=quart_race_b.id, couloir_id=couloirs[3]))
                    db.session.add(Participant_race(titulaire_id=pool_race_b.participations[3].titulaire_id, race_id=quart_race_b.id, couloir_id=couloirs[4]))

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=pool_race_d.participations[0].titulaire_id, race_id=quart_race_c.id, couloir_id=couloirs[0]))
                    db.session.add(Participant_race(titulaire_id=pool_race_e.participations[1].titulaire_id, race_id=quart_race_c.id, couloir_id=couloirs[1]))
                    db.session.add(Participant_race(titulaire_id=pool_race_a.participations[2].titulaire_id, race_id=quart_race_c.id, couloir_id=couloirs[2]))
                    db.session.add(Participant_race(titulaire_id=pool_race_d.participations[2].titulaire_id, race_id=quart_race_c.id, couloir_id=couloirs[3]))
                    db.session.add(Participant_race(titulaire_id=pool_race_e.participations[3].titulaire_id, race_id=quart_race_c.id, couloir_id=couloirs[4]))

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=pool_race_e.participations[0].titulaire_id, race_id=quart_race_d.id, couloir_id=couloirs[0]))
                    db.session.add(Participant_race(titulaire_id=pool_race_d.participations[1].titulaire_id, race_id=quart_race_d.id, couloir_id=couloirs[1]))
                    db.session.add(Participant_race(titulaire_id=pool_race_e.participations[2].titulaire_id, race_id=quart_race_d.id, couloir_id=couloirs[2]))
                    db.session.add(Participant_race(titulaire_id=pool_race_a.participations[3].titulaire_id, race_id=quart_race_d.id, couloir_id=couloirs[3]))
                    db.session.add(Participant_race(titulaire_id=pool_race_d.participations[3].titulaire_id, race_id=quart_race_d.id, couloir_id=couloirs[4]))

                    db.session.commit()

                    for participant in quart_race_a.participations :
                        db.session.add(Participant_manche(participant.titulaire_id, manche_id=quart_race_a.manches[0].id, place_depart=participant.couloirs.couloir_1))
                    for participant in quart_race_b.participations :
                        db.session.add(Participant_manche(participant.titulaire_id, manche_id=quart_race_b.manches[0].id, place_depart=participant.couloirs.couloir_1))
                    for participant in quart_race_c.participations :
                        db.session.add(Participant_manche(participant.titulaire_id, manche_id=quart_race_c.manches[0].id, place_depart=participant.couloirs.couloir_1))
                    for participant in quart_race_d.participations :
                        db.session.add(Participant_manche(participant.titulaire_id, manche_id=quart_race_d.manches[0].id, place_depart=participant.couloirs.couloir_1))

                    db.session.commit()
                categorie.quart_genere = True
                db.session.commit()

            elif not categorie.demi_finie and not categorie.demi_genere :
                if nb_participants_categorie >= 17 :
                    if nb_participants_categorie >= 17 and nb_participants_categorie <= 19 :

                        pool_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="A").first()
                        pool_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="B").first()
                        pool_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="C").first()

                        demi_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="A").first()
                        demi_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="B").first()

                        db.session.add(Manche(race_id=demi_race_a.id))
                        db.session.add(Manche(race_id=demi_race_b.id))

                        couloirs = Couloir.query.all()

                        random.shuffle(couloirs)
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[0]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[1]))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[1].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[2]))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[3]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[4]))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[3].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[5]))

                        random.shuffle(couloirs)
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[0].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[0]))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[1]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[2]))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[2].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[3]))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[4]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[5]))

                        db.session.commit()

                        for participant in demi_race_a.participations :
                            db.session.add(Participant_manche(participant.titulaire_id, manche_id=demi_race_a.manches[0].id, place_depart=participant.couloirs.couloir_1))
                        for participant in demi_race_b.participations :
                            db.session.add(Participant_manche(participant.titulaire_id, manche_id=demi_race_b.manches[0].id, place_depart=participant.couloirs.couloir_1))

                        db.session.commit()

                    elif nb_participants_categorie >= 20 and nb_participants_categorie <= 32 :

                        pool_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="A").first()
                        pool_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="B").first()
                        pool_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="C").first()
                        pool_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="D").first()

                        demi_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="A").first()
                        demi_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="B").first()

                        db.session.add(Manche(race_id=demi_race_a.id))
                        db.session.add(Manche(race_id=demi_race_b.id))

                        couloirs = Couloir.query.all()

                        random.shuffle(couloirs)
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[0]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[1]))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[1].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[2]))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[1].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[3]))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[4]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[5]))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[3].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[6]))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[3].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[7]))

                        random.shuffle(couloirs)
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[0].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[0]))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[0].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[1]))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[2]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[3]))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[2].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[4]))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[2].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[5]))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[6]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[7]))

                        db.session.commit()

                        for participant in demi_race_a.participations :
                            db.session.add(Participant_manche(participant.titulaire_id, manche_id=demi_race_a.manches[0].id, place_depart=participant.couloirs.couloir_1))
                        for participant in demi_race_b.participations :
                            db.session.add(Participant_manche(participant.titulaire_id, manche_id=demi_race_b.manches[0].id, place_depart=participant.couloirs.couloir_1))

                        db.session.commit()

                    elif nb_participants_categorie >= 33 :

                        quart_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="A").first()
                        quart_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="B").first()
                        quart_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="C").first()
                        quart_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="D").first()

                        demi_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="A").first()
                        demi_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="B").first()

                        db.session.add(Manche(race_id=demi_race_a.id))
                        db.session.add(Manche(race_id=demi_race_b.id))

                        couloirs = Couloir.query.all()

                        random.shuffle(couloirs)
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[0]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[1]))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[1].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[2]))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[1].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[3]))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[4]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[5]))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[3].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[6]))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[3].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[7]))

                        random.shuffle(couloirs)
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[0].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[0]))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[0].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[1]))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[2]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[3]))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[2].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[4]))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[2].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[5]))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[6]))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[7]))

                        db.session.commit()

                        for participant in demi_race_a.participations :
                            db.session.add(Participant_manche(participant.titulaire_id, manche_id=demi_race_a.manches[0].id, place_depart=participant.couloirs.couloir_1))
                        for participant in demi_race_b.participations :
                            db.session.add(Participant_manche(participant.titulaire_id, manche_id=demi_race_b.manches[0].id, place_depart=participant.couloirs.couloir_1))

                        db.session.commit()
                categorie.demi_genere = True
                db.session.commit()

            elif not categorie.finale_finie and not categorie.finale_genere :
                if nb_participants_categorie >= 9 and nb_participants_categorie <= 16 :

                    if nb_participants_categorie == 9 :
                        limit = 3
                    else :
                        limit = 4

                    pool_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="A").first()
                    pool_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="B").first()

                    finale_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="A").first()
                    finale_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="B").first()

                    for i in range(2) :
                        db.session.add(Manche(race_id=finale_race_a.id))
                    for i in range(2) :
                        db.session.add(Manche(race_id=finale_race_b.id))
                    db.session.commit()

                    couloirs_a = Couloir.query.all()
                    random.shuffle(couloirs_a)
                    couloirs_b = Couloir.query.all()
                    random.shuffle(couloirs_b)
                    index_couloir_a = 0
                    index_couloir_b = 0

                    for index_participant, participant in enumerate(pool_race_a.participations) :
                        if index_participant < limit :
                            db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs_a[index_couloir_a].id))
                            index_couloir_a += 1
                        else :
                            db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs_b[index_couloir_b].id))
                            index_couloir_b += 1
                    for index_participant, participant in enumerate(pool_race_b.participations) :
                        if index_participant < limit :
                            db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs_a[index_couloir_a].id))
                            index_couloir_a += 1
                        else :
                            db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs_b[index_couloir_b].id))
                            index_couloir_b += 1

                    db.session.commit()

                    for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race_a.id).all()) :
                        for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                            if index_manche == 0 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                            elif index_manche == 1 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))

                    for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race_b.id).all()) :
                        for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                            if index_manche == 0 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                            elif index_manche == 1 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))

                    db.session.commit()



                elif nb_participants_categorie >= 17 and nb_participants_categorie <= 32 :

                    limit = 4

                    demi_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="A").first()
                    demi_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="B").first()

                    finale_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="A").first()
                    finale_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="B").first()

                    db.session.add(Manche(race_id=finale_race_a.id))
                    db.session.add(Manche(race_id=finale_race_b.id))
                    for i in range(2) :
                        db.session.add(Manche(race_id=finale_race_c.id))
                    db.session.commit()

                    couloirs_a = Couloir.query.all()
                    random.shuffle(couloirs_a)
                    couloirs_b = Couloir.query.all()
                    random.shuffle(couloirs_b)
                    index_couloir_a = 0
                    index_couloir_b = 0

                    for index_participant, participant in enumerate(demi_race_a.participations) :
                        if index_participant < limit :
                            db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs_a[index_couloir_a].id))
                            index_couloir_a += 1
                        else :
                            db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs_b[index_couloir_b].id))
                            index_couloir_b += 1
                    for index_participant, participant in enumerate(demi_race_b.participations) :
                        if index_participant < limit :
                            db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs_a[index_couloir_a].id))
                            index_couloir_a += 1
                        else :
                            db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs_b[index_couloir_b].id))
                            index_couloir_b += 1

                    for participant in demi_race_a.participations :
                        db.session.add(Participant_manche(participant.titulaire_id, manche_id=demi_race_a.manches[0].id, place_depart=participant.couloirs.couloir_1))
                    for participant in demi_race_b.participations :
                        db.session.add(Participant_manche(participant.titulaire_id, manche_id=demi_race_b.manches[0].id, place_depart=participant.couloirs.couloir_1))

                    pool_races = Race.query.filter_by(categorie_id=categorie.id, race_type=phase_pool.id).all()

                    finale_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="C").first()
                    for i in range(2) :
                        db.session.add(Manche(race_id=finale_race_c.id))
                    couloirs_c = Couloir.query.all()
                    random.shuffle(couloir_c)
                    index_couloir_c = 0
                    if nb_participants_categorie >= 25 :
                        finale_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="D").first()
                        for i in range(2) :
                            db.session.add(Manche(race_id=finale_race_d.id))
                        couloirs_d = Couloir.query.all()
                        random.shuffle(couloir_d)
                    add_race_c = True

                    for race in pool_races :
                        for participant in race.participation[3:] :
                            if nb_participants_categorie <= 24 or add_race_c :
                                db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_c.id, couloir_id=couloirs_c[index_couloir_c].id))
                                finale_race = finale_race_c
                                index_couloir_c += 1
                                add_race_c = False
                            else :
                                db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_d.id, couloir_id=couloirs_c[index_couloir_d]))
                                finale_race = finale_race_d
                                index_couloir_d += 1
                                add_race_c = True

                            db.session.commit()
                            for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race.id).all()) :
                                for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                                    if index_manche == 0 :
                                        db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                                    elif index_manche == 1 :
                                        db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))

                    db.session.commit()

                elif nb_participants_categorie >= 33 :

                    demi_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="A").first()
                    demi_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="B").first()

                    finale_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="A").first()
                    finale_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="B").first()


                    db.session.add(Manche(race_id=finale_race_a.id))
                    db.session.add(Manche(race_id=finale_race_b.id))

                    couloirs = Couloir.query.all()

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[0].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[0]))
                    db.session.add(Participant_race(titulaire_id=demi_race_c.participations[0].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[1]))
                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[1].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[2]))
                    db.session.add(Participant_race(titulaire_id=demi_race_d.participations[1].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[3]))
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[2].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[4]))
                    db.session.add(Participant_race(titulaire_id=demi_race_c.participations[2].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[5]))
                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[3].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[6]))
                    db.session.add(Participant_race(titulaire_id=demi_race_d.participations[3].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[7]))

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[0].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[0]))
                    db.session.add(Participant_race(titulaire_id=demi_race_d.participations[0].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[1]))
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[1].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[2]))
                    db.session.add(Participant_race(titulaire_id=demi_race_c.participations[1].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[3]))
                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[2].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[4]))
                    db.session.add(Participant_race(titulaire_id=demi_race_d.participations[2].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[5]))
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[3].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[6]))
                    db.session.add(Participant_race(titulaire_id=demi_race_c.participations[3].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[7]))

                    db.session.commit()

                    for participant in finale_race_a.participations :
                        db.session.add(Participant_manche(participant.titulaire_id, manche_id=finale_race_a.manches[0].id, place_depart=participant.couloirs.couloir_1))
                    for participant in finale_race_b.participations :
                        db.session.add(Participant_manche(participant.titulaire_id, manche_id=finale_race_b.manches[0].id, place_depart=participant.couloirs.couloir_1))

                    db.session.commit()

                    quart_races = Race.query.filter_by(categorie_id=categorie.id, race_type=quart_pool.id).all()
                    finale_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="C").first()
                    for i in range(2) :
                        db.session.add(Manche(race_id=finale_race_c.id))
                    db.session.commit()

                    random.shuffle(couloirs)
                    index_couloir_c = 0

                    for race in quart_race :
                        for participant in race.participation[3:] :
                            db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_c.id, couloir_id=couloirs[index_couloir_c]))
                            index_couloir_c += 1
                            db.session.commit()
                            for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race_c.id).all()) :
                                for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                                    if index_manche == 0 :
                                        db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                                    elif index_manche == 1 :
                                        db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))
                            db.session.commit()


                    pool_races = Race.query.filter_by(categorie_id=categorie.id, race_type=quart_pool.id).all()
                    finale_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="D").first()
                    finale_race_e = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="E").first()
                    for i in range(2) :
                        db.session.add(Manche(race_id=finale_race_d.id))
                    for i in range(2) :
                        db.session.add(Manche(race_id=finale_race_e.id))
                    db.session.commit()

                    add_race_d = True
                    couloirs_d = Couloir.query.all()
                    random.shuffle(couloirs_d)
                    index_couloir_d = 0
                    couloirs_e = Couloir.query.all()
                    random.shuffle(couloirs_e)
                    index_couloir_e = 0

                    for race in pool_race :
                        for participant in race.participation[3:] :
                            if add_race_d :
                                db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_d.id, couloir_id=couloirs_d[index_couloir_d].id))
                                index_couloir_d += 1
                                add_race_d = False
                                finale_race = finale_race_d
                            else :
                                db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_e.id, couloir_id=couloirs_e[index_couloir_e].id))
                                index_couloir_e += 1
                                add_race_d = True
                                finale_race = finale_race_e
                            db.session.commit()
                            for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race.id).all()) :
                                for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                                    if index_manche == 0 :
                                        db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                                    elif index_manche == 1 :
                                        db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))
                            db.session.commit()
                    db.session.commit()

                categorie.finale_genere = True
                db.session.commit()

        return redirect(url_for('views.races', etape_id=etape_id, championnat_id=championnat_id, categorie_type_id=categorie_type_id))


@views.route("/championnat-<championnat_id>/etape-<etape_id>/categorie-<categorie_type_id>/race-<race_id>/manches")
@login_required
def manches(etape_id, championnat_id, categorie_type_id, race_id) :
    """Fonction liée au end-point "/championnat-<championnat_id>/etape-<etape_id>/categorie-<categorie_type_id>/race-<race_id>/manches"

    Fonction affichant la liste des manches d'une race

    Args:
        etape_id (int): id de l'étape
        championnat_id (int): id du championnat
        categorie_type_id (int): id de la catégorie
        race_id (int): id de la race

    Returns:
        Template: template manches.html

    """

    manches = Manche.query.filter_by(race_id=race_id).all()
    race = Race.query.filter_by(id=race_id).first()
    etape = Etape.query.filter_by(id=etape_id).first()
    categorie_type = Categorie_type.query.filter_by(id=categorie_type_id).first()
    club = etape.club

    return render_template("manches.html", championnat_id=championnat_id, race=race, categorie_type=categorie_type, etape=etape, club=club, manches=manches)

@views.route("/championnat-<championnat_id>/etape-<etape_id>/categorie-<categorie_type_id>/race-<race_id>/manches", methods=['POST'])
@login_required
def manches_post(etape_id, championnat_id, categorie_type_id, race_id) :
    """Fonction liée au end-point "/championnat-<championnat_id>/etape-<etape_id>/categorie-<categorie_type_id>/race-<race_id>/manches" en methode POST

    Fonction enregistrant l'ordre d'arrivé des pilotes d'une manche

    Args:
        etape_id (int): id de l'étape
        championnat_id (int): id du championnat
        categorie_type_id (int): id de la catégorie
        race_id (int): id de la race

    Returns:
        Redirect: redirection vers views.manches

    """

    manche_id = request.form.get('manche_id')

    if manche_id is not None :
        manche = Manche.query.filter_by(id=manche_id).first()
        if manche is not None :
            for participant in manche.participations :
                place_arrive = request.form.get(f'place_arrive_{participant.titulaire.id}')
                if place_arrive is not None :
                    if place_arrive != "none" :
                        participant.resultat = place_arrive
                    else :
                        participant.resultat = 9

            manche.finie = True
            db.session.commit()

            race_finie = True
            race = Race.query.filter_by(id=race_id).first()
            for manche in race.manches :
                if not manche.finie :
                    race_finie = False
            race.finie = race_finie
            db.session.commit()

            categorie_pool_finie = True
            categorie_quart_finie = True
            categorie_demi_finie = True
            categorie_finale_finie = True

            etape = race.etape
            etape_finie = True

            phase_pool = Race_type.query.filter_by(type="Pool").first()
            phase_finale = Race_type.query.filter_by(type="Finale").first()
            phase_demi = Race_type.query.filter_by(type="1/2 Finale").first()
            phase_quart = Race_type.query.filter_by(type="1/4 Finale").first()

            for categorie in etape.categories :
                for race in categorie.races :
                    print(race.name, race.race_type.type)
                    if race.race_type_id == phase_pool.id and not race.finie :
                        categorie_pool_finie = False
                    elif race.race_type_id == phase_quart.id and not race.finie :
                        categorie_quart_finie = False
                    elif race.race_type_id == phase_demi.id and not race.finie :
                        categorie_demi_finie = False
                    elif race.race_type_id == phase_finale.id and not race.finie :
                        categorie_finale_finie = False

                categorie.pool_finie = categorie_pool_finie
                categorie.quart_finie = categorie_quart_finie
                categorie.demi_finie = categorie_demi_finie
                categorie.finale_finie = categorie_finale_finie
                db.session.commit()

                if categorie.pool_finie and categorie.quart_finie and categorie.demi_finie and categorie.finale_finie :
                    categorie.finie = True
                else :
                    categorie.finie = False
                    etape_finie = False
            etape.finie = etape_finie
            db.session.commit()

            championnat_finie = True
            championnat = etape.championnat
            for etape in championnat.etapes :
                if not etape.finie :
                    championnat_finie = False
            championnat.finie = championnat_finie
            db.session.commit()

        return redirect(url_for('views.manches', championnat_id=championnat_id, etape_id=etape_id, categorie_type_id=categorie_type_id, race_id=race_id))
