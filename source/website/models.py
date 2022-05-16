from flask_login import UserMixin
from .__init__ import db

class User(UserMixin, db.Model) :
    """Représentation des utilisateurs dans la base de données

    Classe représentant les utilisateurs dans la base de données, la table associée est "user"

    Attributes:
        id: Clef primaire, id de l'utilisateur
        username: Chaine de caractère de taille 100, nom d'utilisateur
        password: Chaine de caractère de taille 100, hash du mot de passe
    """
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Sexe(db.Model) :
    """Représentation des sexes dans la base de données

    Classe représentant les sexes dans la base de données, la table associée est "sexe"

    Attributes:
        id: Clef primaire, id du sexe
        denomination: Chaine de caractère de taille 20, denomination du sexe (ie: Homme)
        titulaires: Liste de tous les titulaires ayant le sexe
    """
    __tablename__ = "sexe"

    id = db.Column(db.Integer, primary_key=True)
    denomination = db.Column(db.String(20), unique=True, nullable=False)
    titulaires = db.relationship('Titulaire', backref='sexe', lazy=True)


class Club(db.Model) :
    """Représentation des clubs dans la base de données

    Classe représentant les clubs dans la base de données, la table associée est "club"

    Attributes:
        id: Clef primaire, id du club
        ville: Chaine de caractère de taille 100, ville du club
        initiales: Chaine de caractère de taille 5, initiale(s) du club
        titulaire: Liste des titulaires du club
        etapes: Liste des étapes ayant lieux dans la ville du club
    """
    __tablename__ = "club"

    id = db.Column(db.Integer, primary_key=True)
    ville = db.Column(db.String(100), unique=True, nullable=False)
    initiales = db.Column(db.String(5), unique=True, nullable=False)
    titulaires = db.relationship('Titulaire', backref='club', lazy=True)
    etapes = db.relationship('Etape', backref='club', lazy=True)

