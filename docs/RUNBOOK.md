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

## Actualizar las interacciones (dos veces por semana)

### Reglas (validadas por Kevin, 13 nov 2026)

- Las campañas **no se congelan**: se actualizan aunque el cliente las haya aprobado.
- Una cifra de una publicación **solo se actualiza si sube**; si la lectura es menor se conserva la anterior.
- Instagram muestra los me gusta **redondeados** desde ~1.000 (`4.9K`). La cifra redondeada se usa solo si es **mayor** que la exacta anterior y el reporte la muestra con **«≈»** (`aprox` en la captura).
- Los **compartidos** de Instagram se leen en pantalla y suman al EMV.
- Los **seguidores** reflejan la cuenta hoy (pueden bajar).
- **Nada se borra**; una publicación nueva se agrega primero en `config/campanas/<id>.yaml`.
- Textos curados (`why`, `cause`, `talk`) se mantienen; los nuevos los escribe Claude.
- Todo esto vive en `scripts/actualizar_cifras.py` y lo prueba `tests/test_actualizar.py`. Las pruebas de cuadre (`tests/test_metrics.py`) siguen leyendo la ficha aprobada `datos/capturas/2026-10/2026-11-04.json`.

### Fuentes

| Red | Qué | Cómo |
|---|---|---|
| Instagram | me gusta, comentarios, compartidos | Pantalla con sesión: Claude en Chrome del OptiPlex, perfil `Default` (kevinromeroe). |
| Instagram | reproducciones exactas | Apify: `~/.claude/skills/levantamiento-redes/scripts/vistas_apify.py`. |
| TikTok | todo | `__UNIVERSAL_DATA_FOR_REHYDRATION__` → `statsV2` en la página del video. |
| YouTube | vistas, me gusta | Página del video en Chrome. |
| Seguidores | exactos | En el perfil, `main span[title]`. |

La API interna de Instagram (`/api/v1/media/…`) **ya no se usa**: está bloqueada desde Chrome.

### Pasos (en el OptiPlex, `~/repos/lci-influencers`, rama `actualizacion/<fecha>`)

1. **Leer las redes con Claude en Chrome** (comprobar que instagram.com tiene la sesión iniciada en el perfil de Datalítica).
   - Ritmo prudente: 5 a 10 s entre publicaciones, máximo ~40 páginas de Instagram por sesión y no más de 10 perfiles ajenos seguidos. Si aparece verificación, `/challenge` o "actividad inusual": parar, no hacer clic y avisar a Kevin.
   - Instagram, en `https://www.instagram.com/p/<código>/`, barra de acciones:

     ```js
     const s=document.querySelector('main section'); const w=document.createTreeWalker(s,5); const o=[]; let n;
     while(n=w.nextNode()){ if(n.nodeType==1&&n.tagName.toLowerCase()=='svg'&&n.getAttribute('aria-label')) o.push('['+n.getAttribute('aria-label')+']');
       else if(n.nodeType==3&&n.textContent.trim()&&!n.parentElement.closest('svg')) o.push(n.textContent.trim()); }
     o.join(' ')   // «[Like] 4.9K [Comment] 42 [Share] 363 [Save]»
     ```
   - TikTok (esperar ~6 s; la URL redirige):

     ```js
     JSON.parse(document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__').textContent)
       .__DEFAULT_SCOPE__['webapp.video-detail'].itemInfo.itemStruct.statsV2
     ```
2. **Vistas de Instagram**: `python3 ~/.claude/skills/levantamiento-redes/scripts/vistas_apify.py lci-influencers <códigos>` (respeta el tope mensual de Apify y registra el gasto).
3. **Guardar las lecturas** en `~/datos/crudos/lci-influencers/lecturas-<AAAA-MM-DD>.json`, con las cifras tal como se ven (`"4.9K"`). Formato en la cabecera de `scripts/actualizar_cifras.py`.
4. **Crear la captura**:
   ```
   .venv/bin/python scripts/actualizar_cifras.py 2026-10 ~/datos/crudos/lci-influencers/lecturas-<fecha>.json --prueba
   .venv/bin/python scripts/actualizar_cifras.py 2026-10 ~/datos/crudos/lci-influencers/lecturas-<fecha>.json
   .venv/bin/python scripts/build_reporte.py
   .venv/bin/python -m unittest discover tests
   ```
