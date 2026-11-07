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

require_once _PS_MODULE_DIR_ . 'ecom_webpauto/classes/EcomWebpautoGenerador.php';
require_once _PS_MODULE_DIR_ . 'ecom_webpauto/classes/EcomWebpautoHtaccess.php';

class Ecom_Webpauto extends Module
{
    const CARPETAS_DEFECTO = "img/*\nimg/cms\nimg/c\nimg/m\nimg/su\nimg/st\nimg/co\nmodules/ps_imageslider/images\nmodules/ps_banner/img\nstupload\nupload";

    /** @var bool una sola revisión programada por petición */
    private static $programado = false;

    public function __construct()
    {
        $this->name = 'ecom_webpauto';
        $this->tab = 'administration';
        $this->version = '1.0.0';
        $this->author = 'Ecom Experts';
        $this->need_instance = 0;
        $this->bootstrap = true;
        $this->ps_versions_compliancy = array('min' => '1.7.6.0', 'max' => _PS_VERSION_);

        parent::__construct();

        $this->displayName = $this->trans('Automatic WebP for banners and sliders', array(), 'Modules.Ecomwebpauto.Admin');
        $this->description = $this->trans('Creates the WebP copy of every banner, slider and image that is uploaded or changed, and serves it to the browsers that accept it.', array(), 'Modules.Ecomwebpauto.Admin');
    }

    public function isUsingNewTranslationSystem()
    {
        return true;
    }

    /**
     * Module::trans() es protected y en PS 8 escapa el texto: se amplía a public y sin escapar (se escapa en la plantilla).
     */
    public function trans($id, array $parameters = array(), $domain = null, $locale = null)
    {
        return $this->getTranslator()->trans($id, $parameters, $domain, $locale);
    }

    public function install()
    {
        if (!parent::install()
            || !$this->registerHook('actionDispatcherBefore')
            || !$this->registerHook('displayBackOfficeHeader')
            || !$this->registerHook('actionHtaccessCreate')) {
            return false;
        }
        $this->valoresPorDefecto();
        if ((int) Configuration::getGlobalValue('ECOMWEBP_SERVIR')) {
            EcomWebpautoHtaccess::poner();
        }
        Configuration::updateValue('GMARTOS_LAST_PING_' . $this->name, 0);
        $this->checkGmartosUpdate();

        return true;
    }

    public function uninstall()
    {
        EcomWebpautoHtaccess::quitar();
        foreach (array('ECOMWEBP_ACTIVO', 'ECOMWEBP_SERVIR', 'ECOMWEBP_CALIDAD', 'ECOMWEBP_CARPETAS', 'ECOMWEBP_PRODUCTOS',
            'ECOMWEBP_ULTIMO', 'ECOMWEBP_TOKEN', 'ECOMWEBP_VERSION') as $clave) {
            Configuration::deleteByName($clave);
        }
        Configuration::deleteByName('GMARTOS_LAST_PING_' . $this->name);
        Configuration::deleteByName('GMARTOS_UPDATE_AVAILABLE_' . $this->name);
        Configuration::deleteByName('GMARTOS_LATEST_VERSION_' . $this->name);

        return parent::uninstall();
    }

    /**
     * Valores de fábrica. Toda la configuración es GLOBAL: los ficheros son los mismos para todas las tiendas.
     */
    private function valoresPorDefecto()
    {
        $defecto = array(
            'ECOMWEBP_ACTIVO' => 1,
            'ECOMWEBP_SERVIR' => 1,
            'ECOMWEBP_CALIDAD' => 82,
            'ECOMWEBP_CARPETAS' => self::CARPETAS_DEFECTO,
            'ECOMWEBP_PRODUCTOS' => 0,
            'ECOMWEBP_ULTIMO' => 0,
        );
        foreach ($defecto as $clave => $valor) {
            if (Configuration::getGlobalValue($clave) === false) {
                Configuration::updateGlobalValue($clave, $valor);
            }
        }
        if (!Configuration::getGlobalValue('ECOMWEBP_TOKEN')) {
            Configuration::updateGlobalValue('ECOMWEBP_TOKEN', Tools::passwdGen(32));
        }
    }

