<?php
/**
 * Ecom Experts
 *
 * NOTICE OF LICENSE
 *
 * This source file is subject to the Academic Free License version 3.0 (AFL-3.0)
 * that is bundled with this package in the file LICENSE.txt.
 * https://opensource.org/licenses/AFL-3.0
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   https://opensource.org/licenses/AFL-3.0 Academic Free License version 3.0
 */
if (!defined('_PS_VERSION_')) {
    exit;
}

/**
 * Crea X.webp junto a cada X.jpg / X.png de las carpetas vigiladas cuando falta o es más viejo que su imagen.
 * Nunca borra ni modifica la imagen original. Las fotos de producto (img/p) solo si se pide expresamente.
 */
class EcomWebpautoGenerador
{
    /** Imágenes más grandes que esto (megapíxeles) no se convierten: no caben en memoria con seguridad */
    const MAX_MEGAPIXELES = 40;

    /**
     * Convierte el texto de la configuración en carpetas. «img/*» = solo esa carpeta, sin subcarpetas.
     *
     * @param string $texto
     *
     * @return array lista de array('ruta' => 'img/cms', 'recursiva' => true)
     */
    public static function carpetas($texto)
    {
        $lista = array();
        foreach (preg_split('/\R/', (string) $texto) as $linea) {
            $linea = trim(str_replace('\\', '/', $linea));
            if ($linea === '' || $linea === '-' || $linea[0] === '#' || strpos($linea, '..') !== false) {
                continue;
            }
            $recursiva = true;
            if (substr($linea, -2) === '/*') {
                $recursiva = false;
                $linea = substr($linea, 0, -2);
            }
            $linea = trim($linea, '/');
            if ($linea !== '' && preg_match('#^[A-Za-z0-9_./-]+$#', $linea)) {
                $lista[$linea . ($recursiva ? '' : '/*')] = array('ruta' => $linea, 'recursiva' => $recursiva);
            }
        }

        return array_values($lista);
    }

