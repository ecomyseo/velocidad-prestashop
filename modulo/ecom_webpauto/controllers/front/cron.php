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
 * Tarea programada opcional: crea los WebP que falten (imágenes subidas por FTP, importaciones...). Con token.
 */
class Ecom_WebpautoCronModuleFrontController extends ModuleFrontController
{
    public $auth = false;
    public $guestAllowed = true;
    public $ssl = true;

    public function initContent()
    {
        header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
        header('Pragma: no-cache');
        header('Expires: 0');
        $token = (string) Tools::getValue('token');
        $bueno = (string) Configuration::getGlobalValue('ECOMWEBP_TOKEN');
        if ($bueno === '' || !hash_equals($bueno, $token)) {
            http_response_code(403);
            exit('Acceso denegado');
        }
        Configuration::updateGlobalValue('ECOMWEBP_ULTIMO', time());
        $r = $this->module->generar(50);
        exit(sprintf('ok creados=%d rehechos=%d sin_ventaja=%d errores=%d vistos=%d pendientes=%s',
            (int) $r['creados'], (int) $r['rehechos'], (int) $r['sin_ventaja'], (int) $r['errores'], (int) $r['vistos'], $r['pendientes'] ? 'si' : 'no'));
    }
}
