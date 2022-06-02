from cmath import log
from hmac import new
from operator import index, indexOf
from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
import sqlalchemy
import datetime
import random
from math import ceil
import numpy as np
import os

import xlrd
import os
if os.name == "nt":
    os.environ['PATH'] = r"GTK3" + os.pathsep + os.environ['PATH']
import weasyprint
from flask_weasyprint import HTML, render_pdf

from .__init__ import db
from .models import User, Titulaire, Club, Sexe, Championnat, Championnat_type, Etape, Categorie_type, Participant_etape, Race_type, Couloir, Race, Participant_race, Manche, Participant_manche, Categorie, Participant_categorie

views = Blueprint("views", __name__)


def get_titulaires_dict(titulaires):
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
            "plaque": str(titulaire.numero_plaque),
        })

        # ancienne facon d'avoir la plaque :  "plaque": club.initiales.upper() + " " + str(titulaire.numero_plaque),

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
        non ne retourne rien mais modifie l'attribut resultat d'un participant à une race en faisant le cumul de ces points lors des différentes manches de la race 
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

@views.route('/titulaires/<club_id>/',methods=["POST","GET"])
@login_required
def titulaires_by_ville(club_id) :
    """Fonction liée au end-point "/titulaires/<club_id>/"

    Fonction affichant la liste des titulaires d'un club.

    Args:
        club_id : id du club

    Returns:
        Template: template titulaires.html

    """
    if request.method == "POST":
        #on est dans le cas où formulaire de création de titulaire nous a été soumis, on contrôle et on insère
        #le titulaire si controle ok
        add_titulaire(club_id=club_id)
        
    club = Club.query.filter_by(id=club_id).first()
    titulaires = get_titulaires_dict(Titulaire.query.filter_by(club_id = club.id).all())
    clubs = Club.query.all()
    sexes = Sexe.query.all()

    return render_template("titulaires.html", title=club.ville[0].upper() + club.ville[1:], titulaires=titulaires, clubs=clubs, sexes=sexes)

@views.route("/titulaires/", methods=['POST'])
@login_required
def add_titulaire(club_id=None) :
    """Fonction liée au end-point "/titulaires/ en method POST"
    Args:
        le nom de la template à utiliser pour le rendu (en fonction de là où le titulaire est créé)
    Fonction ajoutant un titulaire

    Returns:
        Redirect: redirection vers views.titulaire

    """
    template_to_return = ""
    clubs = Club.query.all()
    sexes = Sexe.query.all()
    new_titulaires = {}
    if club_id is None:
        new_titulaires = get_titulaires_dict(Titulaire.query.all())
        template_to_return = render_template("titulaires.html", title="tous", titulaires=new_titulaires, clubs=clubs, sexes=sexes, name=True)
    else:
        club = Club.query.filter_by(id=club_id).first()
        new_titulaires = get_titulaires_dict(Titulaire.query.filter_by(club_id=club_id).all())
        template_to_return = render_template("titulaires.html", title=club.ville[0].upper() + club.ville[1:], titulaires=new_titulaires, clubs=clubs, sexes=sexes)

    nom = request.form.get('name').upper() # On met le nom de famille en majuscule
    if nom is None or nom == "":
        return template_to_return
    # On met le prenom en minscule sauf la premiere lettre
    prenom = request.form.get('surname').lower()
    prenom = prenom[0].upper() + prenom[1:]
    if prenom is None or prenom == "" :
        return template_to_return
    date_naissance = request.form.get('birthDate')
    if date_naissance is None or date_naissance == "" or len(date_naissance.split("-")) != 3 or len(date_naissance.split("-")[2]) <= 0 or len(date_naissance.split("-")[2]) > 2 or len(date_naissance.split("-")[1]) <= 0 or len(date_naissance.split("-")[1]) > 2 or len(date_naissance.split("-")[0]) < 4:
        return template_to_return
    club_id_form = request.form.get('clubId')
    if club_id_form is None or club_id_form == "" or Club.query.filter_by(id=club_id_form).first() is None :
        return template_to_return    
    plaque = request.form.get('plaqueNb')
    #si la plaque contient la lettre on l'ajoute
    if plaque[0].isnumeric():
        numero = plaque
        plaque = (Club.query.filter_by(id=club_id_form).first()).initiales+numero
    #sinon
    else:
        plaque = plaque[0].upper() + plaque[1:]
        numero = plaque[1:] # on extrait le numero de la plaque
    # on verifie ensuite que la plaque n'existe pas déjà
    titulaires = Titulaire.query.all()
    PlaqueExist = 0
    for t in titulaires:
        if (t.numero_plaque == plaque) :
            PlaqueExist += 1

    if plaque is None or PlaqueExist >= 1 or plaque == "" or not check_titulaire_number( Club.query.filter_by(id=club_id_form).first().titulaires, plaque) is not None or int(numero)>=1000 or len(plaque)>4:
        return template_to_return
    sexe_id = request.form.get('sexeId')
    if sexe_id is None or sexe_id == "" or Sexe.query.filter_by(id=sexe_id).first() is None :
        return template_to_return
    date_naissance = datetime.datetime.strptime(date_naissance, '%Y-%m-%d')
    if len(plaque) == 2 :
        plaque = plaque[0] + "0" + plaque[1]
    new_titulaire = Titulaire(nom=nom.upper(), prenom=prenom, date_naissance=date_naissance, club_id=club_id_form, numero_plaque=plaque, sexe_id=sexe_id)
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

        uploaded_file = request.files['xls']
        if uploaded_file.filename != '':
            uploaded_file.save(uploaded_file.filename)

        files = xlrd.open_workbook(uploaded_file.filename)

        file = files.sheet_by_index(0)

        indiceFirstRow = file.nrows-1
        indiceFirstColumn = file.ncols-1

        """Pour avoir la première ligne"""
        while (str(file.cell_value(indiceFirstRow, indiceFirstColumn)).upper() != "Sexe".upper() and indiceFirstRow != 0):
            indiceFirstRow -= 1

        """pour avoir la première colonne"""
        while(file.cell_value(indiceFirstRow,indiceFirstColumn) != '' and indiceFirstColumn != 0):
            indiceFirstColumn -= 1

        """se redécaler d'une colonne vers la droite"""
        if(file.cell_value(indiceFirstRow,indiceFirstColumn) == ''):
            indiceFirstColumn += 1

        """se redécaler d'une cases vers le bas (pour éviter d'être sur les titres)"""
        indiceFirstRow += 1

        np_nom = []
        np_dateNaissance = []
        np_club = []
        np_plaque = []
        np_sexe = []

        for i in range(indiceFirstRow, file.nrows):
            if(file.cell_value(i, 0+indiceFirstColumn) != ''):
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

        for row in range(0, len(np_nom)):
            nom = np_nom[row]

            #Dissociation du nom et prenom, dans le excel ils sont dans la même case
            #Exemple Martin-Denis François Baptiste
            #nom = Martin-Denis
            #prenom = François Baptiste
            nom_prenom = nom.split(' ',1)
            nom = nom_prenom[0]
            prenom = nom_prenom[1]

            date_naissance = np_dateNaissance[row]
            club_nom = np_club[row]
            numero_plaque = np_plaque[row]

            d0 = datetime.date(1900, 1, 1)
            delta = datetime.timedelta(days=(date_naissance - 2))
            date_naissance = d0 + delta

            club_existe = False

            clubs = Club.query.all()

            # Vérification de si le club existe dans la bd
            for club in clubs:
                if club.ville.upper() == club_nom.upper(): #s'il existe donc on récupère son numéro
                    club_existe = True
                    club_id = club.id
                    break

                #s'il n'existe pas alors on le crée
            if club_existe == False:
                new_club = Club(ville=club_nom.lower(), initiales=numero_plaque[0].upper())
                db.session.add(new_club)
                db.session.commit()

            # si le titulaire est un homme sexe_id = 1, femme sexe_id = 2
            if np_sexe[row] == "H":
                sexe_id = 1
            else:
                sexe_id = 2

            # Regarder si un titulaire existe déjà dans la base de données on ne l'ajoute pas
            titulaire_existe = False

            titulaires = Titulaire.query.all()

            i_titu = 0

            # vérification de si un titulaire existe déjà
            while titulaire_existe == False and i_titu != len(titulaires):
                if titulaires[i_titu].numero_plaque == numero_plaque:  # s'il existe donc on récupère son numéro
                    titulaire_existe = True

                i_titu += 1

                # s'il n'existe pas alors on le crée
            if titulaire_existe == False:
                new_titulaire = Titulaire(nom=nom.upper(), prenom=prenom, date_naissance=date_naissance,
                                          club_id=club_id,
                                          numero_plaque=numero_plaque, sexe_id=sexe_id)
                db.session.add(new_titulaire)
                db.session.commit()

        os.remove(uploaded_file.filename)

    return redirect(url_for('views.titulaires'))

