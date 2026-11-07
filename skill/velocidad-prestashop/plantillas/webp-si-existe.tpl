{**
 * Ecom Experts - Licencia AFL-3.0
 *
 * Deja en la variable «ew_var» de la plantilla que lo incluye la URL del WebP de una foto de producto del tipo
 * «ew_tipo» si el fichero existe en disco; si no, la URL de siempre (JPG). Para temas que no usan <picture>.
 * Requiere PrestaShop 8.1+ con el formato WebP activado (Diseño > Ajustes de imagen) y las miniaturas regeneradas.
 *
 * Uso:
 *   {include file='catalog/_partials/webp-si-existe.tpl' ew_imagen=$product.cover ew_tipo='home_default' ew_var='urlFoto'}
 *   <img src="{$urlFoto}" ...>
 *
 * Ojo: no se compara con file_exists() sobre la URL (siempre es falso): se comprueba la ruta en disco.
 *}
{strip}
{assign var='ew_url' value=$ew_imagen.bySize.$ew_tipo.url}
{if !empty($ew_imagen.id_image)}
  {assign var='ew_dir' value=Image::getImgFolderStatic($ew_imagen.id_image)}
  {if file_exists("`$smarty.const._PS_PROD_IMG_DIR_``$ew_dir``$ew_imagen.id_image`-`$ew_tipo`.webp")}
    {if !empty($ew_imagen.bySize.$ew_tipo.sources.webp)}{assign var='ew_url' value=$ew_imagen.bySize.$ew_tipo.sources.webp}{else}{assign var='ew_url' value=$ew_imagen.bySize.$ew_tipo.url|regex_replace:'/\.jpg$/':'.webp'}{/if}
  {/if}
{/if}
{assign var=$ew_var value=$ew_url scope='parent'}
{/strip}
