<?php
/**
 * probar_tpl.php: compila plantillas .tpl de un tema con el MISMO Smarty de la tienda, sin cargar PrestaShop,
 * y prueba el parcial webp-si-existe.tpl con ficheros de mentira. No toca la tienda ni su base de datos.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   https://opensource.org/licenses/AFL-3.0 Academic Free License 3.0 (AFL-3.0)
 *
 * Uso:
 *   php probar_tpl.php --smarty=<tienda>/vendor/smarty/smarty/libs/Smarty.class.php --tema=<tema>/templates
 *       [--padre=<tema padre>/templates] [--orig=<copia original>/templates] catalog/product.tpl ...
 *   php probar_tpl.php --smarty=<...>/Smarty.class.php --probar-parcial [--parcial=<ruta a webp-si-existe.tpl>]
 *
 * Las etiquetas propias de PrestaShop ({l}, {url}, {hook}, {widget}…) y los recursos module: se sustituyen por
 * vacíos: aquí solo se comprueba que la plantilla COMPILA. Si se da --orig y la original falla con el mismo error,
 * el fallo es del banco de pruebas, no del cambio. Los avisos de «obsoleto» (Smarty 4.5, PrestaShop 9) se listan.
 * Sale con código 1 si algo falla.
 */
error_reporting(E_ALL);
$opc = array('smarty' => '', 'tema' => '', 'padre' => '', 'orig' => '', 'parcial' => '');
$ficheros = array();
$probarParcial = false;
foreach (array_slice($argv, 1) as $a) {
    if ($a === '--probar-parcial') {
        $probarParcial = true;
    } elseif (preg_match('/^--(smarty|tema|padre|orig|parcial)=(.+)$/', $a, $m)) {
        $opc[$m[1]] = rtrim($m[2], '/\\');
    } else {
        $ficheros[] = $a;
    }
}
if ($opc['smarty'] === '' || !is_file($opc['smarty']) || (!$probarParcial && ($opc['tema'] === '' || !$ficheros))) {
    fwrite(STDERR, "Uso: php probar_tpl.php --smarty=<Smarty.class.php> --tema=<templates> [--padre=<templates>] [--orig=<templates>] fichero.tpl ...\n"
        . "     php probar_tpl.php --smarty=<Smarty.class.php> --probar-parcial [--parcial=<webp-si-existe.tpl>]\n");
    exit(2);
}
require $opc['smarty'];

$avisos = array();
set_error_handler(function ($no, $txt) use (&$avisos) {
    // solo los avisos que Smarty da por la PLANTILLA; los E_DEPRECATED del propio PHP con un Smarty viejo se callan
    if ($no === E_USER_DEPRECATED) {
        $avisos[] = $txt;

        return true;
    }
    if ($no === E_DEPRECATED) {
        return true;
    }

    return false;
});

function ew_vacio()
{
    return '';
}
function ew_manejador($name, $type, $template, &$callback, &$script, &$cacheable)
{
    $callback = 'ew_vacio';

    return true;
}
class EwRecursoVacio extends Smarty_Resource_Custom
{
    protected function fetch($name, &$source, &$mtime)
    {
        $source = '';
        $mtime = time();
    }
}
class EwRecursoPadre extends Smarty_Resource_Custom
{
    public $dir = '';

    protected function fetch($name, &$source, &$mtime)
    {
        $f = $this->dir . '/' . $name;
        $source = ($this->dir !== '' && is_file($f)) ? file_get_contents($f) : '';
        $mtime = is_file($f) ? filemtime($f) : time();
    }
}

$fallos = 0;
function ew_ok($cond, $texto)
{
    global $fallos;
    echo ($cond ? 'OK     ' : 'FALLA  ') . $texto . "\n";
    $fallos += $cond ? 0 : 1;
}

/**
 * Modificadores y clases que la propia tienda registra en config/smarty.config.inc.php (PrestaShop 9 registra
 * file_exists, Tools…): sin ellos, el Smarty 4.5 daría avisos de obsoleto que en la tienda no salen.
 */