"""
/!\ TODO : l'id doit etre passé en parametre de l'url et de la fonction normalement
et la route doit etre : /titulaires/<titulaire_id> et la fonction : edit_titulaire(titulaire_id):
mais j'ai un pb dans l'html je n'arrive pas a passer le bon id en parametre
"""
@views.route("/titulaires/edit", methods=['POST'])
@login_required
def edit_titulaire() :
    """Fonction liée au end-point "/titulaires/edit en method POST"

    Fonction modifiant un titulaire

    Returns:
        Redirect: redirection vers views.titulaire

    """
    titulaire_id = request.form.get('id')

    if titulaire_id is not None:
        titulaire = Titulaire.query.filter_by(id=titulaire_id).first()

        if titulaire is not None:
            nom = request.form.get('name').upper()
            prenom = request.form.get('surname')
            prenom = prenom[0].upper() + prenom[1:].lower()
            sexe_id = request.form.get('sexeId')

            club_name = request.form.get('clubId')
            clubs = Club.query.all()
            for i in range(len(clubs)):
                if (club_name.lower() == clubs[i].ville.lower()):
                    club_id = clubs[i].id

            plaque = request.form.get('plaqueNb')
            if len(plaque) > 4:
                return jsonify({'status': 'error'})  # la plaque d'un titulaire ne doit pas depasse 4 caracteres

            # on verifie si l'utilisateur a entré la lettre avec le numero de la plaque
            if (plaque[0].isnumeric()):
                if len(plaque) > 3:
                    return jsonify({'status': 'error'})  # le numero (sans compter la lettre) ne doit pas depasser 3 caracteres
                club = Club.query.filter_by(id=club_id).first()
                plaque = club.initiales + plaque


            # si la plaque ne fait que 2 caractere, cela veut dire que le numero est < 10 donc on rajoute un 0 devant pour que ce soit plus joli
            if (len( plaque) == 2):
                plaque = plaque[0].upper()+"0" + plaque[1]
            else:
                plaque = plaque[0].upper() + plaque[1:]


            # on verifie ensuite que la plaque n'existe pas déjà
            titulaires = Titulaire.query.all()
            PlaqueExist = 0
            for t in titulaires:
                if (t.numero_plaque == plaque) and (int(t.id) != int(titulaire_id)):
                    PlaqueExist += 1

            if (PlaqueExist >= 1):
                return jsonify({'status': 'errorr'})  #  la plaque du titulaire existe deja, 2 titulaires ne peuvent pas avoir la meme plaque

            str_date = request.form.get('birthDate').split('-')
            date = datetime.datetime(int(str_date[0]), int(str_date[1]),int(str_date[2]))
            titulaire.date_naissance = date

            #titulaire.club_id = club_id

            titulaire.nom = nom
            titulaire.prenom = prenom
            titulaire.sexe_id = sexe_id
            titulaire.numero_plaque = plaque
            titulaire.club_id = club_id
            db.session.commit()

            # Rechargement des donnees
            return redirect(url_for('views.titulaires'))

        else:
            return jsonify({'status': 'error'}) # le titulaire n\'a pas été trouvé dans la base de données'})
    return jsonify({'status': 'error'}) # pas d'id trouve dans les parametres

@views.route("/titulaires/delete_all", methods=['POST'])
@login_required
def delete_all_titulaire():
    """Fonction liée au end-point "/titulaires/delete_all en method POST"

    Fonction supprimant un titulaire, à utiliser en tant qu'API en JS

    Returns:
        Json: résultat de la suppression

    """

    club_name = request.form.get('club_name')

    # si le nom de club est titulaires cela veut dire que on veut supprimer tous les titulaires
    if club_name == 'titulaires':
        titulaires_to_delete = Titulaire.query.all()
        for t in titulaires_to_delete:
            db.session.delete(t)
            db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Les titulaires ont été supprimé avec succès'})

    else:
        club = Club.query.filter_by(ville=club_name.lower()).first()
        club_id = club.id
        titulaires_to_delete = Titulaire.query.filter_by(club_id=club_id)
        if titulaires_to_delete is not None:
            for t in titulaires_to_delete:
                db.session.delete(t)
                db.session.commit()
            return jsonify(
                {'status': 'ok', 'message': 'Les titulaires du club ' + club_name + ' ont été supprimé avec succès'})

    return jsonify({'status': 'error', 'message': 'Erreur serveur'})
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

            return jsonify({'status': 'ok',
                            'message': 'Le titulaire a été supprimé avec succès'})
        else :
            return jsonify({'status': 'error',
                            'message': 'Titulaire inexistant dans la base de données'})
        
@views.route("/championnats/delete", methods=['POST'])
@login_required
def delete_championnat() :
    """Fonction liée au end-point "/championnats/delete en method POST"

    Fonction supprimant un championnat, à utiliser en tant qu'API en JS

    Returns:
        Json: résultat de la suppression

    """

    championnat_id = request.form.get('championnat_id')
    if championnat_id is not None :
        championnat = Championnat.query.filter_by(id=championnat_id).first()
        if championnat is not None :
            db.session.delete(championnat)
            db.session.commit()

            return jsonify({'status': 'ok'})
        else :
            return jsonify({'status': 'error'})
        
@views.route("/etapes/delete", methods=['POST'])
@login_required
def delete_etape() :
    """Fonction liée au end-point "/etapes/delete en method POST"

    Fonction supprimant une etape, à utiliser en tant qu'API en JS

    Returns:
        Json: résultat de la suppression

    """

    etape_id = request.form.get('etape_id')
    if etape_id is not None :
        etape = Etape.query.filter_by(id=etape_id).first()
        if etape is not None :
            db.session.delete(etape)
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