    /**
     * Migraciones al entrar en la configuración (sin ficheros upgrade/).
     */
    public function addnewfeatures()
    {
        try {
            foreach (array('actionDispatcherBefore', 'displayBackOfficeHeader', 'actionHtaccessCreate') as $gancho) {
                if (!$this->isRegisteredInHook($gancho)) {
                    $this->registerHook($gancho);
                }
            }
            $this->valoresPorDefecto();
            if ((int) Configuration::getGlobalValue('ECOMWEBP_SERVIR') && !EcomWebpautoHtaccess::puesto()) {
                EcomWebpautoHtaccess::poner();
            }
            Configuration::updateGlobalValue('ECOMWEBP_VERSION', $this->version);
        } catch (Exception $e) {
            PrestaShopLogger::addLog('ecom_webpauto addnewfeatures: ' . $e->getMessage(), 2);
        }
    }

    /**
     * Cualquier petición del back-office: si trae ficheros subidos (o hace más de 5 minutos de la última revisión),
     * se revisan las carpetas al TERMINAR la petición, cuando el módulo que recibe la imagen ya la ha guardado.
     */
    public function hookActionDispatcherBefore($params)
    {
        if (!isset($params['controller_type']) || (int) $params['controller_type'] !== (int) Dispatcher::FC_ADMIN) {
            return;
        }
        $this->programarRevision(!empty($_FILES));
    }

    public function hookDisplayBackOfficeHeader($params)
    {
        $this->programarRevision(!empty($_FILES));

        return '';
    }

    public function hookActionHtaccessCreate($params)
    {
        if ((int) Configuration::getGlobalValue('ECOMWEBP_SERVIR')) {
            EcomWebpautoHtaccess::poner();
        }
    }

    private function programarRevision($hayFicheros)
    {
        if (self::$programado || !(int) Configuration::getGlobalValue('ECOMWEBP_ACTIVO')) {
            return;
        }
        if (!$hayFicheros && time() - (int) Configuration::getGlobalValue('ECOMWEBP_ULTIMO') < 300) {
            return;
        }
        self::$programado = true;
        register_shutdown_function(array($this, 'revisarAlTerminar'), $hayFicheros ? 8 : 3);
    }

    /**
     * Se ejecuta al final de la petición. No envía nada ni cierra la respuesta: solo crea ficheros .webp.
     *
     * @param int $segundos tope de tiempo
     */
    public function revisarAlTerminar($segundos)
    {
        try {
            Configuration::updateGlobalValue('ECOMWEBP_ULTIMO', time());
            $this->generar((int) $segundos);
        } catch (Exception $e) {
            PrestaShopLogger::addLog('ecom_webpauto: ' . $e->getMessage(), 2);
        } catch (Error $e) {
            PrestaShopLogger::addLog('ecom_webpauto: ' . $e->getMessage(), 2);
        }
    }

    /**
     * @param int $segundos
     *
     * @return array recuento de lo hecho
     */
    public function generar($segundos)
    {
        return EcomWebpautoGenerador::procesar(
            _PS_ROOT_DIR_,
            EcomWebpautoGenerador::carpetas((string) Configuration::getGlobalValue('ECOMWEBP_CARPETAS')),
            (int) Configuration::getGlobalValue('ECOMWEBP_CALIDAD'),
            $segundos,
            (bool) Configuration::getGlobalValue('ECOMWEBP_PRODUCTOS')
        );
    }

