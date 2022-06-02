from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user

from .models import User
from .__init__ import db

auth = Blueprint("auth", __name__)

@auth.route("/login")
def login() :
    """Fonction liée au end-point "/login"

    Fonction affichant la page de connection

    Returns:
        Template: template login.html

    """
    return render_template("login.html")

@auth.route("/login", methods=["POST"])
def login_post() :
    """Fonction liée au end-point "/login" en methode POST

    Fonction gérant la connection

    Returns:
        Redirect: redirection vers views.home ou auth.login

    """
    username = request.form.get('username')
    password = request.form.get('password')
    remember_me = request.form.get('rememberMe')

    if username is not None and username != '' and password is not None and password != "" :
        if remember_me == 'on' :
            remember_me = True
        else :
            remember_me = False

        user = User.query.filter_by(username=username).first()
        if user is not None and check_password_hash(user.password, password) :
            login_user(user, remember=remember_me)

            return redirect(url_for('views.home'))

    return redirect(url_for('auth.login'))

@auth.route("/logout")
def logout() :
    """Fonction liée au end-point "/logout"

    Fonction déconnectant l'utilisateur

    Returns:
        Redirect: redirection vers views.home

    """
    logout_user()
    return redirect(url_for('views.home'))