@views.route("/clubs/<club_id>", methods=['POST'])
@login_required
def edit_club(club_id):
    """Fonction liée au end-point "/clubs/<club_id> en method POST"

    Fonction modifiant un club.

    Returns:
        Redirect : redirection vers views.club

    """
    new_club_name = request.form.get('club_name')
    new_club_init = request.form.get('club_init')
    new_club_init = new_club_init.upper()

    if club_id is not None :
        club = Club.query.filter_by(id=club_id).first()
        if club is not None :
            club.ville = new_club_name

            if (club.initiales != new_club_init):

                titulaires_from_club = Titulaire.query.all()
                old_club_init = club.initiales
                club.initiales = new_club_init

                for i in range( len(titulaires_from_club)):
                    if titulaires_from_club[i].numero_plaque[0] == old_club_init:
                        titulaires_from_club[i].numero_plaque = new_club_init + titulaires_from_club[i].numero_plaque[1:]

            db.session.commit()

    # Rechargement des donnees
    return redirect(url_for('views.clubs'))

@views.route("/clubs/delete", methods=['POST'])
@login_required
def delete_club():
    """Fonction liée au end-point "/clubs/delete en method POST"

    Fonction supprimant une etape, à utiliser en tant qu'API en JS

    Returns:
        Json: résultat de la suppression

    """

    club_id = request.form.get('club_id')
    if club_id is not None :
        club = Club.query.filter_by(id=club_id).first()
        if club is not None:
            db.session.delete(club)
            db.session.commit()

            return jsonify({'status': 'ok',
                            'message': 'Le club a été supprimé avec succès'})
        else :
            return jsonify({'status': 'error',
                            'message': 'Club non trouvé'})
    return jsonify({'status': 'error',
                    'message': 'Id non trouvé'})

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

        cmpt_participant = 0
        for new_participant_id in request.form :
            if request.form.get(new_participant_id) == "on" :
                titulaire = Titulaire.query.filter_by(id=new_participant_id).first()
                if titulaire is not None :
                    cmpt_participant += 1

        if cmpt_participant <= 40:
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

        championnat = Championnat.query.filter_by(id=championnat_id).first()
        championnat_type_id = championnat.championnat_type_id
        
        if championnat_type_id == 1:

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


                    elif nb_participants >= 9 and nb_participants <= 40:
                        race_names = ['A', 'B', 'C', 'D', 'E', 'F']

                        if nb_participants >= 9 and  nb_participants <= 16:
                            nb_races = 2
                        elif nb_participants >= 17 and nb_participants <= 19:
                            nb_races = 3
                        elif nb_participants >= 20 and nb_participants <= 32:
                            nb_races = 4
                        elif nb_participants >= 33:
                            nb_races = 5

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
                                new_participant_race = Participant_race(titulaire_id=participants_etape[index_participant_etape].titulaire_id, race_id=race.id, couloir_id=couloirs[index_participant_race].id)
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

                        if nb_participants >= 9 and nb_participants <= 16:
                             for index_race in range(2) :
                                new_race = Race(name=race_names[index_race], etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_final.id, categorie_id=new_categorie.id)
                                db.session.add(new_race)

                        if nb_participants >= 17 and nb_participants <= 24:
                            for index_race in range(3) :
                                new_race = Race(name=race_names[index_race], etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_final.id, categorie_id=new_categorie.id)
                                db.session.add(new_race)

                        if nb_participants >= 25 and nb_participants <= 32:
                            for index_race in range(4) :
                                new_race = Race(name=race_names[index_race], etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_final.id, categorie_id=new_categorie.id)
                                db.session.add(new_race)

                        if nb_participants >= 33 and nb_participants <= 36:
                            for index_race in range(5) :
                                new_race = Race(name=race_names[index_race], etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_final.id, categorie_id=new_categorie.id)
                                db.session.add(new_race)

                        if nb_participants >= 37 and nb_participants <= 40:
                            for index_race in range(6) :
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
                            for index_race in range(4):
                                new_race = Race(name=race_names[index_race], etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_quart.id, categorie_id=new_categorie.id)
                                db.session.add(new_race)
                            db.session.commit()
        #championnat departemental
        elif championnat_type_id == 2:
            
            
            #creation de l'architecture des courses + phases seches
            phase_seche = Race_type.query.filter_by(type="Seche").first()
            
            participants_total = Participant_etape.query.filter_by(etape_id=etape_id).all()
            print(participants_total)
            for categorie_type in Categorie_type.query.all() :
                participants_etape = Participant_etape.query.filter_by(etape_id=etape_id, categorie_type_id=categorie_type.id).all()
                
                if participants_etape is not None :
                    nb_participants = len(participants_etape)
                    couloirs = Couloir.query.all()
                    
                    if nb_participants > 0 :
                        new_categorie = Categorie(etape_id=etape_id, categorie_type_id=categorie_type.id)
                        db.session.add(new_categorie)
                        db.session.commit()

                        for participant_etape in participants_etape :
                            new_participant_categorie = Participant_categorie(titulaire_id=participant_etape.titulaire_id, categorie_id=new_categorie.id)
                            db.session.add(new_participant_categorie)
                        db.session.commit()

                        #creation de 3 races seches
                        for race_index in range (1, 4):
                            race_i = Race(name=race_index, etape_id=etape_id, categorie_type_id=categorie_type.id, race_type_id=phase_seche.id, categorie_id=new_categorie.id)
                            db.session.add(race_i)
                            db.session.commit()
                            
                            for index_participant, participant_etape in enumerate(participants_etape) :
                                new_participant_race_i = Participant_race(titulaire_id=participant_etape.titulaire_id, race_id=race_i.id, couloir_id=couloirs[0].id) #couloir_id par important
                                db.session.add(new_participant_race_i)
                                
                            db.session.commit()
                            
                            pioche = [i for i in range (0, nb_participants)]
                            print("pioche = ", pioche)
                            
                            
                            if nb_participants % 8 == 0: #des manches de 8, pas de soucis
                                for i in range(round(nb_participants / 8)):
                                    tirage = random.sample(pioche, 8)
                                    
                                    for t in tirage:
                                        pioche.remove(t)
                                    
                                    new_manche = Manche(race_id=race_i.id)
                                    db.session.add(new_manche)
                                    db.session.commit()
                                    
                                    print("tirage = ", tirage)
                                    index = 1
                                    for index_participant in tirage:
                                        print("pilote : ", participants_etape[index_participant], " part couloir ", index)
                                        
                                        participant_race = participants_etape[index_participant]
                                        new_participant_manche = Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=new_manche.id, place_depart=index)
                                        
                                        db.session.add(new_participant_manche)
                                        index+=1
                                    db.session.commit()
                                    
                                    
                            else: #pas divisible par 8, donc on cherche la meilleure repartition de manches
                                n = nb_participants
                                k = round(int(n/8) + 1)
                                z = n/k #le nombre d'éléments par sous ensemble en moyenne
                                k1 = round((z - int(z))*k)# sous ensembles a E(z)+1 éléments
                                k2 = round(k - k1) # sous ensembles a E(z) elements
                                
                                #remplissage des k1 sous ensembles
                                z1 = round(int(z) + 1)
                                for i in range(k1):
                                    tirage = random.sample(pioche, z1)
                                    
                                    for t in tirage:
                                        pioche.remove(t)
                                    
                                    new_manche = Manche(race_id=race_i.id)
                                    db.session.add(new_manche)
                                    db.session.commit()
                                    
                                    #print("tirage = ", tirage)
                                    index = 1
                                    for index_participant in tirage:
                                        #print("pilote : ", participants_etape[index_participant], " part couloir ", index)
                                        
                                        participant_race = participants_etape[index_participant]
                                        new_participant_manche = Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=new_manche.id, place_depart=index)
                                        
                                        db.session.add(new_participant_manche)
                                        index+=1
                                    db.session.commit()
                                
                                #remplissage des k2 sous ensembles
                                z2 = round(int(z))
                                for i in range(k2):
                                    tirage = random.sample(pioche, z2)
                                    
                                    for t in tirage:
                                        pioche.remove(t)
                                    
                                    new_manche = Manche(race_id=race_i.id)
                                    db.session.add(new_manche)
                                    db.session.commit()
                                    
                                    #print("tirage = ", tirage)
                                    index = 1
                                    for index_participant in tirage:
                                        #print("pilote : ", participants_etape[index_participant], " part couloir ", index)
                                        
                                        participant_race = participants_etape[index_participant]
                                        new_participant_manche = Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=new_manche.id, place_depart=index)
                                        
                                        db.session.add(new_participant_manche)
                                        index+=1
                                    db.session.commit()
                                
                                
                            """
                            while pioche != []:
                                if nb_participants % 8 == 0:
                                    
                                    tirage = random.sample(pioche, 8)
                                    
                                    for t in tirage:
                                        pioche.remove(t)
                                    
                                    new_manche = Manche(race_id=race_i.id)
                                    db.session.add(new_manche)
                                    db.session.commit()
                                    
                                    print("tirage = ", tirage)
                                    index = 1
                                    for index_participant in tirage:
                                        print("pilote : ", participants_etape[index_participant], " part couloir ", index)
                                        
                                        participant_race = participants_etape[index_participant]
                                        new_participant_manche = Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=new_manche.id, place_depart=index)
                                        
                                        db.session.add(new_participant_manche)
                                        index+=1
                                    db.session.commit()
                                elif nb_participants % 7 == 0:
                                    
                                    tirage = random.sample(pioche, 7)
                                    
                                    for t in tirage:
                                        pioche.remove(t)
                                    
                                    new_manche = Manche(race_id=race_i.id)
                                    db.session.add(new_manche)
                                    db.session.commit()
                                    
                                    print("tirage = ", tirage)
                                    index = 1
                                    for index_participant in tirage:
                                        print("pilote : ", participants_etape[index_participant], " part couloir ", index)
                                        
                                        participant_race = participants_etape[index_participant]
                                        new_participant_manche = Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=new_manche.id, place_depart=index)
                                        
                                        db.session.add(new_participant_manche)
                                        index+=1
                                    db.session.commit()
                                elif nb_participants % 6 == 0:
                                    
                                    tirage = random.sample(pioche, 6)
                                    
                                    for t in tirage:
                                        pioche.remove(t)
                                    
                                    new_manche = Manche(race_id=race_i.id)
                                    db.session.add(new_manche)
                                    db.session.commit()
                                    
                                    print("tirage = ", tirage)
                                    index = 1
                                    for index_participant in tirage:
                                        print("pilote : ", participants_etape[index_participant], " part couloir ", index)
                                        
                                        participant_race = participants_etape[index_participant]
                                        new_participant_manche = Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=new_manche.id, place_depart=index)
                                        
                                        db.session.add(new_participant_manche)
                                        index+=1
                                    db.session.commit()
                                
                                elif nb_participants % 5 == 0:
                                    
                                    tirage = random.sample(pioche, 5)
                                    
                                    for t in tirage:
                                        pioche.remove(t)
                                    
                                    new_manche = Manche(race_id=race_i.id)
                                    db.session.add(new_manche)
                                    db.session.commit()
                                    
                                    print("tirage = ", tirage)
                                    index = 1
                                    for index_participant in tirage:
                                        print("pilote : ", participants_etape[index_participant], " part couloir ", index)
                                        
                                        participant_race = participants_etape[index_participant]
                                        new_participant_manche = Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=new_manche.id, place_depart=index)
                                        
                                        db.session.add(new_participant_manche)
                                        index+=1
                                    db.session.commit()
                                
                                else:
                                    min_pioche = min(len(pioche), 6)
                                    print("tirage de ", min_pioche, " elements dans pioche")
                                    tirage = random.sample(pioche, min_pioche)
                                    
                                    for t in tirage:
                                        pioche.remove(t)
                                    
                                    new_manche = Manche(race_id=race_i.id)
                                    db.session.add(new_manche)
                                    db.session.commit()
                                    
                                    print("tirage = ", tirage)
                                    index = 1
                                    for index_participant in tirage:
                                        print("pilote : ", participants_etape[index_participant], " part couloir ", index)
                                        
                                        participant_race = participants_etape[index_participant]
                                        new_participant_manche = Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=new_manche.id, place_depart=index)
                                        
                                        db.session.add(new_participant_manche)
                                        index+=1
                                    db.session.commit()
                                """


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
    categorie = Categorie.query.filter_by(categorie_type_id = categorie_type.id,etape_id=etape_id).first()
    club = etape.club

    return render_template("races.html", championnat_id=championnat_id, races=races, categorie=categorie,categorie_type=categorie_type, etape=etape, club=club)

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
            if not categorie.quart_finie and not categorie.quart_genere:

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
                    db.session.add(Participant_race(titulaire_id=pool_race_a.participations[0].titulaire_id, race_id=quart_race_a.id, couloir_id=couloirs[0].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_b.participations[0].titulaire_id, race_id=quart_race_a.id, couloir_id=couloirs[1].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_c.participations[1].titulaire_id, race_id=quart_race_a.id, couloir_id=couloirs[2].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_b.participations[2].titulaire_id, race_id=quart_race_a.id, couloir_id=couloirs[3].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_c.participations[3].titulaire_id, race_id=quart_race_a.id, couloir_id=couloirs[4].id))

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=pool_race_c.participations[0].titulaire_id, race_id=quart_race_b.id, couloir_id=couloirs[0].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_a.participations[1].titulaire_id, race_id=quart_race_b.id, couloir_id=couloirs[1].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_b.participations[1].titulaire_id, race_id=quart_race_b.id, couloir_id=couloirs[2].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_c.participations[2].titulaire_id, race_id=quart_race_b.id, couloir_id=couloirs[3].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_b.participations[3].titulaire_id, race_id=quart_race_b.id, couloir_id=couloirs[4].id))

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=pool_race_d.participations[0].titulaire_id, race_id=quart_race_c.id, couloir_id=couloirs[0].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_e.participations[1].titulaire_id, race_id=quart_race_c.id, couloir_id=couloirs[1].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_a.participations[2].titulaire_id, race_id=quart_race_c.id, couloir_id=couloirs[2].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_d.participations[2].titulaire_id, race_id=quart_race_c.id, couloir_id=couloirs[3].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_e.participations[3].titulaire_id, race_id=quart_race_c.id, couloir_id=couloirs[4].id))

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=pool_race_e.participations[0].titulaire_id, race_id=quart_race_d.id, couloir_id=couloirs[0].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_d.participations[1].titulaire_id, race_id=quart_race_d.id, couloir_id=couloirs[1].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_e.participations[2].titulaire_id, race_id=quart_race_d.id, couloir_id=couloirs[2].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_a.participations[3].titulaire_id, race_id=quart_race_d.id, couloir_id=couloirs[3].id))
                    db.session.add(Participant_race(titulaire_id=pool_race_d.participations[3].titulaire_id, race_id=quart_race_d.id, couloir_id=couloirs[4].id))

                    db.session.commit()

                    for participant in quart_race_a.participations :
                        couloir = Couloir.query.filter_by(id=participant.couloir_id).first()
                        db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=quart_race_a.manches[0].id, place_depart=couloir.couloir_1))
                    for participant in quart_race_b.participations :
                        couloir = Couloir.query.filter_by(id=participant.couloir_id).first()
                        db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=quart_race_b.manches[0].id, place_depart=couloir.couloir_1))
                    for participant in quart_race_c.participations :
                        couloir = Couloir.query.filter_by(id=participant.couloir_id).first()
                        db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=quart_race_c.manches[0].id, place_depart=couloir.couloir_1))
                    for participant in quart_race_d.participations :
                        couloir = Couloir.query.filter_by(id=participant.couloir_id).first()
                        db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=quart_race_d.manches[0].id, place_depart=couloir.couloir_1))

                    db.session.commit()
                categorie.quart_genere = True
                db.session.commit()

            elif not categorie.demi_finie and not categorie.demi_genere:

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
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[0].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[1].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[1].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[2].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[3].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[4].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[3].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[5].id))

                        random.shuffle(couloirs)
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[0].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[0].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[1].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[2].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[2].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[3].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[4].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[5].id))

                        db.session.commit()

                        for participant in demi_race_a.participations :
                            couloir = Couloir.query.filter_by(id=participant.couloir_id).first()
                            db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=demi_race_a.manches[0].id, place_depart=couloir.couloir_1))
                        for participant in demi_race_b.participations :
                            couloir = Couloir.query.filter_by(id=participant.couloir_id).first()
                            db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=demi_race_b.manches[0].id, place_depart=couloir.couloir_1))

                        db.session.commit()

                    elif nb_participants_categorie >= 20 and nb_participants_categorie <= 32 :

                        pool_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="A").first()
                        pool_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="B").first()
                        pool_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="C").first()
                        pool_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="D").first()

                        demi_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="A").first()
                        demi_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="B").first()

                        db.session.add(Manche(race_id=demi_race_a.id))
                        db.session.add(Manche(race_id=demi_race_b.id))

                        couloirs = Couloir.query.all()

                        random.shuffle(couloirs)
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[0].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[1].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[1].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[2].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[1].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[3].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[4].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[5].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[3].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[6].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[3].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[7].id))

                        random.shuffle(couloirs)
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[0].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[0].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[0].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[1].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[2].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[3].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_b.participations[2].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[4].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_d.participations[2].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[5].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_a.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[6].id))
                        db.session.add(Participant_race(titulaire_id=pool_race_c.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[7].id))

                        db.session.commit()

                        for participant in demi_race_a.participations :
                            couloir = Couloir.query.filter_by(id=participant.couloir_id).first()
                            db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=demi_race_a.manches[0].id, place_depart=couloir.couloir_1))
                        for participant in demi_race_b.participations :
                            couloir = Couloir.query.filter_by(id=participant.couloir_id).first()
                            db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=demi_race_b.manches[0].id, place_depart=couloir.couloir_1))

                        db.session.commit()

                    elif nb_participants_categorie >= 33 :

                        pool_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="A").first()
                        pool_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="B").first()
                        pool_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="C").first()
                        pool_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="D").first()
                        pool_race_e = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="E").first()

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
                        db.session.add(Participant_race(titulaire_id=quart_race_a.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[0].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_c.participations[0].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[1].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_b.participations[1].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[2].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_d.participations[1].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[3].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_a.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[4].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_c.participations[2].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[5].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_b.participations[3].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[6].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_d.participations[3].titulaire_id, race_id=demi_race_a.id, couloir_id=couloirs[7].id))

                        random.shuffle(couloirs)
                        db.session.add(Participant_race(titulaire_id=quart_race_b.participations[0].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[0].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_d.participations[0].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[1].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_a.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[2].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_c.participations[1].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[3].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_b.participations[2].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[4].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_d.participations[2].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[5].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_a.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[6].id))
                        db.session.add(Participant_race(titulaire_id=quart_race_c.participations[3].titulaire_id, race_id=demi_race_b.id, couloir_id=couloirs[7].id))

                        db.session.commit()

                        for participant in demi_race_a.participations :
                            couloir = Couloir.query.filter_by(id=participant.couloir_id).first()
                            db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=demi_race_a.manches[0].id, place_depart=couloir.couloir_1))
                        for participant in demi_race_b.participations :
                            couloir = Couloir.query.filter_by(id=participant.couloir_id).first()
                            db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=demi_race_b.manches[0].id, place_depart=couloir.couloir_1))

                        db.session.commit()
                categorie.demi_genere = True
                db.session.commit()

            elif not categorie.finale_finie and not categorie.finale_genere:

                if nb_participants_categorie >= 9 and nb_participants_categorie <= 16 :

                    if nb_participants_categorie == 9 :
                        limit = 3
                    else :
                        limit = 4

                    pool_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="A").first()
                    pool_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="B").first()
                    pool_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="C").first()
                    pool_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="D").first()
                    pool_race_e = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="E").first()

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
                    finale_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="C").first()

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


                    for participant in finale_race_a.participations :
                        db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=finale_race_a.manches[0].id, place_depart=participant.couloir.couloir_1))
                    for participant in finale_race_b.participations :
                        db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=finale_race_b.manches[0].id, place_depart=participant.couloir.couloir_1))

                    pool_races = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id).all()
                    couloirs_c = Couloir.query.all()
                    random.shuffle(couloirs_c)
                    index_couloir_c = 0



                    if nb_participants_categorie >= 25 :
                        finale_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="D").first()
                        for i in range(2) :
                            db.session.add(Manche(race_id=finale_race_d.id))
                        couloirs_d = Couloir.query.all()
                        random.shuffle(couloirs_d)

                    index_couloir_d = 0

                    participants_a = Participant_race.query.filter_by(race_id=finale_race_a.id).all()
                    participants_b = Participant_race.query.filter_by(race_id=finale_race_b.id).all()

                    titulaires_a = []
                    titulaires_b = []
                    titulaires_c = []

                    for participant_a in participants_a:
                        titulaires_a.append(participant_a.titulaire_id)

                    for participant_b in participants_b:
                        titulaires_b.append(participant_b.titulaire_id)

                    limit1 = 0
                    limit2 = 0
                    if nb_participants_categorie == 25 or nb_participants_categorie == 26:
                        limit1 = 5
                    if nb_participants_categorie == 27 or nb_participants_categorie == 28:
                        limit1 = 6
                    if nb_participants_categorie == 29 or nb_participants_categorie == 30:
                        limit1 = 7
                    if nb_participants_categorie == 31 or nb_participants_categorie == 32:
                        limit1 = 8

                    if nb_participants_categorie == 25:
                        limit2 = 4
                    if nb_participants_categorie == 26 or nb_participants_categorie == 27:
                        limit2 = 5
                    if nb_participants_categorie == 28 or nb_participants_categorie == 29:
                        limit2 = 6
                    if nb_participants_categorie == 30 or nb_participants_categorie == 31:
                        limit2 = 7
                    if nb_participants_categorie == 32:
                        limit2 = 8

                    for race in pool_races :
                        for participant in race.participations:
                            if nb_participants_categorie <= 24 :
                                if participant.titulaire_id not in titulaires_a and participant.titulaire_id not in titulaires_b:
                                    db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_c.id, couloir_id=couloirs_c[index_couloir_c].id))
                                    index_couloir_c += 1

                    cmpt1 = 0
                    cmpt2 = 0
                    for race in pool_races :
                        for participant in race.participations:
                            if nb_participants_categorie > 24 :
                                if cmpt1 < limit1 and index_couloir_c < 8:
                                    if participant.titulaire_id not in titulaires_a and participant.titulaire_id not in titulaires_b:
                                        db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_c.id, couloir_id=couloirs_c[index_couloir_c].id))
                                        index_couloir_c += 1
                                        cmpt1 += 1
                            db.session.commit()

                    participants_c= Participant_race.query.filter_by(race_id=finale_race_c.id).all()
                    for participant_c in participants_c:
                        titulaires_c.append(participant_c.titulaire_id)

                    if nb_participants_categorie >= 25:
                        for race in pool_races :
                            for participant in race.participations:
                                if cmpt2 < limit2 and index_couloir_d < 8:
                                    if participant.titulaire_id not in titulaires_a and participant.titulaire_id not in titulaires_b and participant.titulaire_id not in titulaires_c:
                                        db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_d.id, couloir_id=couloirs_d[index_couloir_d].id))
                                        finale_race = finale_race_d
                                        index_couloir_d += 1
                                        add_race_c = True
                                        cmpt2 += 1
                                db.session.commit()

                    for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race_c.id).all()) :
                        for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                            if index_manche == 0 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                            elif index_manche == 1 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))

                    if nb_participants_categorie >= 25 :
                        for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race_d.id).all()) :
                            for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                                if index_manche == 0 :
                                    db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                                elif index_manche == 1 :
                                    db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))
                        db.session.commit()

                elif nb_participants_categorie >= 33 :

                    list_race = []
                    pool_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="A").first()
                    pool_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="B").first()
                    pool_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="C").first()
                    pool_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="D").first()
                    pool_race_e = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_pool.id, name="E").first()

                    demi_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="A").first()
                    demi_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_demi.id, name="B").first()

                    quart_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="A").first()
                    quart_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="B").first()
                    quart_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="C").first()
                    quart_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="D").first()

                    finale_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="A").first()
                    finale_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="B").first()
                    finale_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="C").first()
                    finale_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="D").first()
                    finale_race_e = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="E").first()
                    finale_race_f = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="F").first()


                    db.session.add(Manche(race_id=finale_race_a.id))
                    db.session.add(Manche(race_id=finale_race_b.id))

                    list_race.append(pool_race_a)
                    list_race.append(pool_race_b)
                    list_race.append(pool_race_c)
                    list_race.append(pool_race_d)
                    list_race.append(pool_race_e)

                    couloirs = Couloir.query.all()

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[0].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[0].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[3].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[3].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[1].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[1].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[2].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[4].id))

                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[0].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[2].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[1].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[5].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[3].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[6].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[2].titulaire_id, race_id=finale_race_a.id, couloir_id=couloirs[7].id))

                    random.shuffle(couloirs)
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[4].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[0].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[5].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[3].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[6].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[1].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_a.participations[7].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[4].id))

                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[4].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[2].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[5].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[5].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[6].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[6].id))
                    db.session.add(Participant_race(titulaire_id=demi_race_b.participations[7].titulaire_id, race_id=finale_race_b.id, couloir_id=couloirs[7].id))

                    db.session.commit()

                    for participant in finale_race_a.participations :
                        db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=finale_race_a.manches[0].id, place_depart=participant.couloir.couloir_1))
                    for participant in finale_race_b.participations :
                        db.session.add(Participant_manche(titulaire_id=participant.titulaire_id, manche_id=finale_race_b.manches[0].id, place_depart=participant.couloir.couloir_1))

                    db.session.commit()

                    finale_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="C").first()
                    for i in range(2) :
                        db.session.add(Manche(race_id=finale_race_c.id))
                    db.session.commit()

                    random.shuffle(couloirs)

                    titulaires_a = []
                    participants_a = Participant_race.query.filter_by(race_id=finale_race_a.id).all()
                    titulaires_b = []
                    participants_b = Participant_race.query.filter_by(race_id=finale_race_b.id).all()

                    for participant_a in participants_a:
                        titulaires_a.append(participant_a.titulaire_id)
                    for participant_b in participants_b:
                        titulaires_b.append(participant_b.titulaire_id)

                    cmptc = 0
                    cmptd = 0
                    cmpte = 0
                    cmptf = 0

                    limitc = 0
                    limitd = 0
                    limite = 0
                    limitf = 0

                    if nb_participants_categorie >= 33 or nb_participants_categorie <= 40:
                        limitc = 4

                    if nb_participants_categorie == 33 or nb_participants_categorie == 34:
                        limitd = 7
                    if nb_participants_categorie == 35 or nb_participants_categorie == 36:
                        limitd = 8
                    if nb_participants_categorie == 37 or nb_participants_categorie == 38:
                        limitd = 6
                    if nb_participants_categorie == 39 or nb_participants_categorie == 40:
                        limitd = 7

                    if nb_participants_categorie == 33:
                        limite = 6
                    if nb_participants_categorie == 34 or nb_participants_categorie == 35:
                        limite = 7
                    if nb_participants_categorie == 36 :
                        limite = 8
                    if nb_participants_categorie == 37 or nb_participants_categorie == 38 or nb_participants_categorie == 39:
                        limite = 6
                    if nb_participants_categorie == 40:
                        limite = 7

                    if nb_participants_categorie == 37:
                        limitf = 5
                    if nb_participants_categorie >= 38 and nb_participants_categorie <= 40:
                        limitf = 6

                    couloirs_c = Couloir.query.all()
                    random.shuffle(couloirs_c)
                    index_couloir_c = 0

                    quart_race_a = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="A").first()
                    quart_race_b = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="B").first()
                    quart_race_c = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="C").first()
                    quart_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_quart.id, name="D").first()

                    list_quarts = []
                    list_quarts.append(quart_race_a)
                    list_quarts.append(quart_race_b)
                    list_quarts.append(quart_race_c)
                    list_quarts.append(quart_race_d)

                    for race in list_quarts:
                        for participant in race.participations:
                            if participant.resultat == 5:
                                db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_c.id, couloir_id=couloirs_c[index_couloir_c].id))
                                index_couloir_c += 1
                                cmptc += 1
                            db.session.commit()

                    titulaires_c = []
                    participants_c = Participant_race.query.filter_by(race_id=finale_race_c.id).all()
                    for participant_c in participants_c:
                        titulaires_c.append(participant_c.titulaire_id)

                    couloirs_d = Couloir.query.all()
                    random.shuffle(couloirs_d)
                    index_couloir_d = 0

                    for race in list_race:
                        for participant in race.participations:
                            if cmptd < limitd and index_couloir_d < 8:
                                if participant.titulaire_id not in titulaires_a and participant.titulaire_id not in titulaires_b and participant.titulaire_id not in titulaires_c:
                                    db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_d.id, couloir_id=couloirs_d[index_couloir_d].id))
                                    index_couloir_d += 1
                                    cmptd += 1
                            db.session.commit()

                    titulaires_d = []
                    participants_d = Participant_race.query.filter_by(race_id=finale_race_d.id).all()
                    for participant_d in participants_d:
                        titulaires_d.append(participant_d.titulaire_id)

                    couloirs_e = Couloir.query.all()
                    random.shuffle(couloirs_e)
                    index_couloir_e = 0

                    for race in list_race:
                        for participant in race.participations:
                            if cmpte < limite and index_couloir_e < 8:
                                if participant.titulaire_id not in titulaires_a and participant.titulaire_id not in titulaires_b and participant.titulaire_id not in titulaires_c and participant.titulaire_id not in titulaires_d:
                                    db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_e.id, couloir_id=couloirs_e[index_couloir_e].id))
                                    index_couloir_e += 1
                                    cmpte += 1
                            db.session.commit()

                    titulaires_e = []
                    participants_e = Participant_race.query.filter_by(race_id=finale_race_e.id).all()
                    for participant_e in participants_e:
                        titulaires_e.append(participant_e.titulaire_id)

                    couloirs_f = Couloir.query.all()
                    random.shuffle(couloirs_f)
                    index_couloir_f = 0
                    if nb_participants_categorie >= 37:
                        for race in list_race:
                            for participant in race.participations:
                                if cmptf < limitf and index_couloir_f < 8:
                                    if participant.titulaire_id not in titulaires_a and participant.titulaire_id not in titulaires_b and participant.titulaire_id not in titulaires_c and participant.titulaire_id not in titulaires_d and participant.titulaire_id not in titulaires_e:
                                        db.session.add(Participant_race(titulaire_id=participant.titulaire_id, race_id=finale_race_f.id, couloir_id=couloirs_f[index_couloir_f].id))
                                        index_couloir_f += 1
                                        cmptf += 1
                                db.session.commit()

                    finale_race_d = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="D").first()
                    finale_race_e = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="E").first()
                    finale_race_f = Race.query.filter_by(categorie_id=categorie.id, race_type_id=phase_finale.id, name="F").first()

                    for i in range(2) :
                        db.session.add(Manche(race_id=finale_race_d.id))
                    for i in range(2) :
                        db.session.add(Manche(race_id=finale_race_e.id))
                    db.session.commit()

                    if nb_participants_categorie >= 37:
                        for i in range(2) :
                            db.session.add(Manche(race_id=finale_race_f.id))

                    couloirs_d = Couloir.query.all()
                    random.shuffle(couloirs_d)
                    index_couloir_d = 0

                    couloirs_e = Couloir.query.all()
                    random.shuffle(couloirs_e)
                    index_couloir_e = 0

                    for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race_c.id).all()) :
                        for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                            if index_manche == 0 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                            elif index_manche == 1 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))
                    db.session.commit()


                    for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race_d.id).all()) :
                        for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                            if index_manche == 0 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                            elif index_manche == 1 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))
                    db.session.commit()

                    for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race_e.id).all()) :
                        for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                            if index_manche == 0 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                            elif index_manche == 1 :
                                db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))
                    db.session.commit()

                    if nb_participants_categorie >= 37:
                        for index_manche, manche in enumerate(Manche.query.filter_by(race_id=finale_race_f.id).all()) :
                            for participant_race in  Participant_race.query.filter_by(race_id=manche.race.id).all() :
                                if index_manche == 0 :
                                    db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_1))
                                elif index_manche == 1 :
                                    db.session.add(Participant_manche(titulaire_id=participant_race.titulaire_id, manche_id=manche.id, place_depart=participant_race.couloir.couloir_2))
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
                place_arrive = request.form.get(f'place_arrive_{participant.titulaire_manche.id}')
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
            categorie = race.categorie
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