    public function getContent()
    {
        $salida = '';
        if ($this->checkGmartosUpdate()) {
            $this->context->smarty->assign(array(
                'gmartos_latest_version' => Configuration::get('GMARTOS_LATEST_VERSION_' . $this->name),
            ));
            $salida .= $this->fetch('module:' . $this->name . '/views/templates/admin/gmartos_update.tpl');
        }
        $this->addnewfeatures();

        if (Tools::isSubmit('submitEcomwebpauto')) {
            $salida .= $this->guardar();
        }
        if (Tools::isSubmit('submitEcomwebpautoGenerar')) {
            $r = $this->generar(20);
            $texto = $this->trans('WebP created: %creados%, remade because their image changed: %rehechos%, left without WebP because it would weigh more: %sinventaja%, errors: %errores%.', array(
                '%creados%' => (int) $r['creados'], '%rehechos%' => (int) $r['rehechos'], '%sinventaja%' => (int) $r['sin_ventaja'], '%errores%' => (int) $r['errores'],
            ), 'Modules.Ecomwebpauto.Admin');
            if ($r['pendientes']) {
                $texto .= ' ' . $this->trans('Some are still missing: press the button again.', array(), 'Modules.Ecomwebpauto.Admin');
            }
            $salida .= $r['errores'] ? $this->displayWarning($texto) : $this->displayConfirmation($texto);
        }

        return $salida . $this->panel() . $this->formulario();
    }

    private function guardar()
    {
        $calidad = (int) Tools::getValue('ECOMWEBP_CALIDAD');
        if ($calidad < 40 || $calidad > 100) {
            $calidad = 82;
        }
        $lineas = array();
        foreach (preg_split('/\R/', (string) Tools::getValue('ECOMWEBP_CARPETAS')) as $l) {
            $l = trim(str_replace('\\', '/', $l), " \t/");
            if ($l !== '' && strpos($l, '..') === false && preg_match('#^[A-Za-z0-9_./*-]+$#', $l)) {
                $lineas[] = $l;
            }
        }
        $servirAntes = (int) Configuration::getGlobalValue('ECOMWEBP_SERVIR');
        $servir = (int) Tools::getValue('ECOMWEBP_SERVIR') ? 1 : 0;
        Configuration::updateGlobalValue('ECOMWEBP_ACTIVO', (int) Tools::getValue('ECOMWEBP_ACTIVO') ? 1 : 0);
        Configuration::updateGlobalValue('ECOMWEBP_SERVIR', $servir);
        Configuration::updateGlobalValue('ECOMWEBP_PRODUCTOS', (int) Tools::getValue('ECOMWEBP_PRODUCTOS') ? 1 : 0);
        Configuration::updateGlobalValue('ECOMWEBP_CALIDAD', $calidad);
        Configuration::updateGlobalValue('ECOMWEBP_CARPETAS', $lineas ? implode("\n", $lineas) : '-');

        $aviso = '';
        if ($servir && !EcomWebpautoHtaccess::poner()) {
            $aviso = $this->displayWarning($this->trans('The .htaccess file could not be written: the server will not deliver the WebP files.', array(), 'Modules.Ecomwebpauto.Admin'));
        } elseif (!$servir && $servirAntes) {
            EcomWebpautoHtaccess::quitar();
        }

        return $this->displayConfirmation($this->trans('Settings saved.', array(), 'Modules.Ecomwebpauto.Admin')) . $aviso;
    }

    private function panel()
    {
        $carpetas = EcomWebpautoGenerador::carpetas((string) Configuration::getGlobalValue('ECOMWEBP_CARPETAS'));
        $filas = EcomWebpautoGenerador::contar(_PS_ROOT_DIR_, $carpetas, (bool) Configuration::getGlobalValue('ECOMWEBP_PRODUCTOS'));
        $prueba = (int) Configuration::getGlobalValue('ECOMWEBP_SERVIR') ? EcomWebpautoHtaccess::probar($carpetas) : null;
        $ultimo = (int) Configuration::getGlobalValue('ECOMWEBP_ULTIMO');
        $this->context->smarty->assign(array(
            'ew_filas' => $filas,
            'ew_htaccess' => EcomWebpautoHtaccess::puesto(),
            'ew_servir' => (int) Configuration::getGlobalValue('ECOMWEBP_SERVIR'),
            'ew_prueba' => $prueba,
            'ew_ultimo' => $ultimo ? date('d/m/Y H:i', $ultimo) : '',
            'ew_cron' => $this->context->link->getModuleLink($this->name, 'cron', array('token' => Configuration::getGlobalValue('ECOMWEBP_TOKEN'))),
            'ew_accion' => $this->context->link->getAdminLink('AdminModules', true) . '&configure=' . $this->name,
            'ew_multitienda' => Shop::isFeatureActive(),
        ));

        return $this->display(__FILE__, 'views/templates/admin/panel.tpl');
    }

