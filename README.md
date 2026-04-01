# Sistema de gestión de socios
## Asociación Iberoamericana "Shito Ryu Itosu Kai" de Karate y Kobudo

Aplicación web para gestionar socios, registrar pagos de cuotas y emitir comprobantes en PDF.

---

## Funcionalidades

- Dashboard con estado de cuotas de todos los socios
- Alta, baja y modificación de socios
- Registro de pagos (efectivo o transferencia)
- Generación de comprobante PDF con recibo + estado de cuenta
- Envío del comprobante por email al socio
- Configuración de cuota mensual y credenciales de email

---

## Instalación local (para probar en tu PC)

### Requisitos
- Python 3.10 o superior

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/richardyag/asoc-ibero.git
cd asoc-ibero

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar
python app.py
```

Abrí el navegador en `http://localhost:5000`

**Contraseña inicial:** `karate2024`
**Importante:** cambiala desde Configuración antes de publicar en internet.

---

## Publicación en PythonAnywhere (hosting gratuito)

### 1. Crear cuenta
Registrarse en [pythonanywhere.com](https://www.pythonanywhere.com) (plan Beginner, gratuito).

### 2. Subir el código
En la consola de PythonAnywhere:
```bash
git clone https://github.com/richardyag/asoc-ibero.git
cd asoc-ibero
pip install --user -r requirements.txt
```

### 3. Configurar la app web
1. Ir a la pestaña **Web** → **Add a new web app**
2. Elegir **Manual configuration** → **Python 3.10**
3. En **Code** → **Source code**: `/home/TU_USUARIO/asoc-ibero`
4. En **WSGI configuration file**: editar y reemplazar TODO el contenido con:

```python
import sys, os
sys.path.insert(0, '/home/TU_USUARIO/asoc-ibero')
os.chdir('/home/TU_USUARIO/asoc-ibero')
from app import app as application, init_db
init_db()
```

5. Hacer clic en **Reload** para publicar.

Tu app quedará disponible en `https://TU_USUARIO.pythonanywhere.com`

---

## Configuración del email (Gmail)

Para poder enviar recibos por email necesitás una **Contraseña de aplicación** de Google:

1. Ir a [myaccount.google.com](https://myaccount.google.com)
2. **Seguridad** → activar **Verificación en dos pasos**
3. Volver a Seguridad → **Contraseñas de aplicaciones**
4. Seleccionar "Correo" → "Otro (nombre personalizado)" → escribir "Recibos Karate"
5. Google genera una contraseña de 16 caracteres
6. Ingresarla en el sistema desde **Configuración → Email**

---

## Estructura del proyecto

```
asoc-ibero/
├── app.py              # Rutas y lógica principal
├── models.py           # Modelos de base de datos
├── pdf_utils.py        # Generación de PDFs
├── wsgi.py             # Para PythonAnywhere
├── requirements.txt
├── static/
│   └── logo.jpg
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── socios_lista.html
    ├── socio_detalle.html
    ├── socio_form.html
    ├── pago_form.html
    ├── recibo_detalle.html
    └── configuracion.html
```

---

## Primeros pasos después de instalar

1. Ingresar con la contraseña `karate2024`
2. Ir a **Configuración** y:
   - Cambiar la contraseña de acceso
   - Ingresar el valor de la cuota mensual
   - Configurar el email (si querés enviar recibos)
3. Ir a **Socios** → **Nuevo socio** y cargar los 22 asociados
4. Para cada socio con deuda desde 2024, ir a su ficha y usar **Registrar pago**
   (podés seleccionar múltiples meses de una vez)
