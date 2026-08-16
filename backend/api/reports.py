"""
RF19 — Exportación del reporte de uso (CSV/Excel y PDF).

El reporte es POR ESTUDIANTE (por persona, no por bloque horario): una fila por
estudiante con sus reservas, asistencias, cancelaciones e inasistencias.
CSV se abre en Excel; el PDF usa reportlab.
"""
import csv
import io
from django.http import HttpResponse
from rest_framework.decorators import api_view

from .features import build_student_rows

HEADERS = ['name', 'email', 'estado', 'activas', 'completadas',
           'canceladas', 'no_show', 'cancelaciones_restantes']


@api_view(['GET'])
def usage_csv(request):
    rows = build_student_rows()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=HEADERS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    resp = HttpResponse(buf.getvalue(), content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="reporte_estudiantes_gimnasio.csv"'
    return resp


@api_view(['GET'])
def usage_pdf(request):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    rows = build_student_rows()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), title='Reporte por estudiante')
    styles = getSampleStyleSheet()
    elems = [Paragraph('Reporte por estudiante — Gimnasio UdeM', styles['Title']), Spacer(1, 0.5 * cm)]

    headers = ['Estudiante', 'Correo', 'Estado', 'Activas', 'Asistió',
               'Canceladas', 'No-Show', 'Cancel. restantes']
    data = [headers] + [
        [r['name'], r['email'], r['estado'], r['activas'], r['completadas'],
         r['canceladas'], r['no_show'], r['cancelaciones_restantes']]
        for r in rows
    ]
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CC0000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F4F4F6')]),
    ]))
    elems.append(table)
    doc.build(elems)

    resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="reporte_estudiantes_gimnasio.pdf"'
    return resp
