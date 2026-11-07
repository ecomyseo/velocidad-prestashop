{**
 * Ecom Experts
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   https://opensource.org/licenses/AFL-3.0 Academic Free License version 3.0
 *}
<div class="panel" id="ecomwebpauto-panel">
    <div class="panel-heading"><i class="icon-picture"></i> {l s='WebP status' d='Modules.Ecomwebpauto.Admin'}</div>

    {if $ew_multitienda}
        <div class="alert alert-info">{l s='The settings are common to all shops: the image files are shared.' d='Modules.Ecomwebpauto.Admin'}</div>
    {/if}
    {if $ew_servir && !$ew_htaccess}
        <div class="alert alert-danger">{l s='The .htaccess rule is missing and could not be written: browsers keep receiving JPG and PNG.' d='Modules.Ecomwebpauto.Admin'}</div>
    {elseif $ew_servir && $ew_prueba && !$ew_prueba.ok}
        <div class="alert alert-warning">{l s='The rule is in place but the server does not deliver the WebP (it may be nginx serving the images directly).' d='Modules.Ecomwebpauto.Admin'}</div>
    {/if}

    <table class="table">
        <thead>
            <tr>
                <th>{l s='Folder' d='Modules.Ecomwebpauto.Admin'}</th>
                <th class="text-right">{l s='Images' d='Modules.Ecomwebpauto.Admin'}</th>
                <th class="text-right">{l s='With WebP' d='Modules.Ecomwebpauto.Admin'}</th>
                <th class="text-right">{l s='No gain' d='Modules.Ecomwebpauto.Admin'}</th>
                <th class="text-right">{l s='Missing' d='Modules.Ecomwebpauto.Admin'}</th>
                <th class="text-right">{l s='Weight: image / WebP' d='Modules.Ecomwebpauto.Admin'}</th>
            </tr>
        </thead>
        <tbody>
        {foreach from=$ew_filas item=fila}
            <tr>
                <td><code>{$fila.carpeta|escape:'html':'UTF-8'}</code>{if !$fila.existe} <span class="text-muted">({l s='does not exist' d='Modules.Ecomwebpauto.Admin'})</span>{/if}</td>
                <td class="text-right">{$fila.imagenes|intval}</td>
                <td class="text-right">{$fila.con_webp|intval}</td>
                <td class="text-right">{$fila.sin_ventaja|intval}</td>
                <td class="text-right">{if $fila.faltan}<strong class="text-danger">{$fila.faltan|intval}</strong>{else}0{/if}</td>
                <td class="text-right">{if $fila.con_webp}{$fila.kb_imagen|intval} KB / {$fila.kb_webp|intval} KB{/if}</td>
            </tr>
        {/foreach}
        </tbody>
    </table>

    <form method="post" action="{$ew_accion|escape:'html':'UTF-8'}" style="margin-top:12px">
        <button type="submit" name="submitEcomwebpautoGenerar" value="1" class="btn btn-primary"><i class="icon-cogs"></i> {l s='Create the missing WebP now' d='Modules.Ecomwebpauto.Admin'}</button>
        <span class="help-block" style="display:inline-block;margin-left:10px">
            {l s='Last automatic check:' d='Modules.Ecomwebpauto.Admin'} {if $ew_ultimo}{$ew_ultimo|escape:'html':'UTF-8'}{else}{l s='never' d='Modules.Ecomwebpauto.Admin'}{/if}
            {if $ew_servir && $ew_prueba} · {l s='The server delivers WebP:' d='Modules.Ecomwebpauto.Admin'} <strong>{if $ew_prueba.ok}{l s='yes' d='Modules.Ecomwebpauto.Admin'}{else}{l s='no' d='Modules.Ecomwebpauto.Admin'}{/if}</strong>{/if}
        </span>
    </form>

    <details style="margin-top:14px">
        <summary style="cursor:pointer"><strong>{l s='Help: how it works' d='Modules.Ecomwebpauto.Admin'}</strong></summary>
        <ul style="margin-top:8px">
            <li>{l s='When an image is uploaded or changed in the back office (sliders, banners, CMS pages, categories, brands...), its WebP copy is created at the end of that same request, next to the original and with the same name.' d='Modules.Ecomwebpauto.Admin'}</li>
            <li>{l s='Product photos are not touched: PrestaShop 8 and 9 create them when the WebP format is active in Design > Image settings.' d='Modules.Ecomwebpauto.Admin'}</li>
            <li>{l s='The originals are never modified or deleted. If an image changes, its WebP is created again.' d='Modules.Ecomwebpauto.Admin'}</li>
            <li>{l s='No gain: its WebP would weigh more than the image, or there is another image with the same name (logo.jpg and logo.png). Those keep being served as they are.' d='Modules.Ecomwebpauto.Admin'}</li>
            <li>{l s='The page keeps asking for the JPG or PNG; the .htaccess rule sends the WebP only to browsers that accept it, so no template has to be changed.' d='Modules.Ecomwebpauto.Admin'}</li>
            <li>{l s='For images uploaded by FTP or by imports, you can call this address from the server cron:' d='Modules.Ecomwebpauto.Admin'} <code>{$ew_cron|escape:'html':'UTF-8'}</code></li>
        </ul>
    </details>
</div>
