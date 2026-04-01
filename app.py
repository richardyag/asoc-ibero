import os
import smtplib
from datetime import date, datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import (Flask, flash, make_response, redirect, render_template,
                   request, url_for)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

from models import Admin, Configuracion, Pago, PagoMes, Socio, db
from pdf_utils import MESES_ES, generar_recibo_pdf

# ── Configuración de la app ───────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ibero-shito-ryu-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///asociacion.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Iniciá sesión para continuar.'
login_manager.login_message_category = 'warning'

# Mes/año a partir del cual el sistema lleva registro
INICIO_SISTEMA = date(2024, 1, 1)


# ── Helpers ───────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))


def get_config(clave, default=''):
    cfg = Configuracion.query.filter_by(clave=clave).first()
    return cfg.valor if cfg else default


def set_config(clave, valor):
    cfg = Configuracion.query.filter_by(clave=clave).first()
    if cfg:
        cfg.valor = valor
    else:
        db.session.add(Configuracion(clave=clave, valor=valor))
    db.session.commit()


def meses_rango(desde: date, hasta: date):
    """Lista de (anio, mes) desde `desde` hasta `hasta` inclusive."""
    result, y, m = [], desde.year, desde.month
    while (y, m) <= (hasta.year, hasta.month):
        result.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return result


def get_historial_socio(socio):
    """
    Retorna dict {(anio, mes): info | None} para todos los meses
    desde el inicio del sistema (o alta del socio) hasta hoy.

    info = {'numero_recibo': int, 'fecha_pago': date, 'pago_id': int}
    """
    inicio = max(INICIO_SISTEMA,
                 date(socio.fecha_alta.year, socio.fecha_alta.month, 1))
    hoy = date.today()
    todos = meses_rango(inicio, hoy)

    pagados = {}
    for pago in socio.pagos:
        for pm in pago.meses:
            pagados[(pm.anio, pm.mes)] = {
                'numero_recibo': pago.numero_recibo,
                'fecha_pago': pago.fecha_pago,
                'pago_id': pago.id,
            }

    return {(y, m): pagados.get((y, m)) for (y, m) in todos}


def get_meses_adeudados(socio):
    return [(y, m) for (y, m), info in get_historial_socio(socio).items()
            if info is None]


# ── Rutas ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        admin = Admin.query.first()
        if admin and admin.check_password(request.form.get('password', '')):
            login_user(admin, remember=True)
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Contraseña incorrecta.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    socios = Socio.query.filter_by(activo=True).order_by(
        Socio.apellido, Socio.nombre).all()
    valor_cuota = float(get_config('valor_cuota', '0'))

    datos, total_adeudado, al_dia, con_deuda = [], 0, 0, 0
    for s in socios:
        adeud = get_meses_adeudados(s)
        monto = len(adeud) * valor_cuota
        ultimo = max((p.fecha_pago for p in s.pagos), default=None)
        total_adeudado += monto
        if adeud:
            con_deuda += 1
        else:
            al_dia += 1
        datos.append({
            'socio': s,
            'meses_adeudados': len(adeud),
            'monto_adeudado': monto,
            'ultimo_pago': ultimo,
        })

    return render_template('dashboard.html',
                           datos_socios=datos,
                           total_socios=len(socios),
                           socios_al_dia=al_dia,
                           socios_con_deuda=con_deuda,
                           total_adeudado=total_adeudado,
                           valor_cuota=valor_cuota)


@app.route('/socios')
@login_required
def socios_lista():
    socios = Socio.query.order_by(Socio.apellido, Socio.nombre).all()
    return render_template('socios_lista.html', socios=socios)


@app.route('/socios/nuevo', methods=['GET', 'POST'])
@login_required
def socio_nuevo():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        apellido = request.form['apellido'].strip()
        email = request.form.get('email', '').strip()
        telefono = request.form.get('telefono', '').strip()
        fecha_str = request.form.get('fecha_alta', '')

        if not nombre or not apellido or not fecha_str:
            flash('Nombre, apellido y fecha de alta son obligatorios.', 'danger')
            return render_template('socio_form.html', socio=None,
                                   today=date.today().isoformat())

        fecha_alta = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        s = Socio(nombre=nombre, apellido=apellido, email=email,
                  telefono=telefono, fecha_alta=fecha_alta, activo=True)
        db.session.add(s)
        db.session.commit()
        flash(f'Socio {nombre} {apellido} agregado correctamente.', 'success')
        return redirect(url_for('socio_detalle', id=s.id))

    return render_template('socio_form.html', socio=None,
                           today=date.today().isoformat())