@views.route("/championnat-<championnat_id>/etape-<etape_id>/download/",methods=['POST'])
@login_required
def generer_pdf_classement_categories(etape_id,championnat_id):
    liste_categories = Categorie.query.filter_by(etape_id=etape_id).all()
    liste_classements = []
    etape = Etape.query.filter_by(id=etape_id).first()
    for categorie in liste_categories:
        classement_transforme = get_classement_etape_categorie(etape_id,categorie.categorie_type.id)
        liste_classements.append(classement_transforme)
    html = render_template('classement_etape_categories_pdf.html',etape = etape, liste_categories= liste_categories,liste_classements=liste_classements)
    return render_pdf(HTML(string=html))

@views.route("/championnat-<championnat_id>/etape-<etape_id>/categorie-<categorie_type_id>/download/",methods=['POST'])
@login_required
def generer_pdf_classement_races(etape_id, championnat_id,categorie_type_id):
    etape = Etape.query.filter_by(id=etape_id).first()
    categorie_type = Categorie_type.query.filter_by(id=categorie_type_id).first()
    classement_transforme = get_classement_etape_categorie(etape_id,categorie_type_id)
    html = render_template('classement_etape_pdf.html',etape = etape, categorie_type=categorie_type,classement_transforme=classement_transforme)
    return render_pdf(HTML(string=html))