    private function formulario()
    {
        $si = $this->trans('Yes', array(), 'Modules.Ecomwebpauto.Admin');
        $no = $this->trans('No', array(), 'Modules.Ecomwebpauto.Admin');
        $interruptor = function ($nombre, $etiqueta, $desc, $pestana) use ($si, $no) {
            return array(
                'type' => 'switch', 'label' => $etiqueta, 'name' => $nombre, 'desc' => $desc, 'tab' => $pestana, 'is_bool' => true,
                'values' => array(array('id' => $nombre . '_on', 'value' => 1, 'label' => $si), array('id' => $nombre . '_off', 'value' => 0, 'label' => $no)),
            );
        };
        $form = array(array('form' => array(
            'legend' => array('title' => $this->trans('Settings', array(), 'Modules.Ecomwebpauto.Admin'), 'icon' => 'icon-picture'),
            'tabs' => array(
                'ewgeneral' => $this->trans('General', array(), 'Modules.Ecomwebpauto.Admin'),
                'ewcarpetas' => $this->trans('Folders', array(), 'Modules.Ecomwebpauto.Admin'),
            ),
            'input' => array(
                $interruptor('ECOMWEBP_ACTIVO', $this->trans('Create WebP automatically', array(), 'Modules.Ecomwebpauto.Admin'),
                    $this->trans('When an image is uploaded or changed in the back office, its WebP copy is created.', array(), 'Modules.Ecomwebpauto.Admin'), 'ewgeneral'),
                $interruptor('ECOMWEBP_SERVIR', $this->trans('Deliver the WebP to browsers that accept it', array(), 'Modules.Ecomwebpauto.Admin'),
                    $this->trans('Adds a rule to the .htaccess file: the page keeps asking for the JPG or PNG and the server sends the WebP.', array(), 'Modules.Ecomwebpauto.Admin'), 'ewgeneral'),
                array('type' => 'text', 'label' => $this->trans('Quality', array(), 'Modules.Ecomwebpauto.Admin'), 'name' => 'ECOMWEBP_CALIDAD',
                    'class' => 'fixed-width-sm', 'desc' => $this->trans('From 40 to 100. 82 is a good balance.', array(), 'Modules.Ecomwebpauto.Admin'), 'tab' => 'ewgeneral'),
                array('type' => 'textarea', 'label' => $this->trans('Folders to watch', array(), 'Modules.Ecomwebpauto.Admin'), 'name' => 'ECOMWEBP_CARPETAS',
                    'rows' => 12, 'desc' => $this->trans('One per line, from the shop root. Ending in /* means only that folder, without subfolders.', array(), 'Modules.Ecomwebpauto.Admin'), 'tab' => 'ewcarpetas'),
                $interruptor('ECOMWEBP_PRODUCTOS', $this->trans('Also product photos', array(), 'Modules.Ecomwebpauto.Admin'),
                    $this->trans('Only for shops where PrestaShop does not create them (1.7, or 8 and 9 without the WebP format active).', array(), 'Modules.Ecomwebpauto.Admin'), 'ewcarpetas'),
            ),
            'submit' => array('title' => $this->trans('Save', array(), 'Modules.Ecomwebpauto.Admin'), 'name' => 'submitEcomwebpauto'),
        )));
        $helper = new HelperForm();
        $helper->module = $this;
        $helper->name_controller = $this->name;
        $helper->table = $this->name;
        $helper->identifier = $this->identifier;
        $helper->token = Tools::getAdminTokenLite('AdminModules');
        $helper->currentIndex = AdminController::$currentIndex . '&configure=' . $this->name;
        $helper->default_form_language = (int) Configuration::get('PS_LANG_DEFAULT');
        $helper->allow_employee_form_lang = (int) Configuration::get('PS_BO_ALLOW_EMPLOYEE_FORM_LANG');
        $helper->submit_action = 'submitEcomwebpauto';
        $carpetas = (string) Configuration::getGlobalValue('ECOMWEBP_CARPETAS');
        $helper->fields_value = array(
            'ECOMWEBP_ACTIVO' => (int) Configuration::getGlobalValue('ECOMWEBP_ACTIVO'),
            'ECOMWEBP_SERVIR' => (int) Configuration::getGlobalValue('ECOMWEBP_SERVIR'),
            'ECOMWEBP_CALIDAD' => (int) Configuration::getGlobalValue('ECOMWEBP_CALIDAD'),
            'ECOMWEBP_CARPETAS' => $carpetas === '-' ? '' : $carpetas,
            'ECOMWEBP_PRODUCTOS' => (int) Configuration::getGlobalValue('ECOMWEBP_PRODUCTOS'),
        );

        return $helper->generateForm($form);
    }

