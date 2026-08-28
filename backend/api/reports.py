"""
RF19/RF20 — Exportación de reportes (CSV/Excel y PDF).

RF20 — `daily_pdf` genera el REPORTE GENERAL DIARIO imprimible con el total de
asistencias, cancelaciones e inasistencias y los estudiantes penalizados.

El reporte es POR ESTUDIANTE (por persona, no por bloque horario): una fila por
estudiante con sus reservas, asistencias, cancelaciones e inasistencias.
CSV se abre en Excel; el PDF usa reportlab.
"""
import csv
import io
from django.http import HttpResponse, JsonResponse
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


# ── RF20 / P20 / HU19-HU20 — REPORTE GENERAL DIARIO EN PDF ─────────────────
@api_view(['GET'])
def daily_pdf(request):
    """Genera el reporte general diario en PDF para imprimirlo.

    Incluye el total de asistencias, cancelaciones e inasistencias del día y
    el listado de estudiantes penalizados. Solo entrenadores y administradores.
    Parámetros: ?actor_email=coach@udem.edu.co&fecha=2026-08-18 (fecha opcional).
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    from .attendance import _actor_staff, build_daily_report
    from .db import hoy_local

    if not _actor_staff(request.query_params.get('actor_email')):
        return JsonResponse(
            {'error': 'Solo un entrenador o administrador puede generar el reporte general.'},
            status=403,
        )

    fecha = (request.query_params.get('fecha') or '').strip() or hoy_local().isoformat()
    rep = build_daily_report(fecha)
    t = rep['totales']

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Reporte diario {rep['fecha']}")
    styles = getSampleStyleSheet()
    elems = [
        Paragraph('Reporte general diario — Gimnasio UdeM', styles['Title']),
        Paragraph(rep['fecha_label'].capitalize(), styles['Heading3']),
        Spacer(1, 0.5 * cm),
    ]

    # Totales del día (RF20).
    resumen = Table([
        ['Asistencias', 'Cancelaciones', 'Inasistencias', 'Estudiantes penalizados'],
        [t['asistencias'], t['cancelaciones'], t['inasistencias'], t['estudiantes_penalizados']],
    ], colWidths=[4.2 * cm] * 4)
    resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#CC0000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 20),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
        ('TOPPADDING', (0, 1), (-1, 1), 10),
    ]))
    elems += [resumen, Spacer(1, 0.7 * cm)]

    def _seccion(titulo, filas, columnas, extractor):
        elems.append(Paragraph(titulo, styles['Heading3']))
        if not filas:
            elems.append(Paragraph('Sin registros.', styles['Normal']))
        else:
            tabla = Table([columnas] + [extractor(f) for f in filas], repeatRows=1)
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FAFAFA')]),
            ]))
            elems.append(tabla)
        elems.append(Spacer(1, 0.5 * cm))

    persona = ['Estudiante', 'Documento', 'Hora']
    _seccion(f"Asistencias ({t['asistencias']})", rep['asistencias'], persona,
             lambda f: [f['name'], f['documento'], f['hour']])
    _seccion(f"Cancelaciones ({t['cancelaciones']})", rep['cancelaciones'], persona,
             lambda f: [f['name'], f['documento'], f['hour']])
    _seccion(f"Inasistencias ({t['inasistencias']})", rep['inasistencias'], persona,
             lambda f: [f['name'], f['documento'], f['hour']])
    _seccion(f"Estudiantes penalizados ({t['estudiantes_penalizados']})", rep['penalizados'],
             ['Estudiante', 'Documento', 'Inasistencias', 'Penalizado hasta'],
             lambda f: [f['name'], f['documento'], f['no_show_count'], f['penalizado_hasta'] or '—'])

    doc.build(elems)
    resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
    resp['Content-Disposition'] = f"inline; filename=\"reporte_diario_{rep['fecha']}.pdf\""
    return resp