function ew_registros($rutaSmarty)
{
    $raiz = dirname($rutaSmarty, 5);
    $conf = $raiz . '/config/smarty.config.inc.php';
    $r = array('modificadores' => array(), 'clases' => array());
    if (!is_file($conf)) {
        return $r;
    }
    $c = file_get_contents($conf);
    if (preg_match_all("/smartyRegisterFunction\\(\\s*\\\$smarty\\s*,\\s*'modifier'\\s*,\\s*'(\\w+)'\\s*,\\s*'(\\w+)'/", $c, $m, PREG_SET_ORDER)) {
        foreach ($m as $x) {
            if (function_exists($x[2])) {
                $r['modificadores'][$x[1]] = $x[2];
            }
        }
    }
    if (preg_match_all("/registerClass\\(\\s*'(\\w+)'\\s*,\\s*'([\\\\\\w]+)'/", $c, $m, PREG_SET_ORDER)) {
        foreach ($m as $x) {
            $r['clases'][$x[1]] = $x[2];
        }
    }

    return $r;
}

function ew_smarty(array $dirs, $padre)
{
    global $opc;
    static $registros = null;
    if ($registros === null) {
        $registros = ew_registros($opc['smarty']);
    }
    $s = new Smarty();
    foreach ($registros['modificadores'] as $nombre => $funcion) {
        $s->registerPlugin('modifier', $nombre, $funcion);
    }
    foreach ($registros['clases'] as $nombre => $clase) {
        // aquí no se carga PrestaShop: una clase vacía con ese nombre basta para compilar
        if (!class_exists($clase)) {
            eval('class ' . ltrim($clase, chr(92)) . ' {}');
        }
        $s->registerClass($nombre, $clase);
    }
    $s->setCompileDir(sys_get_temp_dir() . '/ew_smarty_' . md5(implode('|', $dirs) . microtime(true)));
    $s->setTemplateDir($dirs);
    $s->registerDefaultPluginHandler('ew_manejador');
    $s->registerResource('module', new EwRecursoVacio());
    $p = new EwRecursoPadre();
    $p->dir = $padre;
    $s->registerResource('parent', $p);
    if (method_exists($s, 'muteUndefinedOrNullWarnings')) {
        $s->muteUndefinedOrNullWarnings();
    }

    return $s;
}

$r = ew_registros($opc['smarty']);
echo 'Smarty ' . Smarty::SMARTY_VERSION . ' con PHP ' . PHP_VERSION . ' (' . count($r['modificadores']) . ' modificadores y '
    . count($r['clases']) . " clases registrados como en la tienda)\n";

if ($ficheros) {
    $dirs = array($opc['tema']);
    if ($opc['padre'] !== '') {
        $dirs[] = $opc['padre'];
    }
    foreach ($ficheros as $t) {
        $avisos = array();
        $s = ew_smarty($dirs, $opc['padre']);
        try {
            $s->createTemplate($t)->compileTemplateSource();
            ew_ok(true, "compila $t");
        } catch (Throwable $e) {
            $mismo = false;
            if ($opc['orig'] !== '' && is_file($opc['orig'] . '/' . $t)) {
                try {
                    ew_smarty(array($opc['orig']), $opc['padre'])->createTemplate($t)->compileTemplateSource();
                } catch (Throwable $e2) {
                    $mismo = $e2->getMessage() === $e->getMessage();
                }
            }
            ew_ok($mismo, "compila $t: " . $e->getMessage() . ($mismo ? ' (la original da el mismo error: es del banco de pruebas)' : ''));
        }
        foreach (array_unique($avisos) as $a) {
            echo "  AVISO  $a\n";
        }
    }
}

