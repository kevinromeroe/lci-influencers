# Reporte de campaña de influencers · LCI Bogotá

Reporte web de las publicaciones pagas de influencers de **LCI Bogotá**, con PDF descargable por pestaña.
Ejecutor: Datalítica. Publicado en `https://influencermarketing.datalitica.com.co` (GitHub Pages).

## Qué muestra

| Pestaña | Contenido |
|---|---|
| **Todas las publicaciones** | Lo mismo que respondía el PPT de Runway: indicadores totales, resultados por red, influencers por EMV y publicaciones por EMV |
| **Una por influencer** | Indicadores, conclusiones, reel de LCI frente a sus últimos reels y conversación |

Cada campaña vive en su carpeta (`/2026-10/`) y la raíz `/` redirige a la más reciente.
Cada pestaña tiene su PDF en `/<campaña>/pdf/<pestaña>.pdf`, que baja el botón **Descargar PDF**.

## Fórmulas

Todas se calculan una sola vez en [`pipeline/metrics.py`](pipeline/metrics.py); la plantilla solo las formatea.

- **EMV** = me gusta × $7.200 + comentarios × $10.500 + compartidos × $12.350 + guardados × $13.560 (benchmark de LCI, en [`config/cliente.yaml`](config/cliente.yaml)).
- **ROI** = (EMV − inversión) ÷ inversión. La inversión de cada publicación es el valor para LCI del talento ÷ su número de salidas. CPV = inversión ÷ reproducciones; CPE = inversión ÷ interacciones. Sin ese valor, la tarjeta muestra "—".
- **Engagement** = (me gusta + comentarios) ÷ reproducciones.
- **Frente a su contenido habitual** = reproducciones del reel de LCI ÷ mediana de los otros reels recientes del influencer, sin contar los fijados.

## Flujo

```
config/campanas/<id>.yaml        influencers, publicaciones, pagos y textos curados
datos/capturas/<id>/<fecha>.json captura leída de Instagram con Claude en Chrome (solo local)
   ▼
scripts/build_reporte.py         métricas (pipeline/metrics.py) + templates/reporte.html   ← en local
   ▼
<id>/index.html                  se revisa en local y se sube con Commit + Push
   │  workflow "Pruebas + PDF"   pruebas de cuadre + PDF por pestaña (Playwright)
   ▼
<id>/pdf/*.pdf  →  GitHub Pages
```

La captura (con los comentarios y sus usuarios) nunca se sube al repo público: el sitio publicado solo lleva las cifras y el top 3 de comentarios.

## Estructura

```
config/cliente.yaml          valores de EMV, reglas, benchmark de industria (vacío)
config/campanas/<id>.yaml    una campaña por archivo
pipeline/metrics.py          cálculo único de todas las cifras
templates/reporte.html       plantilla aprobada (pestañas, indicadores, gráficos)
scripts/build_reporte.py     genera el HTML de cada campaña
scripts/render_pdf.py        genera los PDF
tests/test_metrics.py        pruebas de cuadre contra las fichas aprobadas
supabase/schema.sql          esquema de la base (etapa de ingesta)
assets/avatars/              fotos de perfil de los influencers
docs/RUNBOOK.md              operación paso a paso
```

## Correr en local

```bash
pip install -r requirements.txt
python -m unittest discover tests
python scripts/build_reporte.py
python -m http.server 8000      # abrir http://localhost:8000/
```
