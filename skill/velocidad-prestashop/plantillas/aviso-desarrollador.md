# Modelo de aviso al desarrollador de un módulo

Un buen aviso se arregla; uno vago se ignora. Lleva **versión exacta, traza real, cifras y lo que se pide**, y deja
claro que no se ha tocado su código (o qué se ha tocado y por qué).

---

**Asunto:** Módulo <nombre> para PrestaShop: <qué pasa, en una línea>

Hola:

Os escribimos por el módulo <nombre> instalado en una tienda que mantenemos. Hemos detectado que <síntoma que ve el
cliente>. Os pedimos que lo corrijáis en el módulo.

**Entorno**

- PrestaShop <versión>, PHP <versión> (<FPM / FastCGI>), <panel / servidor>.
- Módulo «<nombre>»: <fichero principal> declara la versión <x.y.z> (<config.xml dice ...>). Librerías: <...>.
- Configuración relevante: <claves y valores>.

**Qué pasa**

1. <Primer problema>. En <gancho>, <clase::método()> (<fichero>, línea <n>) <qué hace>. <Consecuencia>.
   Traza real, del registro de peticiones lentas de PHP-FPM (<fecha y hora>):

   ```
   curl_exec()        <ruta>:<línea>
   <método>()          <ruta>:<línea>
   ...
   ```

   Cifra: <en una hora, X de Y páginas lentas estaban esperando aquí>.
2. <Segundo problema>, con su cifra.
3. ...

**Lo que os pedimos**

1. <Arreglo concreto 1> (por ejemplo: que la llamada no bloquee la página y tenga un tiempo máximo corto, o que la
   tarea se lance solo desde un cron del servidor).
2. <Arreglo concreto 2> (por ejemplo: un bloqueo atómico en base de datos para que se ejecute una sola vez).
3. ...

Si nos indicáis una versión corregida, la probaremos. Y si mientras tanto recomendáis <solución provisional>,
decidnos cómo hacerlo sin romper <lo que el módulo tiene que seguir haciendo>.

Un saludo,
<firma>

---

## Ejemplo real resumido (módulo de pago aplazado seQura 7.0.3)

- **Qué pasa:** en `hookDisplayHeader`, `Crontab::poolCron()` llama por `curl` a la propia tienda
  (`/module/sequra/triggerreport`) y espera la respuesta, sin `CURLOPT_TIMEOUT`. La tarea «diaria» se lanzaba 461
  veces en una hora porque el candado (`SEQURA_AUTOCRON_NEXT`) se lee de la configuración ya cargada en cada
  petición. `callCron()` no evalúa la respuesta y registra «could not be sent: (200) ok» siempre (166.454 filas en
  `ps_log`). Con el grupo de PHP lleno, la tienda se bloqueaba sola.
- **Lo que se pidió:** llamada asíncrona o desde cron real; bloqueo atómico en base de datos; comprobar la respuesta;
  `CURLOPT_CONNECTTIMEOUT` y `CURLOPT_TIMEOUT` en todas las llamadas de la librería.
