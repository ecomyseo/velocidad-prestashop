{**
 * webp-si-existe.tpl
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   https://opensource.org/licenses/AFL-3.0 Academic Free License 3.0 (AFL-3.0)
 *
 * Deja en una variable de la plantilla que lo incluye la URL WebP (o AVIF) de una foto de producto
 * SOLO si el fichero existe en img/p/. Si no existe, la URL JPG de siempre (o una cadena vacía).
 * Va en templates/catalog/_partials/ del tema (del tema HIJO si lo hay). PrestaShop 1.7, 8 y 9.
 *
 * Parámetros:
 *   ew_imagen   la imagen tal como la da el núcleo: $product.cover, $product.default_image
 *               o cada $image de $product.images
 *   ew_tipo     el tipo de imagen: home_default, large_default, medium_default, small_default,
 *               cart_default… o los alias del núcleo large / medium / small (se traducen al tipo real)
 *   ew_var      nombre de la variable que se crea en la plantilla que incluye
 *   ew_formato  (opcional) webp (por defecto) o avif
 *   ew_sin      (opcional) jpg (por defecto): sin fichero, la URL JPG.
 *               vacio: sin fichero, cadena vacía (para pintar un <source> solo si hay WebP)
 *
 * Uso en un <img> (el src pasa a ser el WebP cuando existe):
 *   {include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$product.cover ew_tipo='home_default' ew_var='urlMiniatura'}
 *   <img src="{$urlMiniatura}" ...>
 *
 * Uso en un <picture> (solo si el JavaScript del tema no cambia el src de esa foto):
 *   {include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$product.cover ew_tipo='home_default' ew_var='webpMiniatura' ew_sin='vacio'}
 *   <picture>{if $webpMiniatura}<source srcset="{$webpMiniatura}" type="image/webp">{/if}<img src="{$product.cover.bySize.home_default.url}" ...></picture>
 *
 * La variable se asigna SIEMPRE (también vacía), así que dentro de un {foreach} cada foto lleva la suya.
 * Sin Image::getImgFolderStatic() (clase sin registrar: aviso de obsoleto en el Smarty 4.5 de PrestaShop 9)
 * y sin _PS_PROD_IMG_DIR_ (no existe en PrestaShop 9): la carpeta se calcula aquí y la ruta sale de _PS_IMG_DIR_.
 *}
{strip}
{if empty($ew_formato)}{assign var='ew_formato' value='webp'}{/if}
{assign var='ew_url' value=''}
{assign var='ew_hay' value=false}
{assign var='ew_t' value=$ew_tipo}
{if ($ew_t == 'large' || $ew_t == 'medium' || $ew_t == 'small') && !empty($ew_imagen.$ew_t.url) && !empty($ew_imagen.bySize)}
  {foreach $ew_imagen.bySize as $ew_nombre => $ew_datos}
    {if !empty($ew_datos.url) && $ew_datos.url == $ew_imagen.$ew_t.url}{assign var='ew_t' value=$ew_nombre}{/if}
  {/foreach}
{/if}
{if !empty($ew_imagen.bySize.$ew_t.url)}{assign var='ew_url' value=$ew_imagen.bySize.$ew_t.url}{/if}
{if $ew_url && !empty($ew_imagen.id_image) && ($ew_imagen.id_image|regex_replace:'/[0-9]/':'') == ''}
  {assign var='ew_carpeta' value=$ew_imagen.id_image|regex_replace:'/([0-9])/':'$1/'}
  {assign var='ew_fichero' value="`$ew_imagen.id_image`-`$ew_t`.`$ew_formato`"}
  {if file_exists("`$smarty.const._PS_IMG_DIR_`p/`$ew_carpeta``$ew_fichero`")}
    {assign var='ew_hay' value=true}
    {if !empty($ew_imagen.bySize.$ew_t.sources.$ew_formato)}
      {assign var='ew_url' value=$ew_imagen.bySize.$ew_t.sources.$ew_formato}
    {else}
      {assign var='ew_url' value="`$smarty.const._THEME_PROD_DIR_``$ew_carpeta``$ew_fichero`"}
    {/if}
  {/if}
{/if}
{if !$ew_hay && isset($ew_sin) && $ew_sin == 'vacio'}{assign var='ew_url' value=''}{/if}
{assign var=$ew_var value=$ew_url scope='parent'}
{/strip}
