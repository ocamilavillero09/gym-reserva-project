"""
EXPORTACIÓN DEL REPORTE GENERAL DIARIO EN PDF

REQUISITOS FUNCIONALES CUBIERTOS EN ESTE ARCHIVO
    RF20  Generación e impresión en PDF del reporte general diario, con el
          total de asistencias, cancelaciones y estudiantes penalizados.

Los datos los arma `attendance.build_daily_report`, el mismo que alimenta la
consulta en pantalla (RF19): así el PDF y el panel muestran siempre lo mismo.
Aquí solo se maqueta el documento.
"""
import io

from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view


# ── RF20 · Reporte general diario en PDF ────────────────────────────────
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
    from .reglas import hoy_local

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