@views.route("/championnat-<championnat_id>/download/",methods=['POST'])
@login_required
def generer_pdf_classement_general(championnat_id):
    championnat = Championnat.query.filter_by(id=championnat_id).first()
    liste_etapes = Etape.query.filter_by(championnat_id=championnat_id).all()
    #chaque entrée de liste_groupes_categories représente une liste de catégories liées à une étape spécifique
    liste_types_categories = []

    #les clés de ce dictionnaire seront les categorie_type
    #les valeurs de ce dictionnaire seront d'autres dictionnaires
    # avec en clé les étapes et en valeur les classements d'étapes/categories
    # {Categorie1:{etape1:{pilote1:50,pilote2:47 ...},etape2{pilote1:47,pilote2:50 ...}},Categorie2{etape1{},etape2{} ...}} 
    dictionnaire_general = {}
    liste_types_categories.append(Categorie_type.query.all())
    for type_categorie in liste_types_categories[0]:
        dictionnaire_general[type_categorie] = {}
        dictionnaire_general[type_categorie]["general"] = {}
        for etape in liste_etapes:
            classement_etape_categorie = get_classement_etape_categorie(etape.id,type_categorie.id)
            #ci-dessous, un dictionnaire pour accueillir les différents classements d'étapes liés à un type de catégorie
            #on ajoute les dictionnaires de classement dans chaque dictionnaire de categorie
            #et un dictionnaire pour accueillir la somme des points pour toutes les étapes d'une catégorie
            
            dictionnaire_general[type_categorie][etape] = []
            for entree_classement in classement_etape_categorie:
                #on stocke les scores d'étapes de tous les pilotes liés à une catégorie et à une étape 
                dictionnaire_general[type_categorie][etape].append((entree_classement[0],entree_classement[1]))
                if entree_classement[0] not in dictionnaire_general[type_categorie]["general"]:
                    dictionnaire_general[type_categorie]["general"][entree_classement[0]] = entree_classement[1]
                else:
                    dictionnaire_general[type_categorie]["general"][entree_classement[0]] += entree_classement[1]
    for type_categorie in liste_types_categories[0]:
        #on trie le dictionnaire general sur la base des valeurs de points, tri décroissant.
        dictionnaire_general[type_categorie]["general"] = {k: v for k, v in sorted(dictionnaire_general[type_categorie]["general"].items(), key=lambda item: item[1],reverse=True)}
    #il nous reste encore à trier le classement général, mais problème, on n'a pas l'info des places hors général
    html = render_template("classement_general_pdf.html",liste_etapes=liste_etapes,classement_general_global=dictionnaire_general,championnat=championnat)
    return render_pdf(HTML(string=html))