5. **Comentarios y textos**: si hay comentarios nuevos, se leen en pantalla y se clasifican (positivo, neutro, crítico, sin contar marca ni creador); revisar los textos que llevan cifras (`why`, `cause`).
6. **Mostrar la vista previa a Kevin** (servidor local) con lo que cambió frente a lo publicado. Él revisa el resultado, no la rama. Nada se publica sin su aprobación.
7. Commit, fusionar a `main` y push. El workflow "Pruebas + PDF" regenera los PDF. Verificar el sitio.

Historial: 13 nov 2026, primera actualización con este proceso (`lecturas-2026-11-13.json`; EMV 39,0 M → 44,5 M por los compartidos de Instagram).

Buenas prácticas con Instagram: pocas consultas y espaciadas; leer la página, no la API.

## Registrar el pago de un influencer

En el influencer, `value_cop` (valor para LCI del Excel) y `actions` (número de salidas). La inversión de cada publicación es `value_cop ÷ actions` (o `payment_cop` si se da explícito). Con eso salen ROI, CPV y CPE, y la nota "aún faltan N acciones por validar" se calcula sola con las salidas que falten por medir.

La inversión total y las salidas de toda la campaña van en `campaign.budget` y alimentan la tarjeta "Ejecución de la inversión".

## Verificación antes de avisar al cliente

- `python -m unittest discover tests` en verde.
- Cada pestaña abre, las fotos cargan y los PDF bajan.
- Ninguna tarjeta en cero y ningún mensaje técnico visible.

## Corrida automática (desde el 14 de noviembre de 2026)

Corre sola en el OptiPlex **lunes y jueves a las 7:00** (`~/ops/influencers/corrida.sh`, crontab). Decisión de Kevin: sin vista previa; **se publica sola si pasa el control automático** y, si no, no se publica y avisa en el resumen de WhatsApp.

1. `lista.py` arma la lista de publicaciones del reporte.
2. **Instagram va completo por Apify** (vistas, me gusta, comentarios y seguidores, `apify_ig.py`): la sesión de Instagram en Chrome pidió verificación. Apify no da compartidos: esa cifra se conserva. **TikTok y YouTube** los lee Claude en Chrome (sin sesión, nunca abre Instagram).
3. `validar_corrida.py`: se frena si se leyó menos del 80 % de las publicaciones o aparece una que no está en el reporte; una cifra que sube más de 30 % y más de 1.000 de golpe no se aplica (se conserva la anterior) y se informa.
4. `scripts/actualizar_cifras.py` aplica las reglas de este documento, pruebas, build/PDF, push y verificación en línea.
5. Si fallan las pruebas o el build, el trabajo queda en una rama `fallida/<fecha>-<repo>` y no se publica.

Esta sección reemplaza los pasos manuales de lectura por Chrome para Instagram; el resto de las reglas sigue igual.

### Candado: no publicar desde otro equipo

El reporte lo construye y publica solo el OptiPlex, porque sus capturas (`datos/`, fuera de git) son las más recientes.
`scripts/build_reporte.py` se detiene (código 2, mensaje «[ALTO]») si la captura del equipo donde corre es más vieja
que la del reporte ya construido. Lo prueba `tests/test_candado.py`.

- Desde el portátil: sube solo cambios de `config/`, `templates/` o `pipeline/`. La próxima corrida (lunes o jueves 7:00) publica.
- Si un cambio debe salir antes de la corrida: `python scripts/rearmar_desde_publicado.py .` rearma el reporte con la config y la plantilla actuales sobre las cifras publicadas por el OptiPlex (no usa la captura local). Revisa que solo cambie lo esperado antes de subir.
- `--forzar` salta el candado; úsalo solo con una razón clara (por ejemplo, el OptiPlex fuera de servicio y una captura nueva en el portátil).
- Origen: el 26-nov-2026 un build del portátil con la captura del 4-nov reemplazó las cifras del día (EMV $44,5 M → $39,0 M).
