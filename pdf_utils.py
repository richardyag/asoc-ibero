import io
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (HRFlowable, Image, PageBreak, Paragraph,
                                 SimpleDocTemplate, Spacer, Table, TableStyle)

MESES_ES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'logo.jpg')

COLOR_ROJO = colors.HexColor('#c0392b')


def _estilo(size, bold=False, alignment=TA_CENTER, color=colors.black, space_after=4):
    return ParagraphStyle(
        f's{size}{"b" if bold else ""}',
        fontSize=size,
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        alignment=alignment,
        textColor=color,
        spaceAfter=space_after,
        leading=size * 1.4,
    )


def _encabezado(story):
    if os.path.exists(LOGO_PATH):
        img = Image(LOGO_PATH, width=3.5 * cm, height=3.5 * cm)
        img.hAlign = 'CENTER'
        story.append(img)
        story.append(Spacer(1, 0.2 * cm))

    story.append(Paragraph('ASOCIACIÓN IBEROAMERICANA', _estilo(13, bold=True)))
    story.append(Paragraph('"SHITO RYU ITOSU KAI"', _estilo(13, bold=True, color=COLOR_ROJO)))
    story.append(Paragraph('DE KARATE Y KOBUDO', _estilo(10)))
    story.append(Spacer(1, 0.15 * cm))
    story.append(HRFlowable(width='100%', thickness=2, color=COLOR_ROJO))
    story.append(Spacer(1, 0.4 * cm))


def generar_recibo_pdf(pago, socio, historial, valor_cuota):
    """
    Genera un PDF de dos páginas: recibo de pago + estado de cuenta.

    pago        : objeto Pago (con .meses relacionados)
    socio       : objeto Socio
    historial   : dict {(anio, mes): {'numero_recibo': int, 'fecha_pago': date} | None}
    valor_cuota : float — cuota mensual vigente (para calcular deuda)

    Retorna: bytes del PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=1.5 * cm, bottomMargin=2 * cm,
        title=f'Recibo N° {pago.numero_recibo:04d}',
    )

    story = []
    nombre_socio = f'{socio.nombre} {socio.apellido}'
    meses_str = ', '.join(f'{MESES_ES[pm.mes]} {pm.anio}' for pm in pago.meses)
    metodo_str = 'Efectivo' if pago.metodo == 'efectivo' else 'Transferencia bancaria'

    # ── PÁGINA 1: RECIBO ──────────────────────────────────────────────────────
    _encabezado(story)

    story.append(Paragraph(f'RECIBO DE PAGO N° {pago.numero_recibo:04d}',
                            _estilo(18, bold=True)))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f'Buenos Aires, {pago.fecha_pago.strftime("%d/%m/%Y")}',
        _estilo(10, alignment=TA_RIGHT),
    ))
    story.append(Spacer(1, 0.5 * cm))

    filas = [
        ['Recibí de:', nombre_socio],
        ['La suma de:', f'$ {pago.monto:,.2f}'],
        ['En concepto de:', f'Cuota social — {meses_str}'],
        ['Forma de pago:', metodo_str],
    ]
    if pago.notas:
        filas.append(['Observaciones:', pago.notas])

    tbl = Table(filas, colWidths=[4 * cm, 13 * cm])
    tbl.setStyle(TableStyle([
        ('FONTNAME',     (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME',     (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE',     (0, 0), (-1, -1), 11),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',   (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 7),
        ('ROWBACKGROUNDS',(0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
        ('BOX',          (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('INNERGRID',    (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 2.5 * cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 2.5 * cm))

    firma_data = [
        ['________________________', '________________________'],
        ['Firma del socio', 'Tesorero / Firma y sello'],
    ]
    firma_tbl = Table(firma_data, colWidths=[8.5 * cm, 8.5 * cm])
    firma_tbl.setStyle(TableStyle([
        ('ALIGN',    (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('TOPPADDING',(0, 0), (-1, -1), 4),
    ]))
    story.append(firma_tbl)

    # ── PÁGINA 2: ESTADO DE CUENTA ────────────────────────────────────────────
    story.append(PageBreak())
    _encabezado(story)

    story.append(Paragraph('ESTADO DE CUENTA', _estilo(18, bold=True)))
    story.append(Spacer(1, 0.3 * cm))

    estilo_cuerpo = _estilo(11, alignment=TA_CENTER.__class__.__mro__[0])  # reuse
    story.append(Paragraph(
        f'<b>Socio:</b> {nombre_socio}',
        ParagraphStyle('cb', fontSize=11, leading=16, spaceAfter=4),
    ))

    hoy = date.today()
    meses_ord = sorted(historial.keys())
    if meses_ord:
        p0 = meses_ord[0]
        story.append(Paragraph(
            f'<b>Período:</b> {MESES_ES[p0[1]]} {p0[0]} — {MESES_ES[hoy.month]} {hoy.year}',
            ParagraphStyle('cb2', fontSize=11, leading=16, spaceAfter=8),
        ))

    # Tabla de meses
    tabla_data = [['Período', 'N° Recibo', 'Fecha de Pago', 'Estado']]
    meses_adeudados_count = 0

    for (y, m) in meses_ord:
        info = historial[(y, m)]
        periodo = f'{MESES_ES[m]} {y}'
        if info:
            nro = f'{info["numero_recibo"]:04d}'
            fecha = info['fecha_pago'].strftime('%d/%m/%Y')
            estado = 'PAGADO'
        else:
            nro = '—'
            fecha = '—'
            estado = 'PENDIENTE'
            meses_adeudados_count += 1
        tabla_data.append([periodo, nro, fecha, estado])

    monto_adeudado = meses_adeudados_count * valor_cuota
    tabla_data.append(['', '', 'TOTAL ADEUDADO', f'$ {monto_adeudado:,.2f}'])

    n = len(tabla_data)
    tbl_est = Table(tabla_data, colWidths=[4 * cm, 3.5 * cm, 4.5 * cm, 5 * cm],
                    repeatRows=1)

    ts = [
        ('BACKGROUND',    (0, 0), (-1, 0), COLOR_ROJO),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('BOX',           (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, colors.lightgrey),
        # Fila de totales
        ('FONTNAME',      (0, n - 1), (-1, n - 1), 'Helvetica-Bold'),
        ('BACKGROUND',    (0, n - 1), (-1, n - 1), colors.HexColor('#f2f2f2')),
    ]

    for i, (y, m) in enumerate(meses_ord, start=1):
        info = historial[(y, m)]
        if info:
            bg = colors.HexColor('#d5f5e3')  # verde claro
        elif (y, m) == (hoy.year, hoy.month):
            bg = colors.HexColor('#fef9e7')  # amarillo (mes actual)
        else:
            bg = colors.HexColor('#fadbd8')  # rojo claro (vencido)
        ts.append(('BACKGROUND', (0, i), (-1, i), bg))

    tbl_est.setStyle(TableStyle(ts))
    story.append(tbl_est)
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f'Documento generado el {hoy.strftime("%d/%m/%Y")}',
        ParagraphStyle('pie', fontSize=8, textColor=colors.grey, alignment=TA_CENTER),
    ))

    doc.build(story)
    return buffer.getvalue()
