# 1. Método seguro: copia, antes y después, y vuelta atrás

Una tienda es dinero de alguien. Una mejora de velocidad que rompe el carrito durante una hora cuesta más de lo que
ahorra en un año. Todo cambio sigue estos pasos, sin excepciones.

## Antes de tocar nada

1. **Pedir permiso nombrando la web y lo que se va a hacer.** «Voy a encender `mod_expires` en el servidor, afecta a
   las seis webs que aloja» es un permiso; «voy a optimizar el servidor» no lo es.
2. **Listar qué aloja el servidor.** Un servidor puede tener varias tiendas, copias y clones. Un cambio de Apache,
   nginx o PHP les afecta a todas.
3. **Copia de cada cosa que se va a tocar**, en una carpeta con fecha:
   - ficheros: `cp -p fichero /root/copias-AAAAMMDD/tarea/` (con `-p` para conservar dueño, permisos y fecha);
   - configuración de PrestaShop: un `SELECT name, value FROM ps_configuration WHERE name IN (...)` guardado;
   - estado del servidor: módulos de Apache cargados (`apache2ctl -M`), la línea del `php.ini`, el fichero del pool;
   - ficheros nuevos que se van a crear: su lista, para poder borrarlos.
4. **Escribir el `volver.sh` antes de aplicar**, con un argumento por cada parte (`volver.sh cache`,
   `volver.sh plantilla`, `volver.sh todo`). Y comprobar su sintaxis con `bash -n volver.sh`.
5. **Si la vuelta atrás la ejecuta el usuario de la web, la copia va en una carpeta suya**, no en `/root`: si no
   puede leerla, la vuelta atrás falla a medias y nadie se entera.
6. **Medir el estado de partida** con el mismo guion que se usará después (ver `02-medir.md`).

## Al aplicar

- **Un cambio cada vez.** Si se cambian tres cosas a la vez y algo va peor, no se sabe cuál fue.
- **Escribir los ficheros sin pisarlos a medias**: se escribe un temporal al lado y se renombra (`mv -f`). Un
  fichero servido por nginx que se sobrescribe puede salir cortado durante un minuto.
- **Comprobar la configuración antes de recargar**: `nginx -t`, `apachectl configtest`, `php-fpm -t` (este último no
  imprime nada si está bien: mirar el código de salida).
- **El mensaje de éxito va detrás de `&&`**, nunca detrás de `;`. Un `mv ...; echo CAMBIADO` imprime «CAMBIADO»
  aunque el `mv` haya fallado.

## Después de aplicar

1. **Vaciar las cachés que tapan el cambio:** compilados de Smarty, la caché CCC del tema (`Media::clearCache()`), la
   caché de página completa si hay un módulo que la haga, y OPcache si tiene `validate_timestamps=0`.
2. **Comparar con el estado de partida, no con «todo 200».** Una imagen que ya daba 404 antes no es un fallo del
   cambio; una página que pasa de 200 a 500 sí.
3. **Errores de JavaScript:** se guarda la lista de antes y se compara. Los que ya estaban no se arreglan sin
   permiso, pero se avisan.
4. **Probar lo que toca dinero:** añadir al carrito, ver el carrito, llegar al checkout.
5. **Si algo empeora, el guion deshace solo.** Es mejor que la vuelta atrás esté dentro del propio guion de
   aplicación: si la comprobación falla, ejecuta `volver.sh` sin esperar a nadie.
6. **Medir otra vez** y anotar las dos cifras.

## Activar y desactivar para saber si algo ayuda

Una opción (CCC, `<picture>`, una precarga, `defer`) solo se deja si mejora la medida:

- Se mide con la opción y sin ella, **alternando** (A, B, A, B), con 3-5 cargas de cada una, y se compara la mediana.
- **PageSpeed no vale para esto**: la misma página sin cambios da a veces 2,1 s y a veces 3,8 s de FCP.
- Si las dos variantes salen iguales, se queda la más simple.

## Lo que se le cuenta al dueño de la tienda

- Qué se ha cambiado y en qué web.
- La cifra de antes y la de después, y cómo se ha medido.
- Dónde está la copia y la orden exacta para deshacerlo.
- Lo que se ha visto y no se ha tocado.