@views.route("/championnat-<championnat_id>/etape-<etape_id>/categorie-<categorie_type_id>/race-<race_id>/manches/download/",methods=['POST'])
@login_required
def download_form_post(etape_id, championnat_id, categorie_type_id, race_id):
    manches = Manche.query.filter_by(race_id=race_id).all()
    race = Race.query.filter_by(id=race_id).first()
    liste_participants_race = Participant_race.query.filter_by(race_id = race.id)
    #retourne les titulaires pour une race donnée (pas possible de s'appuyer sur une référence directe à l'objet titulaire dans participant_race)
    #je veux tous les titulaires dont l'id est égal à titulaire_id dans liste_participants_race 
    etape = Etape.query.filter_by(id=etape_id).first()
    vecteurClassementRace = {}
    #on itère sur tous les participants de la race
    for participant_race in liste_participants_race:
        #pour une race, on a plusieurs manches
        for index, manche in enumerate(manches):
            liste_participants_manche = Participant_manche.query.filter_by(manche_id = manche.id)
            for participant_manche in liste_participants_manche:
                if participant_manche.titulaire_id == participant_race.titulaire_id:
                    if vecteurClassementRace.get(participant_race.titulaire_race):
                        vecteurClassementRace[participant_race.titulaire_race] = vecteurClassementRace[participant_race.titulaire_race] +participant_manche.resultat
                    else:
                        vecteurClassementRace[participant_race.titulaire_race] = participant_manche.resultat

    #il faudrait stocker ce vecteur de Classement de race quelque-part pour le réutiliser lors du classement d'étape
    categorie_type = Categorie_type.query.filter_by(id=categorie_type_id).first()
    club = etape.club
    #tri du vecteur de classement par valeur avant l'envoi
    sorted_classement = {}
    sorted_cle = sorted(vecteurClassementRace,key=vecteurClassementRace.get)
    for i in sorted_cle:
        sorted_classement[i] = vecteurClassementRace[i]
    html = render_template('manchesPDF.html', club=club,championnat_id=championnat_id, etape = etape, categorie_type=categorie_type, race=race,manches=manches, vecteur_classement_race = sorted_classement)
    return render_pdf(HTML(string=html))