    /**
     * Ficheros JPG/PNG de una carpeta (sin las fotos de producto, salvo que se pidan).
     *
     * @return array rutas absolutas
     */
    public static function ficheros($raiz, array $carpeta, $productos)
    {
        $dir = rtrim($raiz, '/') . '/' . $carpeta['ruta'];
        $salida = array();
        if (!is_dir($dir)) {
            return $salida;
        }
        $prodDir = rtrim($raiz, '/') . '/img/p/';
        if ($carpeta['recursiva']) {
            $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS));
            foreach ($it as $f) {
                if ($f->isFile()) {
                    $salida[] = $f->getPathname();
                }
            }
        } else {
            $glob = glob($dir . '/*');
            foreach (is_array($glob) ? $glob : array() as $f) {
                if (is_file($f)) {
                    $salida[] = $f;
                }
            }
        }
        $buenas = array();
        $prodDir = str_replace('\\', '/', $prodDir);
        foreach ($salida as $f) {
            $f = str_replace('\\', '/', $f);
            if (!preg_match('/\.(jpe?g|png)$/i', $f)) {
                continue;
            }
            if (strpos($f, $prodDir) === 0) {
                // fotos de producto: solo si se pide, y nunca la original subida (img/p/1/2/123.jpg)
                if (!$productos || preg_match('#/\d+\.jpg$#', $f)) {
                    continue;
                }
            }
            $buenas[] = $f;
        }

        return $buenas;
    }

    /**
     * X.jpg -> X.webp. Devuelve null si hay otra imagen con el mismo nombre y otra extensión (logo.jpg y logo.png).
     */
    public static function destino($f)
    {
        static $listados = array();
        $f = str_replace('\\', '/', $f);
        $dir = dirname($f);
        if (!isset($listados[$dir])) {
            if (count($listados) > 500) {
                $listados = array();
            }
            $nombres = @scandir($dir);
            $listados[$dir] = is_array($nombres) ? array_flip($nombres) : array();
        }
        // se compara la lista real de la carpeta: en un disco que no distingue mayúsculas, is_file('x.JPG') miente
        $base = preg_replace('/\.(jpe?g|png)$/i', '', basename($f));
        $hermanas = 0;
        foreach (array('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG', '.Jpg', '.Png') as $e) {
            if (isset($listados[$dir][$base . $e])) {
                ++$hermanas;
            }
        }

        return $hermanas > 1 ? null : $dir . '/' . $base . '.webp';
    }

    /**
     * Crea los que faltan o han quedado viejos, con tope de tiempo.
     *
     * @return array creados, rehechos, errores, pendientes, vistos
     */
    public static function procesar($raiz, array $carpetas, $calidad, $segundos, $productos)
    {
        $r = array('vistos' => 0, 'creados' => 0, 'rehechos' => 0, 'sin_ventaja' => 0, 'errores' => 0, 'pendientes' => false);
        if (!function_exists('imagewebp')) {
            $r['errores'] = 1;

            return $r;
        }
        $fin = microtime(true) + max(0, (int) $segundos);
        $calidad = max(40, min(100, (int) $calidad ?: 82));
        $omitidas = self::omitidas();
        $cambiadas = false;
        foreach (self::conProductos($carpetas, $productos) as $carpeta) {
            foreach (self::ficheros($raiz, $carpeta, $productos) as $f) {
                ++$r['vistos'];
                $d = self::destino($f);
                if ($d === null) {
                    continue;
                }
                $mt = filemtime($f);
                $existe = is_file($d);
                if (($existe && filemtime($d) >= $mt) || (isset($omitidas[$f]) && $omitidas[$f] === $mt)) {
                    continue;
                }
                if (microtime(true) > $fin) {
                    $r['pendientes'] = true;
                    break 2;
                }
                $res = self::convertir($f, $d, $calidad);
                if ($res === 'sin_ventaja') {
                    // pesaría más que la imagen: no se crea, y si había uno viejo (de otra imagen) se quita
                    if ($existe) {
                        @unlink($d);
                    }
                    $omitidas[$f] = $mt;
                    $cambiadas = true;
                    ++$r['sin_ventaja'];
                } elseif ($res) {
                    ++$r[$existe ? 'rehechos' : 'creados'];
                } else {
                    ++$r['errores'];
                }
            }
        }
        if ($cambiadas) {
            self::omitidas($omitidas);
        }

        return $r;
    }

    /**
     * Imágenes cuyo WebP pesaría más que ellas: no se reintentan hasta que la imagen cambie (se guarda su fecha).
     *
     * @param array|null $guardar si se pasa, se guarda
     *
     * @return array ruta => fecha de la imagen
     */
    public static function omitidas($guardar = null)
    {
        if (!defined('_PS_MODULE_DIR_')) {
            return array();
        }
        $f = _PS_MODULE_DIR_ . 'ecom_webpauto/logs/sin_ventaja.json';
        if (is_array($guardar)) {
            foreach ($guardar as $ruta => $fecha) {
                if (!is_file($ruta)) {
                    unset($guardar[$ruta]);
                }
            }
            @file_put_contents($f, json_encode($guardar), LOCK_EX);

            return $guardar;
        }
        $datos = is_file($f) ? json_decode((string) @file_get_contents($f), true) : null;

        return is_array($datos) ? $datos : array();
    }

    /**
     * Recuento por carpeta para la pantalla del módulo.
     */
    public static function contar($raiz, array $carpetas, $productos)
    {
        $filas = array();
        $omitidas = self::omitidas();
        foreach (self::conProductos($carpetas, $productos) as $carpeta) {
            $fila = array('carpeta' => $carpeta['ruta'] . ($carpeta['recursiva'] ? '' : '/*'), 'existe' => is_dir(rtrim($raiz, '/') . '/' . $carpeta['ruta']),
                'imagenes' => 0, 'con_webp' => 0, 'sin_ventaja' => 0, 'faltan' => 0, 'kb_imagen' => 0, 'kb_webp' => 0);
            foreach (self::ficheros($raiz, $carpeta, $productos) as $f) {
                ++$fila['imagenes'];
                $d = self::destino($f);
                if ($d !== null && is_file($d) && filemtime($d) >= filemtime($f)) {
                    ++$fila['con_webp'];
                    $fila['kb_imagen'] += filesize($f) / 1024;
                    $fila['kb_webp'] += filesize($d) / 1024;
                } elseif ($d === null || (isset($omitidas[$f]) && $omitidas[$f] === filemtime($f))) {
                    // no compensa, o hay otra imagen con el mismo nombre (logo.jpg y logo.png): no es que falte
                    ++$fila['sin_ventaja'];
                } else {
                    ++$fila['faltan'];
                }
            }
            $fila['kb_imagen'] = (int) $fila['kb_imagen'];
            $fila['kb_webp'] = (int) $fila['kb_webp'];
            $filas[] = $fila;
        }

        return $filas;
    }

    private static function conProductos(array $carpetas, $productos)
    {
        if ($productos) {
            $carpetas[] = array('ruta' => 'img/p', 'recursiva' => true);
        }

        return $carpetas;
    }

    /**
     * Convierte con GD, conservando la transparencia. Escribe a un temporal y lo renombra: nunca queda un WebP a medias.
     * Si el WebP pesa casi lo mismo que la imagen se prueba con 10 puntos menos de calidad (no menos de 60); si aun así
     * pesa lo mismo o más, no se crea: devuelve 'sin_ventaja'.
     *
     * @return bool|string true creado, false error, 'sin_ventaja'
     */
    public static function convertir($origen, $destino, $calidad)
    {
        $info = @getimagesize($origen);
        if (!is_array($info) || $info[0] * $info[1] > self::MAX_MEGAPIXELES * 1000000) {
            return false;
        }
        $im = @imagecreatefromstring((string) @file_get_contents($origen));
        if (!$im) {
            return false;
        }
        if (!imageistruecolor($im)) {
            imagepalettetotruecolor($im);
        }
        imagealphablending($im, false);
        imagesavealpha($im, true);
        $tmp = $destino . '.ecomtmp';
        $peso = (int) filesize($origen);
        $ok = @imagewebp($im, $tmp, (int) $calidad);
        clearstatcache(true, $tmp);
        if ($ok && is_file($tmp) && filesize($tmp) >= $peso * 0.95 && $calidad > 60) {
            $ok = @imagewebp($im, $tmp, max(60, (int) $calidad - 10));
            clearstatcache(true, $tmp);
        }
        unset($im);
        if (!$ok || !is_file($tmp) || filesize($tmp) < 26) {
            @unlink($tmp);

            return false;
        }
        if (filesize($tmp) >= $peso) {
            @unlink($tmp);

            return 'sin_ventaja';
        }
        if (!@rename($tmp, $destino)) {
            @unlink($tmp);

            return false;
        }
        @chmod($destino, 0644);

        return true;
    }
}