    /**
     * Registro y aviso de versión en modules.gmartos.es: una vez por semana, 3 s de tope, en silencio si falla.
     */
    private function checkGmartosUpdate()
    {
        $ultimo = (int) Configuration::get('GMARTOS_LAST_PING_' . $this->name);
        if ((time() - $ultimo) < 604800) {
            return (bool) Configuration::get('GMARTOS_UPDATE_AVAILABLE_' . $this->name);
        }
        if (!function_exists('curl_init')) {
            return false;
        }
        $datos = array(
            'action' => 'register',
            'module_name' => $this->name,
            'version' => $this->version,
            'url' => Tools::getShopDomainSsl(true),
            'email' => Configuration::get('PS_SHOP_EMAIL'),
        );
        try {
            $curl = \curl_init('https://modules.gmartos.es/api.php');
            if ($curl === false) {
                return false;
            }
            \curl_setopt($curl, CURLOPT_POST, true);
            \curl_setopt($curl, CURLOPT_POSTFIELDS, json_encode($datos));
            \curl_setopt($curl, CURLOPT_HTTPHEADER, array('Content-Type: application/json'));
            \curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
            \curl_setopt($curl, CURLOPT_TIMEOUT, 3);
            \curl_setopt($curl, CURLOPT_CONNECTTIMEOUT, 2);
            \curl_setopt($curl, CURLOPT_SSL_VERIFYPEER, true);
            \curl_setopt($curl, CURLOPT_SSL_VERIFYHOST, 2);
            $cuerpo = (string) \curl_exec($curl);
            $codigo = (int) \curl_getinfo($curl, CURLINFO_HTTP_CODE);
            \curl_close($curl);
        } catch (Exception $e) {
            return false;
        }
        if ($codigo === 200 && $cuerpo) {
            $json = json_decode($cuerpo, true);
            if (is_array($json) && !empty($json['success'])) {
                Configuration::updateValue('GMARTOS_LAST_PING_' . $this->name, time());
                if (!empty($json['update_available'])) {
                    Configuration::updateValue('GMARTOS_UPDATE_AVAILABLE_' . $this->name, true);
                    Configuration::updateValue('GMARTOS_LATEST_VERSION_' . $this->name, isset($json['latest_version']) ? $json['latest_version'] : '');

                    return true;
                }
                Configuration::updateValue('GMARTOS_UPDATE_AVAILABLE_' . $this->name, false);
            }
        }

        return false;
    }
}