def get_classement_etape_categorie(etape_id,categorie_type_id):
    """Fonction ne renvoyant pas de vue html mais servant à générer les données de classement pour une étape donnée et une catégorie d'age
    Elle se base sur les places d'arrivées lors des manches de finale ainsi que la lettre de chaque Race

    Args:
        etape_id (int): id de l'étape
        categorie_type_id (int): id du type de la catégorie

    Returns:
        un tuple avec en première valeur l'objet categorie qui concerne ce classement et ensuite en deuxième, une liste ordonnée selon l'ordre du classement contenant les pilotes et le score qui leur est associé pour l'étape passée en paramètre

    """
    categorie = Categorie.query.filter_by(etape_id=etape_id, categorie_type_id=categorie_type_id).first()
    race_type_finale = Race_type.query.filter_by(type="Finale").first()
    etape = Etape.query.filter_by(id=etape_id).first()
    categorie_type = Categorie_type.query.filter_by(id=categorie_type_id).first()
    liste_manches = []
    liste_races = []
    vecteur_classement_etape = {}
    classement_transforme = []
    if categorie is not None:
        if len(categorie.participations) > 8 and etape.championnat.championnat_type.type != "Départemental":
            liste_races = Race.query.filter_by(etape_id=etape_id, categorie_id=categorie.id, race_type_id=race_type_finale.id).all()
        else:
            liste_races = Race.query.filter_by(etape_id=etape_id, categorie_id=categorie.id).all()
    #cumul des positions en dessous
        if categorie.participations is not None and categorie.finie:
            for race in liste_races:
                liste_manches.append(Manche.query.filter_by(race_id=race.id).all())
            for groupe_manche in liste_manches:
                for manche in groupe_manche:
                    for participation in manche.participations:
                        if vecteur_classement_etape.get(participation.titulaire_manche):
                            vecteur_classement_etape[participation.titulaire_manche] += participation.resultat
                        else:
                            vecteur_classement_etape[participation.titulaire_manche] = participation.resultat
            if len(categorie.participations) > 8:
                #3 manches de qualification pour chaque race, les 6 meilleurs en A pour une finale en 2 manches les 3 autres en B pareil finale en 2 manches
                max_vecteur_classement = max(vecteur_classement_etape.values())
                titulaires_finale_B = []
                for race in liste_races:
                    if race.name == "B":
                        for participant_finale_B in race.participations:
                            titulaires_finale_B.append(participant_finale_B.titulaire_race)
                for titulaire_finale_B in titulaires_finale_B:
                    vecteur_classement_etape[titulaire_finale_B] += max_vecteur_classement

                if len(categorie.participations) > 16:
                    #maj du nouveau max ci-dessous
                    max_vecteur_classement = max(vecteur_classement_etape.values())
                    titulaires_finale_C = []
                    for race in liste_races:
                        if race.name == "C":
                            for participant_finale_C in race.participations:
                                titulaires_finale_C.append(participant_finale_C.titulaire_race)
                    for titulaire_finale_C in titulaires_finale_C:
                        vecteur_classement_etape[titulaire_finale_C] += max_vecteur_classement
                    #maj du nouveau max ci-dessous
                    max_vecteur_classement = max(vecteur_classement_etape.values())

                if len(categorie.participations) > 24:
                    titulaires_finale_D = []
                    for race in liste_races:
                        if race.name == "D":
                            for participant_finale_D in race.participations:
                                titulaires_finale_D.append(participant_finale_D.titulaire_race)
                    for titulaire_finale_D in titulaires_finale_D:
                        vecteur_classement_etape[titulaire_finale_D] += max_vecteur_classement

                if len(categorie.participations) > 32:
                    titulaires_finale_E = []
                    for race in liste_races:
                        if race.name == "E":
                            for participant_finale_E in race.participations:
                                titulaires_finale_E.append(participant_finale_E.titulaire_race)
                    for titulaire_finale_E in titulaires_finale_E:
                        vecteur_classement_etape[titulaire_finale_E] += max_vecteur_classement

            #on retourne une liste triée sur la base de vecteur_classement_étape contenant les pilotes et le score qui leur est associé
            classement_etape_brut = sorted(
                vecteur_classement_etape.items(), key=lambda x: x[1])
            for index_classement in range(len(classement_etape_brut)):
                if index_classement == 0:
                    classement_transforme.append(
                        (classement_etape_brut[index_classement][0], 50))
                elif index_classement == 1:
                    classement_transforme.append((classement_etape_brut[index_classement][0], 47))
                elif index_classement == 2:
                    classement_transforme.append((classement_etape_brut[index_classement][0], 45))
                #on est dans le cas où index_classement >= 3
                else:
                    classement_transforme.append((classement_etape_brut[index_classement][0], 50-(index_classement+3)))
    return classement_transforme