@app.route('/socios/<int:id>')
@login_required
def socio_detalle(id):
    socio = db.get_or_404(Socio, id)
    historial = get_historial_socio(socio)
    valor_cuota = float(get_config('valor_cuota', '0'))
    meses_adeud = [(y, m) for (y, m), i in historial.items() if i is None]
    monto_adeud = len(meses_adeud) * valor_cuota
    anios = sorted({y for (y, _) in historial})

    return render_template('socio_detalle.html',
                           socio=socio,
                           historial=historial,
                           anios=anios,
                           meses_adeudados=meses_adeud,
                           monto_adeudado=monto_adeud,
                           valor_cuota=valor_cuota,
                           MESES_ES=MESES_ES)


@app.route('/socios/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def socio_editar(id):
    socio = db.get_or_404(Socio, id)

    if request.method == 'POST':
        socio.nombre = request.form['nombre'].strip()
        socio.apellido = request.form['apellido'].strip()
        socio.email = request.form.get('email', '').strip()
        socio.telefono = request.form.get('telefono', '').strip()
        socio.fecha_alta = datetime.strptime(
            request.form['fecha_alta'], '%Y-%m-%d').date()
        socio.activo = 'activo' in request.form
        db.session.commit()
        flash('Datos actualizados.', 'success')
        return redirect(url_for('socio_detalle', id=socio.id))

    return render_template('socio_form.html', socio=socio,
                           today=date.today().isoformat())


@app.route('/socios/<int:id>/pago', methods=['GET', 'POST'])
@login_required
def registrar_pago(id):
    socio = db.get_or_404(Socio, id)
    valor_cuota = float(get_config('valor_cuota', '0'))
    meses_adeud = sorted(get_meses_adeudados(socio))

    if request.method == 'POST':
        meses_raw = request.form.getlist('meses')  # ["2024-3", "2024-4", ...]
        if not meses_raw:
            flash('Seleccioná al menos un mes.', 'danger')
            return redirect(url_for('registrar_pago', id=id))

        meses_sel = []
        for ms in meses_raw:
            y, m = ms.split('-')
            meses_sel.append((int(y), int(m)))

        try:
            monto = float(request.form['monto'].replace(',', '.'))
        except (ValueError, KeyError):
            flash('Monto inválido.', 'danger')
            return redirect(url_for('registrar_pago', id=id))

        metodo = request.form.get('metodo', 'efectivo')
        notas = request.form.get('notas', '').strip()

        try:
            fecha_pago = datetime.strptime(
                request.form.get('fecha_pago', ''), '%Y-%m-%d').date()
        except ValueError:
            fecha_pago = date.today()

        ultimo_nro = db.session.query(
            db.func.max(Pago.numero_recibo)).scalar() or 0
        numero_recibo = ultimo_nro + 1

        pago = Pago(socio_id=socio.id, fecha_pago=fecha_pago, monto=monto,
                    metodo=metodo, numero_recibo=numero_recibo, notas=notas)
        db.session.add(pago)
        db.session.flush()

        for (y, m) in meses_sel:
            db.session.add(PagoMes(pago_id=pago.id, anio=y, mes=m))

        db.session.commit()
        flash(f'Pago registrado — Recibo N° {numero_recibo:04d}.', 'success')
        return redirect(url_for('ver_recibo', pago_id=pago.id))

    # Agrupar meses adeudados por año para el template
    meses_por_anio = {}
    for (y, m) in meses_adeud:
        meses_por_anio.setdefault(y, []).append(m)

    return render_template('pago_form.html',
                           socio=socio,
                           meses_por_anio=meses_por_anio,
                           valor_cuota=valor_cuota,
                           MESES_ES=MESES_ES,
                           today=date.today().isoformat())


@app.route('/recibo/<int:pago_id>')
@login_required
def ver_recibo(pago_id):
    pago = db.get_or_404(Pago, pago_id)
    return render_template('recibo_detalle.html', pago=pago, MESES_ES=MESES_ES)


@app.route('/recibo/<int:pago_id>/pdf')
@login_required
def descargar_pdf(pago_id):
    pago = db.get_or_404(Pago, pago_id)
    historial = get_historial_socio(pago.socio)
    valor_cuota = float(get_config('valor_cuota', '0'))
    pdf = generar_recibo_pdf(pago, pago.socio, historial, valor_cuota)

    resp = make_response(pdf)
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = \
        f'inline; filename="recibo_{pago.numero_recibo:04d}.pdf"'
    return resp


@app.route('/recibo/<int:pago_id>/enviar', methods=['POST'])
@login_required
def enviar_recibo(pago_id):
    pago = db.get_or_404(Pago, pago_id)
    socio = pago.socio

    if not socio.email:
        flash('El socio no tiene email registrado.', 'warning')
        return redirect(url_for('ver_recibo', pago_id=pago_id))

    gmail_user = get_config('gmail_user')
    gmail_pass = get_config('gmail_app_password')
    if not gmail_user or not gmail_pass:
        flash('Configurá el email en Configuración antes de enviar.', 'warning')
        return redirect(url_for('configuracion'))

    historial = get_historial_socio(socio)
    valor_cuota = float(get_config('valor_cuota', '0'))
    pdf = generar_recibo_pdf(pago, socio, historial, valor_cuota)

    meses_str = ', '.join(f'{MESES_ES[pm.mes]} {pm.anio}' for pm in pago.meses)

    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = socio.email
    msg['Subject'] = (f'Recibo N° {pago.numero_recibo:04d} — '
                      'Asociación Iberoamericana Shito Ryu Itosu Kai')
    cuerpo = (
        f'Estimado/a {socio.nombre} {socio.apellido},\n\n'
        f'Adjunto encontrará su comprobante de pago N° {pago.numero_recibo:04d} '
        f'correspondiente a {meses_str}, junto con su estado de cuenta actualizado.\n\n'
        'Muchas gracias.\n\n'
        'Asociación Iberoamericana "Shito Ryu Itosu Kai" de Karate y Kobudo'
    )
    msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

    adjunto = MIMEBase('application', 'pdf')
    adjunto.set_payload(pdf)
    encoders.encode_base64(adjunto)
    adjunto.add_header('Content-Disposition',
                       f'attachment; filename="recibo_{pago.numero_recibo:04d}.pdf"')
    msg.attach(adjunto)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as srv:
            srv.login(gmail_user, gmail_pass)
            srv.sendmail(gmail_user, socio.email, msg.as_string())
        flash(f'Recibo enviado a {socio.email}.', 'success')
    except Exception as e:
        flash(f'Error al enviar email: {e}', 'danger')

    return redirect(url_for('ver_recibo', pago_id=pago_id))


@app.route('/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion():
    if request.method == 'POST':
        accion = request.form.get('accion')

        if accion == 'cuota':
            try:
                valor = float(request.form['valor_cuota'].replace(',', '.'))
                set_config('valor_cuota', str(valor))
                flash('Valor de cuota actualizado.', 'success')
            except ValueError:
                flash('Ingresá un número válido.', 'danger')

        elif accion == 'email':
            set_config('gmail_user', request.form.get('gmail_user', '').strip())
            pw = request.form.get('gmail_app_password', '').strip()
            if pw:
                set_config('gmail_app_password', pw)
            flash('Configuración de email guardada.', 'success')

        elif accion == 'password':
            nueva = request.form.get('nueva_password', '')
            confirmar = request.form.get('confirmar_password', '')
            if nueva != confirmar:
                flash('Las contraseñas no coinciden.', 'danger')
            elif len(nueva) < 6:
                flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            else:
                admin = Admin.query.first()
                admin.set_password(nueva)
                db.session.commit()
                flash('Contraseña actualizada.', 'success')

    return render_template('configuracion.html',
                           valor_cuota=get_config('valor_cuota', '0'),
                           gmail_user=get_config('gmail_user', ''))


# ── Inicialización ────────────────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        if not Admin.query.first():
            admin = Admin()
            admin.set_password('karate2024')
            db.session.add(admin)
            db.session.commit()


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
