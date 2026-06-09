"""
RF19 — Exportación de reportes de uso (CSV/Excel y PDF).

Genera un reporte de uso del gimnasio: por bloque horario, cuántas reservas
hubo y su estado. CSV se abre en Excel; el PDF usa reportlab.
"""
import csv
import io
from django.http import HttpResponse
from rest_framework.decorators import api_view

from .db import get_db


def _build_rows():
    """Filas del reporte: una por bloque con conteos por estado."""
    db = get_db()
    rows = []
    for s in db.slots.find().sort('slotId', 1):
        sid = s['slotId']
        rows.append({
            'bloque': s['hour'],
            'cupos_totales': s['total'],
            'disponibles': s['available'],
            'activas': db.reservations.count_documents({'slotId': sid, 'estado': 'ACTIVA'}),
            'completadas': db.reservations.count_documents({'slotId': sid, 'estado': 'COMPLETADA'}),
            'canceladas': db.reservations.count_documents({'slotId': sid, 'estado': 'CANCELADA'}),
            'no_show': db.reservations.count_documents({'slotId': sid, 'estado': 'NO_SHOW'}),
            'en_espera': db.waitlist.count_documents({'slotId': sid}),
        })
    return rows


@api_view(['GET'])
def usage_csv(request):
    rows = _build_rows()
    headers = ['bloque', 'cupos_totales', 'disponibles', 'activas',
               'completadas', 'canceladas', 'no_show', 'en_espera']
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    resp = HttpResponse(buf.getvalue(), content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="reporte_uso_gimnasio.csv"'
    return resp


@api_view(['GET'])
def usage_pdf(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    rows = _build_rows()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title='Reporte de uso')
    styles = getSampleStyleSheet()
    elems = [Paragraph('Reporte de uso — Gimnasio UdeM', styles['Title']), Spacer(1, 0.5 * cm)]

    headers = ['Bloque', 'Totales', 'Disp.', 'Activas', 'Compl.', 'Cancel.', 'No-Show', 'Espera']
    data = [headers] + [
        [r['bloque'], r['cupos_totales'], r['disponibles'], r['activas'],
         r['completadas'], r['canceladas'], r['no_show'], r['en_espera']]
        for r in rows
    ]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CC0000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F4F6')]),
    ]))
    elems.append(table)
    doc.build(elems)

    resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="reporte_uso_gimnasio.pdf"'
    return resp