if ($probarParcial) {
    $parcial = $opc['parcial'] !== '' ? $opc['parcial'] : dirname(__DIR__) . '/plantillas/webp-si-existe.tpl';
    if (!is_file($parcial)) {
        fwrite(STDERR, "No encuentro el parcial: $parcial\n");
        exit(2);
    }
    $base = sys_get_temp_dir() . '/ew_prueba_' . getmypid();
    @mkdir($base . '/templates/catalog/_partials', 0777, true);
    @mkdir($base . '/img/p/2/4/3/2', 0777, true);
    @mkdir($base . '/img/p/7', 0777, true);
    copy($parcial, $base . '/templates/catalog/_partials/webp-si-existe.tpl');
    touch($base . '/img/p/2/4/3/2/2432-large_default.webp');
    touch($base . '/img/p/2/4/3/2/2432-home_default.webp');
    touch($base . '/img/p/7/7-large_default.avif');
    if (!defined('_PS_IMG_DIR_')) {
        define('_PS_IMG_DIR_', $base . '/img/');
    }
    if (!defined('_THEME_PROD_DIR_')) {
        define('_THEME_PROD_DIR_', '/img/p/');
    }
    $tamano = function ($id, $tipo, $conFuente) {
        $u = "https://tienda.test/$id-$tipo/mesa.jpg";
        $b = array('url' => $u, 'width' => 800, 'height' => 800, 'sources' => array('jpg' => $u));
        if ($conFuente) {
            $b['sources']['webp'] = "https://tienda.test/$id-$tipo/mesa.webp";
        }

        return $b;
    };
    $img = function ($id, $conFuente) use ($tamano) {
        $grande = $tamano($id, 'large_default', $conFuente);
        $casa = $tamano($id, 'home_default', $conFuente);
        $casa['width'] = $casa['height'] = 250;

        return array('id_image' => $id, 'bySize' => array('home_default' => $casa, 'large_default' => $grande),
            'small' => $casa, 'medium' => $casa, 'large' => $grande);
    };
    $avisos = array();
    $s = ew_smarty(array($base . '/templates'), '');
    $inc = "{include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=\$i ew_tipo='%s' ew_var='miUrl'%s}[{\$miUrl}]";
    $f = function ($tipo, $extra = '') use ($s, $inc) {
        return $s->fetch('string:' . sprintf($inc, $tipo, $extra));
    };
    $s->assign('i', $img(2432, true));
    ew_ok($f('large_default') === '[https://tienda.test/2432-large_default/mesa.webp]', 'hay fichero y URL del núcleo (8.1+): la URL WebP del núcleo');
    ew_ok($f('large') === '[https://tienda.test/2432-large_default/mesa.webp]', 'alias «large»: se traduce a large_default');
    ew_ok($f('home_default', " ew_sin='vacio'") === '[https://tienda.test/2432-home_default/mesa.webp]', 'ew_sin=vacio con fichero: la URL WebP');
    $s->assign('i', $img(2432, false));
    ew_ok($f('large_default') === '[/img/p/2/4/3/2/2432-large_default.webp]', 'hay fichero pero no URL del núcleo (1.7, o formato múltiple apagado): ruta física');
    $s->assign('i', $img(99, true));
    ew_ok($f('large_default') === '[https://tienda.test/99-large_default/mesa.jpg]', 'sin fichero (aunque el núcleo dé la URL): el JPG');
    ew_ok($f('large_default', " ew_sin='vacio'") === '[]', 'sin fichero y ew_sin=vacio: cadena vacía');
    $s->assign('i', $img(7, true));
    ew_ok($f('large_default', " ew_formato='avif'") === '[/img/p/7/7-large_default.avif]', 'ew_formato=avif con fichero');
    ew_ok($f('home_default', " ew_formato='avif'") === '[https://tienda.test/7-home_default/mesa.jpg]', 'ew_formato=avif sin fichero: el JPG');
    $s->assign('i', array('bySize' => array('large_default' => array('url' => 'https://tienda.test/sin-foto.jpg'))));
    ew_ok($f('large_default') === '[https://tienda.test/sin-foto.jpg]', 'imagen sin id_image (la de «sin foto»): el JPG');
    $s->assign('i', array('id_image' => 'es-default', 'bySize' => array('large_default' => array('url' => 'https://tienda.test/es-default.jpg'))));
    ew_ok($f('large_default') === '[https://tienda.test/es-default.jpg]', 'id_image no numérico: el JPG');
    $s->assign('i', null);
    ew_ok($f('large_default') === '[]', 'sin imagen (producto sin foto): vacío, sin error');
    $bucle = "string:{foreach \$is as \$image}{include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=\$image ew_tipo='large_default' ew_var='g' ew_sin='vacio'}<{\$g}>{/foreach}";
    $s->assign('is', array($img(2432, true), $img(99, true), $img(2432, false)));
    ew_ok($s->fetch($bucle) === '<https://tienda.test/2432-large_default/mesa.webp><><' . '/img/p/2/4/3/2/2432-large_default.webp>', 'en un bucle cada foto lleva la suya (no arrastra la anterior)');
    foreach (array_unique($avisos) as $a) {
        echo "  AVISO  $a\n";
    }
    ew_ok(!$avisos, 'el parcial no da avisos de obsoleto');
    array_map('unlink', array_filter(array(
        $base . '/img/p/2/4/3/2/2432-large_default.webp', $base . '/img/p/2/4/3/2/2432-home_default.webp',
        $base . '/img/p/7/7-large_default.avif', $base . '/templates/catalog/_partials/webp-si-existe.tpl',
    ), 'is_file'));
}
echo "FALLAN: $fallos\n";
exit($fallos ? 1 : 0);
