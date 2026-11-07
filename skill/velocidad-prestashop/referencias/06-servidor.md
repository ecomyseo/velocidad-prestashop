# 6. Servidor

Ajustes que han dado resultados medidos en servidores de tiendas PrestaShop (Ubuntu con Hestia o Plesk, Apache detrás
de nginx, PHP-FPM, MariaDB). Cada uno se aplica con copia y se mide antes y después (`01-metodo-seguro.md`).

## PHP

### OPcache

- **`opcache.max_accelerated_files` por debajo del número de ficheros PHP.** PrestaShop con unos cuantos módulos pasa
  de 20.000 ficheros: con el límite en 20.000, los que no caben se compilan en cada petición. Se sube a 100.000.
- **`opcache.interned_strings_buffer` lleno.** En PHP 7.4, 64 MB dan unos 47 MB útiles (el resto es la tabla interna):
  se sube a 128. Con `opcache_get_status()` se ve si está lleno.
- **`opcache.validate_timestamps=0`** hace que un fichero cambiado **no se use** hasta reiniciar PHP o invalidarlo.
  Si se deja así, todo despliegue tiene que invalidar la caché; si no, `validate_timestamps=1` con
  `revalidate_freq=2`.

### `open_basedir` y la caché de rutas

Con `open_basedir` activo, PHP **no usa la caché de rutas** (`realpath_cache_size()` devuelve 0): cada `include`
vuelve a resolver la ruta en disco. Quitarlo en un servidor dedicado a una sola tienda bajó la portada de 1,67 a
0,80 s en el servidor. Es una decisión de seguridad: se habla antes con el dueño.

### PHP-FPM

- **`pm.max_children`**: si el grupo de procesos se llena, las peticiones esperan y acaban en 502/503/504. Se mira en
  el registro de FPM («server reached pm.max_children»). Se sube según la memoria disponible.
- **`request_slowlog_timeout = 3s` y `slowlog`**: el registro de peticiones lentas con su traza. Es la herramienta que
  más rápido encuentra un módulo que espera a un servicio externo.
- En Plesk, cambiar los ajustes de PHP desde el panel **regenera el pool y quita las directivas puestas a mano**, y la
  recarga corta las peticiones en curso (503 a las que estaban a medias). Fuera de las horas de las tareas programadas.

### Versión de PHP del dominio en Hestia

Una plantilla propia de PHP-FPM con la versión **delante** del nombre (`PHP-7_4-mitienda`) puede acabar en el PHP por
defecto del servidor cuando Hestia se actualiza solo y reconstruye los dominios. Caso real: una tienda PrestaShop
1.7.8 amaneció en PHP 8.3 y dio cientos de errores fatales (el blog caído, un fallo en el carrito). Las plantillas con
la versión **al final** (`mitienda-PHP-7_4`) se mantuvieron. Tras una actualización de Hestia se comprueba que el
pool de cada dominio está en `/etc/php/<versión>/fpm/pool.d/`.

## Sesiones PHP

- En ficheros (lo normal), la sesión **se bloquea** mientras dura la petición: si un empleado del back-office tiene
  una petición lenta, todas sus otras pestañas esperan (procesos en `locks_lock_inode_wait`). Y si un módulo abre
  sesión PHP en la tienda, los visitantes también hacen cola.
- En Redis **sin bloqueo** (`redis.session.locking_enabled=0`, el valor por defecto de phpredis) desaparecen las
  colas, pero **se rompen los formularios Symfony del back-office** («The CSRF token is invalid»): dos peticiones de la
  misma sesión se pisan el token. Con Redis: `redis.session.locking_enabled=1` y `redis.session.lock_expire=60`.

## MariaDB

- **`innodb_buffer_pool_size`** ≈ datos InnoDB × 1,2, sin pasar del 40 % de la RAM si el servidor comparte con la web.
  Solo se sube, nunca se baja a ciegas.
- **Plesk:** `/etc/mysql/db-performance.cnf` («Performance Booster») se incluye **el último** y gana a cualquier
  fichero de `mariadb.conf.d/`. Caso real: fijaba 128 MB de buffer en una máquina de 128 GB con 9 GB de datos.
- **MariaDB 11.4+:** `innodb_buffer_pool_size_max` limita cuánto puede crecer en caliente; para subir más hay que
  ponerlo en la configuración y reiniciar.
- `table_open_cache` y `table_definition_cache` cortos con PrestaShop (cientos de tablas): 4.000-6.000.
- Registro de consultas lentas siempre activo (`slow_query_log=1`, `long_query_time=2`).
- Conectar la tienda por socket (`database_host` = `localhost`) en lugar de `127.0.0.1` cuando están en la misma
  máquina.
- Tablas que solo crecen (visitas, conexiones, registros de módulos): un registro de vistas de un blog sin índice
  tardaba 0,26 s por visita; con un índice en (ip, id_post), 0,03 s. Las visitas de robots de meses se pueden purgar
  con copia previa.

## Red y sistema

- **DNS lentos del proveedor.** Se han visto servidores DNS de un proveedor que tardan 1-2 s por consulta. Cada
  llamada a un servicio externo (pasarelas de pago, APIs de transporte, módulos que «llaman a casa») espera eso. Se
  mide con `dig` contra cada servidor y se ponen los rápidos delante (`/etc/systemd/resolved.conf.d/`).
- **VPS KVM: `cpuidle_haltpoll`.** En algunas máquinas virtuales, cargar el módulo `cpuidle_haltpoll` (con
  `force=1`) bajó cada ida y vuelta a MariaDB de 0,22 a 0,06 ms. Se mide antes y se deja solo si mejora un 20 % o más.
  Una máquina física no lo necesita.
- **Guiones de «limpieza» que matan procesos.** Uno que mataba cada 4 horas todo proceso con más de 3 horas de vida
  incluía MariaDB: la tienda caía un minuto cada 4 horas. Revisar el `crontab` de root.
- **Tiempos máximos muy largos** (`max_execution_time` de 3.600 s para una tarea) alargan cualquier atasco hasta una
  hora. Las tareas largas, por línea de órdenes, no por la web.
- **Memoria:** antivirus y antispam del correo que no se usan pueden ocupar más de 1 GB; una memoria de intercambio
  llena hace lento todo.

## Robots

- Los filtros del listado (`?q=`) son consultas caras y sin caché: `Disallow: /*?q=` y `Disallow: /*&q=` en
  `robots.txt` para que los buscadores no los recorran.
- Si hay una red de robots atacando los filtros, se nota en el registro: miles de IP con una sola petición cada una.

## Modo desarrollo

Antes de decir que está activado, mirar `config/defines.inc.php`: es habitual que esté condicionado a una IP
(`$_SERVER['REMOTE_ADDR'] == '...'`). Para los clientes está apagado; solo lo ve quien entra desde esa IP.