class Titulaire(db.Model) :
    """Représentation des titulaires dans la base de données

    Classe représentant les titulaires dans la base de données, la table associée est "titulaire"

    Attributes:
        id: Clef primaire, id du titulaire
        nom: Chaine de caractère de taille 100, nom du titulaire
        prenom: Chaine de caractère de taille 100, prénom du titulaire
        date_naissance: Date, date de naissance du titulaire
        numero_plaque: Chaine de caractère de taille 2, numéro de plaque du titulaire
        club_id: Entier, id du club du titulaire
        sexe_id: Entier, id du sexe du titulaire
        manches: Liste des manches auxquelles le titulaire à participé
    """
    __tablename__ = "titulaire"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    date_naissance = db.Column(db.Date, nullable=False)
    numero_plaque = db.Column(db.String(2), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    sexe_id = db.Column(db.Integer, db.ForeignKey('sexe.id'), nullable=False)
    manches = db.relationship('Participant_manche', backref='titulaire', lazy=True)

class Categorie_type(db.Model) :
    """Représentation des types de catégories dans la base de données

    Classe représentant les types de catégories dans la base de données, la table associée est "categorie_type"

    Attributes:
        id: Clef primaire, id du type de categorie
        min_age: Entier, age minimum de la catégorie
        max_age: Entier, age maximum de la catégorie
        name: Chaine de caractère de taille 100, nom du type de catégorie
        races: Liste des races du type de la catégorie
        categories: Liste des catégories de ce type
    """
    __tablename__ = "categorie_type"

    id = db.Column(db.Integer, primary_key=True)
    min_age = db.Column(db.Integer, nullable=False)
    max_age = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    races =  db.relationship('Race', backref='categorie_type', lazy=True)
    categories = db.relationship('Categorie', backref='categorie_type', lazy=True)

class Championnat_type(db.Model) :
    """Représentation des types de championnats dans la base de données

    Classe représentant les types de championnats dans la base de données, la table associée est "championnat_type"

    Attributes:
        id: Clef primaire, id du type de categorie
        type: Chaine de caractère de taille 100, dénomination du type de championnat (ie: Régionnal)
        nb_etapes_max: Entier, nombre d'étapes maximum du type de championnat
        championnats: Liste des championnats de ce type
    """
    __tablename__ = "championnat_type"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    nb_etapes_max = db.Column(db.Integer, nullable=False)
    championnats =  db.relationship('Championnat', backref='championnat_type', lazy=True)

class Championnat(db.Model) :
    """Représentation des championnats dans la base de données

    Classe représentant les championnats dans la base de données, la table associée est "championnat"

    Attributes:
        id: Clef primaire, id de la categorie
        championnat_type_id: Entier, id du type de championnat
        annee: Entier, année du championnat
        etapes: Liste des étapes de ce championnat
    """
    __tablename__ = "championnat"

    id = db.Column(db.Integer, primary_key=True)
    championnat_type_id = db.Column(db.Integer, db.ForeignKey('championnat_type.id'), nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    etapes = db.relationship('Etape', backref='championnat', lazy=True, cascade="all, delete")

class Etape(db.Model) :
    """Représentation des étapes dans la base de données

    Classe représentant les étapes dans la base de données, la table associée est "etape"

    Attributes:
        id: Clef primaire, id de l'étape
        championna_id: Entier, id du championnat
        lieu_id: Entier, id du club organisant l'étape
        finie: Bool, l'étape est-elle terminée ?
        participations: Liste des participations à l'étape
        races: Liste des races de l'étapes
        categories: Liste des catégories de l'étape
    """
    __tablename__ = "etape"

    id = db.Column(db.Integer, primary_key=True)
    championnat_id = db.Column(db.Integer, db.ForeignKey('championnat.id'), nullable=False)
    lieu_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    finie = db.Column(db.Boolean, default=False)
    participations = db.relationship('Participant_etape', backref='etape', lazy=True, cascade="all, delete")
    races = db.relationship('Race', backref='etape', lazy=True, cascade="all, delete")
    categories = db.relationship('Categorie', backref='etape', lazy=True, cascade="all, delete")

class Participant_etape(db.Model) :
    """Représentation des participations à une étaps dans la base de données

    Classe représentant les participations à une étaps dans la base de données, la table associée est "participant_etape"

    Attributes:
        id: Clef primaire, id de la participation à l'étape
        titulaire_id: Entier, id du titulaire
        etape_id: Entier, id de l'étape
        categorie_type_id: Entier, id du type de catégorie
    """
    __tablename__ = "participant_etape"

    id = db.Column(db.Integer, primary_key=True)
    titulaire_id = db.Column(db.Integer, db.ForeignKey('titulaire.id'), nullable=False)
    etape_id = db.Column(db.Integer, db.ForeignKey('etape.id'), nullable=False)
    categorie_type_id = db.Column(db.Integer, db.ForeignKey('categorie_type.id'), nullable=False)

class Categorie(db.Model) :
    """Représentation des catégories dans la base de données

    Classe représentant les catégories dans la base de données, la table associée est "categorie"

    Attributes:
        id: Clef primaire, id de la catégorie
        etape_id: Entier, id de l'étape
        categorie_type_id: Entier, id du type de catégorie
        pool_finie: Bool, les pool sont-elles finies ?
        quart_finie: Bool, les quart sont-ils finis ?
        demi_finie: Bool, les demi sont-ils finies ?
        finale_finie: Bool, les finale sont-elles finies ?
        quart_genere: Bool, les quart sont-ils générés ?
        demi_genere: Bool, les demi sont-elles générées ?
        finale_genere: Bool, les finale sont-elles générées ?
        finie: Bool, la catégorie est-elle terminée ?
        races: Liste des races de la catégorie
        participations: Liste des participations à la catégorie

    """
    __tablename__ = "categorie"

    id = id = db.Column(db.Integer, primary_key=True)
    etape_id = db.Column(db.Integer, db.ForeignKey('etape.id'), nullable=False)
    categorie_type_id = db.Column(db.Integer, db.ForeignKey('categorie_type.id'), nullable=False)
    pool_finie = db.Column(db.Boolean, default=False)
    quart_finie = db.Column(db.Boolean, default=False)
    demi_finie = db.Column(db.Boolean, default=False)
    finale_finie = db.Column(db.Boolean, default=False)
    quart_genere = db.Column(db.Boolean, default=False)
    demi_genere = db.Column(db.Boolean, default=False)
    finale_genere = db.Column(db.Boolean, default=False)
    finie = db.Column(db.Boolean, default=False)
    races = db.relationship('Race', backref='categorie', lazy=True, cascade="all, delete")
    participations = db.relationship('Participant_categorie', backref='categorie', lazy=True, cascade="all, delete")

class Participant_categorie(db.Model) :
    """Représentation des participations à la catégorie dans la base de données

    Classe représentant les participations à la catégorie dans la base de données, la table associée est "participant_categorie"

    Attributes:
        id: Clef primaire, id de la participation à la catégorie
        titulaire_id: Entier, id du titulaire
        categorie_id: Entier, id de la catégorie

    """
    __tablename__ = "participant_categorie"

    id = id = db.Column(db.Integer, primary_key=True)
    titulaire_id = db.Column(db.Integer, db.ForeignKey('titulaire.id'), nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie.id'), nullable=False)

class Couloir(db.Model) :
    """Représentation des couloirs dans la base de données

    Classe représentant les successions de couloirs pour leur attribution dans la base de données, la table associée est "couloir"

    Attributes:
        id: Clef primaire, id du couloir
        couloir_1: Entier, couloir pour la première course
        couloir_2: Entier, couloir pour la deuxième course
        couloir_3: Entier, couloir pour la troisième course
        couloir_4: Entier, couloir pour la quatrième course
        couloir_5: Entier, couloir pour la cinquième course
        participants_race: Liste des participations aux races avec cette enchainement de couloirs

    """
    __tablename__ = "couloir"

    id = db.Column(db.Integer, primary_key=True)
    couloir_1 = db.Column(db.Integer)
    couloir_2 = db.Column(db.Integer)
    couloir_3 = db.Column(db.Integer)
    couloir_4 = db.Column(db.Integer)
    couloir_5 = db.Column(db.Integer)
    participants_race = db.relationship('Participant_race', backref='couloir', lazy=True)

class Participant_race(db.Model) :
    """Représentation des participations à la race dans la base de données

    Classe représentant les participations à la race dans la base de données, la table associée est "participant_race"

    Attributes:
        id: Clef primaire, id de la participation à la race
        titulaire_id: Entier, id du titulaire
        race_id: Entier, id de la race
        couloir_id: Entier, id du couloir attribué
        resultat: Entier, nombre de points sur la race

    """
    __tablename__ = "participant_race"

    id = db.Column(db.Integer, primary_key=True)
    titulaire_id = db.Column(db.Integer, db.ForeignKey('titulaire.id'), nullable=False)
    race_id = db.Column(db.Integer, db.ForeignKey('race.id'), nullable=False)
    couloir_id = db.Column(db.Integer, db.ForeignKey('couloir.id'), nullable=False)
    resultat = db.Column(db.Integer, default=45)

class Race(db.Model) :
    """Représentation des races dans la base de données

    Classe représentant les races dans la base de données, la table associée est "race"

    Attributes:
        id: Clef primaire, id de la race
        name: Chaine de caractère de taille 1, nom de la race (ie: A)
        etape_id: Entier, id de l'étape de la race
        categorie_type_id: Entier, id du type de catégorie
        race_type_id: Entier, id du type de race
        categorie_id: Entier, id de la catégorie de la race
        finie: Bool, la race est-elle terminée ?
        participations: Liste des participations à la race
        manches: Liste des manches de la race

    """
    __tablename__ = "race"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1), nullable=False)
    etape_id = db.Column(db.Integer, db.ForeignKey('etape.id'), nullable=False)
    categorie_type_id = db.Column(db.Integer, db.ForeignKey('categorie_type.id'), nullable=False)
    race_type_id = db.Column(db.Integer, db.ForeignKey('race_type.id'), nullable=False)
    categorie_id = db.Column(db.Integer, db.ForeignKey('categorie.id'), nullable=False)
    finie = db.Column(db.Boolean, default=False)
    participations = db.relationship('Participant_race', backref='race', order_by=Participant_race.resultat, lazy=True, cascade="all, delete")
    manches = db.relationship('Manche', backref='race', lazy=True, cascade="all, delete")

class Race_type(db.Model) :
    """Représentation des types de races dans la base de données

    Classe représentant les types de races dans la base de données, la table associée est "race_type"

    Attributes:
        id: Clef primaire, id du type de race
        type: Chaine de caractère de taille 50, dénomination du type de race (ie: Pool)
        races: Liste des races de cette catégorie
    """
    __tablename__ = "race_type"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    races = db.relationship('Race', backref='race_type', lazy=True)

class Participant_manche(db.Model) :
    """Représentation des participations à la manche dans la base de données

    Classe représentant les participations à la manche dans la base de données, la table associée est "participant_manche"

    Attributes:
        id: Clef primaire, id de la participation à la manche
        titulaire_id: Entier, id du titulaire
        manche_id: Entier, id de la manche
        place_depart: Entier, numéro de couloir de départ pour la manche
        resultat: Entier, nombre de points sur la manche

    """
    __tablename__ = "participant_manche"

    id = db.Column(db.Integer, primary_key=True)
    titulaire_id = db.Column(db.Integer, db.ForeignKey('titulaire.id'), nullable=False)
    manche_id = db.Column(db.Integer, db.ForeignKey('manche.id'), nullable=False)
    place_depart = db.Column(db.Integer)
    resultat = db.Column(db.Integer, default=9)

class Manche(db.Model) :
    """Représentation des manches dans la base de données

    Classe représentant les manches dans la base de données, la table associée est "manche"

    Attributes:
        id: Clef primaire, id de la manche
        race_id: Entier, id de la race de la manche
        finie: Bool, la manche est-elle terminée ?
        participations: Liste des participations à la manche

    """
    __tablename__ = "manche"

    id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.Integer, db.ForeignKey('race.id'), nullable=False)
    finie = db.Column(db.Boolean, default=False)
    participations = db.relationship('Participant_manche', backref='manche', order_by=Participant_manche.place_depart, lazy=True, cascade="all, delete")
