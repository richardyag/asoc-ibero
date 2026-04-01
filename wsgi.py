"""
Archivo WSGI para PythonAnywhere.
En PythonAnywhere, este archivo debe apuntar a tu directorio del proyecto.
Reemplazá 'TU_USUARIO' con tu nombre de usuario de PythonAnywhere.
"""
import sys
import os

# Ajustá esta ruta con tu usuario de PythonAnywhere
project_home = '/home/TU_USUARIO/asoc-ibero'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import app as application, init_db
init_db()
