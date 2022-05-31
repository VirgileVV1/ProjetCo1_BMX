# Projet Collectif 

Projet 1 : Logiciel pour organisation des compétitions de la section bicross (BMX) de
l’UFOLEP37.

Entreprise : BMX/Ufolep

Equipe :
Antoine De Gryse
Emeric Verrier
Ines Garbaa
Jules Courne
Kyllian Bizot--pageot
Lehyan Flouriot
Pierre Fourre <pierre.fourre@etu.univ-tours.fr>
Virgile Vall-Villellas

La liste des dépendances se trouve dans requirements.txt. Ce projet utilise weasyprint, un projet qui permet de convertir les pages html en pdf.
Pour installer WeasyPrint sur Windows 10, la marche à suivre est précisée dans la documentation : 
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows
il vous faudra installer GTK3  ( https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe ). assurez vous que la case Set up PATH soit cochée et que l'option "<instdir> \bin (recommended)" soit sélectionnée.

Pour installer chacune des bibliothèques de notre projet : pip install -r requirements.txt

Pour lancer le projet : python3 app.py
