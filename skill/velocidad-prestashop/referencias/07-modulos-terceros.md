# 7. Módulos de terceros que frenan o tumban la tienda

## Cómo se encuentran

1. Registro de peticiones lentas de PHP-FPM (`06-servidor.md`): la traza dice qué fichero y qué línea esperaban.
2. Perfilador de PrestaShop en una copia: consultas y tiempo por módulo y por gancho.
3. Procesos de PHP en `locks_lock_inode_wait`: cola por una sesión PHP retenida.
4. Registro de accesos: una URL de un módulo que se pide cientos de veces por hora desde la IP del propio servidor.

## Patrones que se repiten

- **Llamar a un servicio externo dentro de la página.** Un `curl` síncrono en `hookDisplayHeader` (o en cualquier
  gancho del front) hace esperar a cada visitante. Sin tiempo máximo, la espera es ilimitada.
- **Llamarse a sí mismo.** Si el servicio al que llama es la propia tienda y el grupo de procesos de PHP está lleno, la
  llamada no encuentra proceso libre y espera: bloqueo mutuo, y la tienda deja de responder (504).
- **«Una vez al día» que se ejecuta cientos de veces.** Un candado guardado con `Configuration::updateValue()` no
  protege: cada petición en curso lee la configuración que cargó al empezar y sigue viendo la hora antigua. El
  candado tiene que ser atómico en la base de datos (un `UPDATE ... WHERE valor = anterior` y comprobar las filas
  afectadas).
- **Consultas producto a producto en los listados.** Un módulo de etiquetas consultaba ficha y categorías de cada
  producto aunque no hubiera ninguna etiqueta asignada: 454 consultas por página. Un atajo «si no hay asignaciones, no
  consultes nada» las dejó en 3.
- **Módulos del back-office que llaman a servicios externos al abrir una ficha** (cuentas, pagos, catálogo): si el
  servicio tarda, la ficha tarda, y las demás pestañas del empleado hacen cola tras su sesión.
- **Registros que escriben en cada visita** y llenan tablas o `ps_log` con cientos de miles de filas.

## seQura (pago aplazado): avisar al desarrollador o actualizar

Visto en una tienda real con el módulo `sequra` 7.0.3 (librería `sequra/php-client` 0.5.0) y la tarea automática
activada (`SEQURA_AUTOCRON = 1`):

- En `hookDisplayHeader`, `Crontab::poolCron()` llama por `curl` a la propia tienda (`/module/sequra/triggerreport`)
  y **espera la respuesta**. `initCurl()` no fija `CURLOPT_TIMEOUT` ni `CURLOPT_CONNECTTIMEOUT`.
- El candado (`SEQURA_AUTOCRON_NEXT` = ahora + 300 con `updateGlobalValue`) no funciona con peticiones simultáneas: la
  tarea «diaria» se lanzaba **cientos de veces por hora** (461 entre las 07:00 y las 08:00).
- `callCron()` no evalúa la respuesta: escribe siempre «could not be sent: (200) ok» en el registro de PrestaShop
  (166.454 filas en `ps_log`).
- Resultado: en una hora, 110 de las 234 páginas lentas estaban esperando a esa llamada, y un día la tienda cayó por
  bloqueo mutuo (todos los procesos de PHP esperando a otra petición de la misma tienda).

**Qué recomendar, en este orden:**

1. **Actualizar el módulo** a la última versión publicada y comprobar en el registro de peticiones lentas y en el de
   accesos (`grep -c triggerreport`) que ya no pasa.
2. **Avisar al desarrollador** con los datos: versión, traza, conteos y lo que se pide. Modelo en
   `plantillas/aviso-desarrollador.md`.
3. Mientras tanto, si el dueño lo autoriza: desactivar la tarea automática del módulo y lanzar su URL desde un `cron`
   del sistema una vez al día, **si el desarrollador confirma cómo** (puede necesitar credenciales).
4. Último recurso, con permiso y documentado: un candado atómico en base de datos dentro de `poolCron()` (como mucho
   un lanzamiento cada pocas horas). Es un cambio a un módulo de terceros: se escribe qué línea cambia, se guarda el
   original y se avisa de que **la próxima actualización del módulo lo borra**.

## Reglas al tocar un módulo de terceros

- Nunca sin copia del fichero original y sin un `README` que diga qué línea cambia y por qué.
- Comprobar que la salida es idéntica antes y después (mismo HTML, mismo `dataLayer`, mismo fichero exportado).
- Avisar al dueño de que una actualización del módulo deshace el cambio, y al desarrollador para que lo arregle.
