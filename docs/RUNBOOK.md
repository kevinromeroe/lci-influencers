# RUNBOOK · Reporte de influencers LCI

## Roles

- **Claude** edita los archivos en el clon local (`~/Documents/GitHub/lci-influencers`) y los valida.
- **Tú** haces Commit + Push en GitHub Desktop.
- El sitio se genera y se revisa **en local** (con la captura de `datos/`) y se sube ya construido.
- El workflow **Pruebas + PDF** corre al subir un reporte: pasa las pruebas de cuadre y regenera los PDF. No reconstruye el HTML.

Sitio: `https://influencermarketing.datalitica.com.co`

## Publicar por primera vez

1. DNS de `datalitica.com.co`: registro `CNAME  influencermarketing  →  kevinromeroe.github.io`.
2. GitHub Desktop → *File → Add local repository* → `Documents/GitHub/lci-influencers`.
3. Primer commit con todos los archivos y **Publish repository** como `kevinromeroe/lci-influencers` (público, igual que SendWave, para usar GitHub Pages gratis). La carpeta `datos/` no aparece en el commit: es correcto.
4. En GitHub: *Settings → Pages → Deploy from a branch → main / (root)*. El dominio se toma del archivo `CNAME`.
5. Cuando GitHub muestre el dominio verificado: marcar *Enforce HTTPS*.

## Publicar una actualización

1. Captura nueva y `python scripts/build_reporte.py` en local.
2. Revisar `http://localhost:8811/` (o `python -m http.server`).
3. Commit + Push. El workflow regenera los PDF.

## Agregar un pedido nuevo (manual, hasta que exista la ingesta)

1. En `config/campanas/<campaña>.yaml`, agregar el influencer (o la publicación a uno existente): red, formato, fecha, enlace, tipo y `payment_cop` si ya se conoce.
2. Cargar las métricas y los últimos reels del influencer (`baseline`), y la foto de perfil en `assets/avatars/`.
3. Escribir o revisar los textos: `why`, `cause` y `talk`.
4. Correr las pruebas y el build en local; revisar el sitio.
5. Commit + Push. El workflow genera los PDF y publica.

## Actualizar las interacciones (captura con Claude en Chrome)

Los pedidos no son frecuentes, así que la actualización se hace leyendo Instagram con Claude en Chrome, sin Apify.

1. Iniciar sesión en Instagram en Chrome (lo hace la persona, nunca Claude).
2. Pedir a Claude: "actualiza las publicaciones de la campaña <id>". Claude lee:
   - de cada publicación de LCI: me gusta y comentarios exactos, y la fecha;
   - de la pestaña de reels de cada influencer: seguidores exactos, reproducciones (como las muestra Instagram, p. ej. 85.9K), fecha (sale del código de la publicación) y si está fijado;
   - todos los comentarios visibles de cada publicación de LCI, incluidas las respuestas, clasificados como positivo, neutro o crítico (sin contar los de la marca ni los del creador). El balance y el top 3 del reporte salen de ahí;
   - de los reels destacados (A, B, C): comentarios, me gusta del comentario más votado y coautores, para actualizar los textos `why`.
3. Claude guarda `datos/capturas/<id>/<AAAA-MM-DD>.json`. La carpeta `datos/` es local y no se versiona.
4. `python scripts/build_reporte.py` usa la captura más reciente; si no hay, usa los valores de la configuración.
5. Revisar los textos curados que llevan cifras (`why`, `cause`): se actualizan a mano si cambiaron.

Ventana de comparación: los últimos 12 reels no fijados publicados hasta la fecha de corte de la campaña (`campaign.corte`). Las marcas A, B, C se asignan por código de publicación en `marks`.

Buenas prácticas con Instagram: pocas consultas y espaciadas. Si responde "Please wait a few minutes" (HTTP 429), esperar y leer la página en vez de consultar la API.

## Registrar el pago de un influencer

En el influencer, `value_cop` (valor para LCI del Excel) y `actions` (número de salidas). La inversión de cada publicación es `value_cop ÷ actions` (o `payment_cop` si se da explícito). Con eso salen ROI, CPV y CPE, y la nota "aún faltan N acciones por validar" se calcula sola con las salidas que falten por medir.

La inversión total y las salidas de toda la campaña van en `campaign.budget` y alimentan la tarjeta "Ejecución de la inversión".

## Verificación antes de avisar al cliente

- `python -m unittest discover tests` en verde.
- Cada pestaña abre, las fotos cargan y los PDF bajan.
- Ninguna tarjeta en cero y ningún mensaje técnico visible.
