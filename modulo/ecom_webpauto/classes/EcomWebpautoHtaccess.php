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
 * Bloque del .htaccess que entrega X.webp a quien pide X.jpg / X.png y acepta WebP (con «Vary: Accept»).
 * Va ENCIMA del bloque de PrestaShop: PrestaShop conserva lo que hay fuera de sus marcas al regenerar el fichero,
 * y además el módulo lo repone en actionHtaccessCreate y al entrar en su configuración.
 */
class EcomWebpautoHtaccess
{
    const INICIO = '# ~~ecom_webpauto start~~';
    const FIN = '# ~~ecom_webpauto end~~';

    public static function ruta()
    {
        return _PS_ROOT_DIR_ . '/.htaccess';
    }

    public static function bloque()
    {
        return implode("\n", array(
            self::INICIO . ' (Ecom Experts: entrega la copia .webp a los navegadores que la aceptan)',
            '<IfModule mod_rewrite.c>',
            'RewriteEngine on',
            'RewriteCond %{HTTP_ACCEPT} image/webp',
            'RewriteCond %{REQUEST_FILENAME} ^(.+)\.(jpe?g|png)$ [NC]',
            'RewriteCond %1.webp -f',
            'RewriteRule ^(.+)\.(jpe?g|png)$ $1.webp [NC,T=image/webp,E=ECOMWEBP:1,L]',
            '</IfModule>',
            '<IfModule mod_headers.c>',
            'Header merge Vary Accept env=ECOMWEBP',
            'Header merge Vary Accept env=REDIRECT_ECOMWEBP',
            '</IfModule>',
            '<IfModule mod_mime.c>',
            'AddType image/webp .webp',
            '</IfModule>',
            self::FIN,
        )) . "\n";
    }

    public static function puesto()
    {
        $f = self::ruta();
        if (!is_file($f)) {
            return false;
        }
        $c = (string) @file_get_contents($f);

        return strpos($c, self::INICIO) !== false && strpos($c, 'RewriteCond %1.webp -f') !== false;
    }

    /**
     * @return bool true si el bloque queda puesto
     */
    public static function poner()
    {
        $f = self::ruta();
        if (!is_file($f) || !is_writable($f)) {
            return false;
        }
        $actual = (string) file_get_contents($f);
        $sinBloque = self::sinBloque($actual);
        $nuevo = self::bloque() . "\n" . ltrim($sinBloque, "\n");
        if ($nuevo === $actual) {
            return true;
        }
        self::copia($actual);
        if (file_put_contents($f, $nuevo, LOCK_EX) === false) {
            return false;
        }

        return self::puesto();
    }

    public static function quitar()
    {
        $f = self::ruta();
        if (!is_file($f) || !is_writable($f)) {
            return false;
        }
        $actual = (string) file_get_contents($f);
        if (strpos($actual, self::INICIO) === false) {
            return true;
        }
        self::copia($actual);

        return file_put_contents($f, ltrim(self::sinBloque($actual), "\n"), LOCK_EX) !== false;
    }

    private static function sinBloque($texto)
    {
        $i = strpos($texto, self::INICIO);
        $j = strpos($texto, self::FIN);
        if ($i === false || $j === false || $j < $i) {
            return $texto;
        }
        $j += strlen(self::FIN);
        if (substr($texto, $j, 1) === "\n") {
            ++$j;
        }

        return substr($texto, 0, $i) . substr($texto, $j);
    }

    /**
     * Copia del .htaccess antes de tocarlo, en logs/ del módulo (protegida contra la descarga). Se guardan las 10 últimas.
     */
    private static function copia($contenido)
    {
        $dir = _PS_MODULE_DIR_ . 'ecom_webpauto/logs/';
        if (!is_dir($dir) || !is_writable($dir)) {
            return;
        }
        @file_put_contents($dir . 'htaccess-' . date('Ymd-His') . '.bak', $contenido);
        $copias = glob($dir . 'htaccess-*.bak');
        if (is_array($copias) && count($copias) > 10) {
            sort($copias);
            foreach (array_slice($copias, 0, count($copias) - 10) as $vieja) {
                @unlink($vieja);
            }
        }
    }

    /**
     * Pide al propio servidor una imagen que ya tiene su .webp, diciendo que acepta WebP, y mira qué devuelve.
     *
     * @return array|null url, ok, tipo, codigo (null si no hay ninguna imagen con WebP para probar)
     */
    public static function probar(array $carpetas)
    {
        if (!function_exists('curl_init')) {
            return null;
        }
        $muestra = null;
        foreach ($carpetas as $carpeta) {
            foreach (EcomWebpautoGenerador::ficheros(_PS_ROOT_DIR_, $carpeta, false) as $f) {
                $d = EcomWebpautoGenerador::destino($f);
                if ($d !== null && is_file($d) && filemtime($d) >= filemtime($f)) {
                    $muestra = $f;
                    break 2;
                }
            }
        }
        if ($muestra === null) {
            return null;
        }
        $rel = ltrim(str_replace('\\', '/', substr($muestra, strlen(_PS_ROOT_DIR_))), '/');
        $url = Context::getContext()->shop->getBaseURL(true) . implode('/', array_map('rawurlencode', explode('/', $rel)));
        $curl = curl_init($url);
        if ($curl === false) {
            return null;
        }
        curl_setopt($curl, CURLOPT_NOBODY, true);
        curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($curl, CURLOPT_FOLLOWLOCATION, false);
        curl_setopt($curl, CURLOPT_TIMEOUT, 5);
        curl_setopt($curl, CURLOPT_CONNECTTIMEOUT, 3);
        curl_setopt($curl, CURLOPT_HTTPHEADER, array('Accept: image/avif,image/webp,image/*,*/*;q=0.8', 'Cache-Control: no-cache'));
        curl_exec($curl);
        $codigo = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
        $tipo = (string) curl_getinfo($curl, CURLINFO_CONTENT_TYPE);
        curl_close($curl);

        return array('url' => $url, 'codigo' => $codigo, 'tipo' => $tipo, 'ok' => $codigo === 200 && stripos($tipo, 'image/webp') !== false);
    }
}
