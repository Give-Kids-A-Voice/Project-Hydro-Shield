/* Hydro-Shield in Spanish. English lives in index.html; this file holds only the Spanish.
   Language: ?lang=es or ?lang=en in the link, else the visitor's own choice (remembered on this device only),
   else the browser's language. Nothing about the visitor is sent anywhere.
   When the English text in index.html changes (a new city in the coverage note, a new credit), change the
   matching Spanish here too. */
var HS_LANG = (function () {
  var q = null, l = null;
  try { q = new URLSearchParams(location.search).get('lang'); } catch (e) {}
  if (q === 'es' || q === 'en') { try { localStorage.setItem('hs-lang', q); } catch (e) {} return q; }
  try { l = localStorage.getItem('hs-lang'); } catch (e) {}
  if (l === 'es' || l === 'en') return l;
  return /^es\b/i.test(navigator.language || '') ? 'es' : 'en';
})();

var HS_ES = {
  // Whole blocks of the page, by data-i18n key (HTML allowed).
  html: {
    h1: 'Cada estanque, canal y piscina cerca de su casa',
    lede: 'Escriba la dirección de una casa. Marcamos el agua que hay a poca distancia a pie y la ordenamos según lo cerca que está la orilla, para que sepa dónde buscar primero si su hijo se aleja.',
    addr_ph: 'Calle y número, ciudad, estado',
    addr_al: 'Dirección de la casa',
    rad_al: 'Radio de búsqueda',
    go: 'Buscar el agua',
    gps: 'Usar mi ubicación',
    install: 'Instalar la app',
    mark: '+ Marcar agua que conozco',
    share: 'Copiar enlace',
    share_t: 'Copiar un enlace que abre Hydro-Shield en esta dirección',
    map_al: 'Mapa de peligros de agua',
    radar: '<b>El radar meteorológico no es nuestro.</b> Viene de los radares NEXRAD de NOAA a través del Iowa Environmental Mesonet, puede llevar de 5 a 10 minutos de retraso y puede tener huecos. El agua que sube en zanjas y arroyos puede no verse en el radar. Para avisos, consulte <a href="https://www.weather.gov/" target="_blank" rel="noopener">weather.gov</a> (en inglés). Si un niño desaparece cerca del agua, llame primero al 911.',
    s_near: 'orilla de agua más cercana',
    s_count: 'peligros de agua encontrados',
    s_close: 'a menos de 150 m',
    list_al: 'Peligros de agua, del más cercano al más lejano',
    list0: 'Escriba una dirección o haga clic en una casa en el mapa. Aquí aparecerán las piscinas, estanques y canales más cercanos, del más cercano al más lejano.',
    gaps: '<b>Al mapa le faltan datos.</b> Faltan estanques de retención nuevos y algunas piscinas. Use <b>Marcar agua que conozco</b> para añadir lo que vea en su calle; se guarda solo en este dispositivo. Tome esta lista como un punto de partida, no como una garantía.',
    cov_al: 'Dónde funciona este mapa',
    disclaimer: '<b>Solo para información.</b> No garantizamos que este mapa esté completo ni que sea exacto. Los registros pueden estar desactualizados, falta parte del agua o aparece un poco desplazada, y las piscinas marcadas como "estimación aérea" son detecciones automáticas en fotos aéreas que pueden estar equivocadas. Recorra y revise siempre usted mismo la zona alrededor de su casa. No reemplaza la supervisión, las alarmas en las puertas ni las clases de natación.',
    coverage: '<b>Dónde funciona.</b> Lagos, estanques, canales y arroyos: en los 48 estados contiguos y Washington, D.C. Los arroyos también vienen del mapa de corrientes del Servicio Geológico de EE. UU. (USGS), que incluye arroyos pequeños escondidos bajo los árboles que faltan en OpenStreetMap: arroyos, canales y zanjas permanentes en todas partes, y arroyos de temporada en los pueblos y sus alrededores. Hawái también está incluido, igual que las principales ciudades de Alaska (Anchorage, Mat-Su y la península de Kenai, Fairbanks, Juneau, Ketchikan, Sitka, Kodiak y Bethel); en el resto de Alaska el mapa consulta en vivo los servidores públicos de OpenStreetMap, que pueden ir lentos o estar ocupados. Registros de piscinas en Florida: condados de Alachua, Brevard, Charlotte, Citrus, Collier, Duval, Hernando, Hillsborough, Indian River, Lake, Lee, Leon, Manatee, Marion, Martin, Orange, Osceola, Pasco, Pinellas, Polk, Sarasota, Seminole, St. Johns, St. Lucie y Volusia; pronto habrá más. Registros de piscinas en California: condados de San Diego, Riverside, Contra Costa, San Joaquin y Solano, y la ciudad de Pasadena. En el resto del sur de California la cobertura de piscinas es parcial (OpenStreetMap): muchas piscinas de patio todavía no están en el mapa. Registros de piscinas en Arizona, Nevada y Texas: condados de Maricopa, Clark, Washoe, Harris, Tarrant, Dallas, Collin y Williamson. En todos los demás lugares, las piscinas vienen de OpenStreetMap y la cobertura es parcial. Los registros de piscinas vienen de los tasadores de propiedad y los distritos de tasación, que pueden tener un año de retraso con las piscinas nuevas y no incluyen piscinas sobre el suelo ni piscinas sin permiso. En el Valle de San Fernando, el oeste de Los Ángeles (de Santa Mónica a Hollywood y el centro), el South Bay y Long Beach, y el Valle de San Gabriel al este hasta Whittier y Pomona, y el condado de Orange, y el Inland Empire (Ontario, Rancho Cucamonga, Upland, Fontana, Rialto, Colton, San Bernardino, Highland, Loma Linda y Redlands), y Thousand Oaks (con Newbury Park, Westlake Village, Oak Park y Agoura Hills), y Simi Valley, y San José (con Willow Glen, Campbell, Cupertino, Saratoga y Los Gatos), y en Tucson, San Antonio, Austin, el condado de Fort Bend (Sugar Land, Katy, Richmond), el condado de Denton (Denton, Flower Mound, Lewisville), Oklahoma City y Midwest City, Raleigh y Cary, Charlotte, y el área metropolitana de Atlanta (con Marietta, Sandy Springs, Roswell y Alpharetta), Baton Rouge, y Sacramento (con Carmichael, Citrus Heights y Rancho Cordova), y Salt Lake City (con Millcreek, Holladay y Murray; imágenes de 2018, el vuelo de verano más reciente allí), Nashville (con Belle Meade, Green Hills y Brentwood), Kansas City a ambos lados de la frontera estatal (con Overland Park, Leawood, Prairie Village y Raytown), Albuquerque (con Corrales), Memphis (con Germantown, Bartlett y Cordova), St. Louis (con Ladue, Clayton, Creve Coeur, Kirkwood y Webster Groves), Birmingham (con Mountain Brook, Homewood, Vestavia Hills y Hoover), y Columbia, Carolina del Sur (con Forest Acres; imágenes de 2019, el vuelo de verano más reciente allí), y Louisville (con St. Matthews, Jeffersontown y Jeffersonville, Indiana; imágenes de 2020, el vuelo reciente más claro allí), Cincinnati (con Indian Hill, Blue Ash, Montgomery y Hyde Park), Columbus (con Upper Arlington, Bexley y Worthington), Indianápolis (con Lawrence, Speedway y Beech Grove), Richmond, Virginia (con Short Pump, Tuckahoe y Bon Air), Greenville, Carolina del Sur (con Mauldin, Taylors y Greer; imágenes de 2019, el vuelo de verano más reciente allí), Tulsa (con Jenks), Mason, Maineville y Hamilton Township en el condado de Warren, Ohio, South Bend (con Mishawaka y Granger), Waldorf, Maryland, el condado de Montgomery, Maryland (Rockville, Gaithersburg, Potomac y Bethesda), Brighton, Míchigan (con Genoa Township), Providence (con Pawtucket, Cranston y East Providence), Hitchcock, Dickinson y Santa Fe en el condado de Galveston, Texas, el condado de Palm Beach de Boca Raton a Jupiter (Boca, Delray, Boynton Beach, Lake Worth, West Palm Beach, Palm Beach, Wellington, Royal Palm Beach, Palm Beach Gardens, Jupiter y Tequesta), Santa Clarita, Indiana, Pensilvania (imágenes de 2019, el vuelo más claro allí), Altoona y Hollidaysburg, State College, Fresno y Clovis, Bakersfield, Metairie y Nueva Orleans, Charleston (con Mount Pleasant y West Ashley), Wilmington, Carolina del Norte, Savannah, Mobile, Wilmington, Delaware (con Hockessin, Pike Creek y Newark), South Jersey (Cherry Hill, Voorhees, Moorestown, Mount Laurel y Marlton), los suburbios de Filadelfia en los condados de Delaware, Montgomery y Chester (Media, la Main Line, King of Prussia, Blue Bell, Lansdale, West Chester, Exton y Malvern), el condado de Bucks y el noreste de Filadelfia (Doylestown, Yardley, Newtown, Langhorne, Bensalem, Warminster, Southampton, Huntingdon Valley, Somerton y Fox Chase), el condado de Kent, Delaware (Dover, Camden, Wyoming, Smyrna y Milford), el condado de Sussex, Delaware (Lewes, Rehoboth Beach, Milton, Bethany Beach, Ocean View, Fenwick Island, Selbyville, Millsboro, Georgetown, Seaford y Laurel), Ocean City, Maryland (con West Ocean City, Ocean Pines y Berlin), el resto de South Jersey (Medford, Hammonton, Sewell, Glassboro, Deptford, Vineland, Millville, Egg Harbor Township, Galloway, Absecon, Mays Landing, Somers Point, Linwood, Margate, Ventnor, Atlantic City, Ocean City, Sea Isle City, Avalon, Stone Harbor, los Wildwoods y Cape May), McAllen, Edinburg, Mission y Pharr, El Paso, Corpus Christi, Brownsville, Lake Havasu City, Yuma, el Grand Strand (Myrtle Beach, North Myrtle Beach y Surfside Beach), Virginia Beach y Chesapeake, Pensacola y Gulf Breeze, Lubbock, Midland, Odessa, Killeen y Harker Heights, Waco y Woodway, Beaumont, Shreveport y Bossier City, Lafayette y Youngsville, Little Rock y North Little Rock, Huntsville y Madison, Montgomery, Jackson (Misisipi), el oeste de Augusta con Martinez, Evans y Grovetown, Macon, St. George, Las Cruces, Columbus (Georgia), Modesto y Ceres, Visalia, Redding, Boise y Meridian, Knoxville, Chattanooga, Panama City (con Lynn Haven, Callaway y parte de Panama City Beach), Orange Park y Fleming Island, Palm Coast, The Villages y el condado de Broward (Hollywood, Hallandale Beach, Dania Beach, Pembroke Pines, Miramar, Cooper City, Fort Lauderdale, Davie, Plantation, Sunrise, Lauderhill, Weston, Tamarac, Margate, Coral Springs, Parkland, Coconut Creek, Pompano Beach y Deerfield Beach), donde no hay registros de piscinas del condado, el mapa también muestra piscinas estimadas a partir de imágenes aéreas del USDA (2018–2023): son detecciones automáticas, así que algunas están equivocadas, faltan algunas piscinas y no aparecen las construidas después de las fotos. Gratis, sin registrarse, y nada de lo que escribe se guarda.',
    installnote: '<b>Instálelo como app.</b> En iPhone: toque Compartir y luego Agregar a pantalla de inicio. En Android, Chrome o Edge: use el botón Instalar la app o el menú del navegador. La app agrega un botón Usar mi ubicación (su ubicación se queda en su dispositivo) y guarda las zonas que ya ha consultado para usarlas con poca señal.',
    credits: 'Datos de agua © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">colaboradores de OpenStreetMap</a>, vía Overpass. Registros de piscinas cortesía del <a href="https://www.hcpafl.org/" target="_blank" rel="noopener">Hillsborough County Property Appraiser</a>, de los tasadores de propiedad (Property Appraisers) de los condados de Alachua, Brevard, Charlotte, Citrus, Collier, Duval, Hernando, Indian River, Lake, Leon, Manatee, Marion, Martin, Orange, Osceola, Pasco, Pinellas, Polk, Sarasota, Seminole, St. Johns, St. Lucie y Volusia, de Lee County GIS y de las ubicaciones de parcelas del Departamento de Ingresos de Florida (registros públicos). Agua del sur de California: colaboradores de OpenStreetMap. Piscinas del condado de San Diego: datos regionales de parcelas de <a href="https://www.sangis.org/" target="_blank" rel="noopener">SanGIS</a>/SANDAG (San Diego County Assessor). Piscinas del condado de Riverside: datos abiertos del Riverside County Assessor (características de propiedades CREST y parcelas). Piscinas de Pasadena: datos de parcelas de la ciudad de Pasadena (Los Angeles County Assessor). Piscinas del condado de Contra Costa: datos de parcelas del tasador, del Departamento de Tecnología de la Información del condado de Contra Costa. Piscinas del condado de San Joaquin: datos de parcelas del San Joaquin County Assessor. Piscinas del condado de Solano: datos públicos de parcelas del condado de Solano. Otras piscinas del sur de California: colaboradores de OpenStreetMap (cobertura parcial). Agua de todos los demás estados contiguos y Washington, D.C.: colaboradores de OpenStreetMap. Piscinas del condado de Maricopa: datos de parcelas de Maricopa County Enterprise GIS. Piscinas del condado de Clark: datos residenciales y mapa de parcelas del Clark County Assessor, publicados de nuevo por la Oficina de GIS de la ciudad de Las Vegas. Piscinas del condado de Harris: Harris Central Appraisal District. Piscinas del condado de Tarrant: Tarrant Appraisal District. Piscinas del condado de Dallas: Dallas Central Appraisal District. Piscinas del condado de Collin: Collin Central Appraisal District. Piscinas del condado de Williamson: datos abiertos del Williamson Central Appraisal District. Piscinas del condado de Washoe: datos públicos del Washoe County Assessor. Mapa de calles de <a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> (OpenMapTiles, datos de OpenStreetMap). Búsqueda de direcciones e imágenes de satélite de Esri; búsqueda de direcciones de respaldo del geocodificador de la Oficina del Censo de EE. UU. y de Nominatim. Radar meteorológico: NOAA NEXRAD, a través del Iowa Environmental Mesonet de Iowa State University. Piscinas estimadas desde el aire: derivadas de imágenes NAIP del USDA.',
    notsub: 'No reemplaza la supervisión, las alarmas en las puertas ni las clases de natación.',
    found: 'Haga una tarjeta "Si me encuentra" para la etiqueta del zapato (en inglés)',
    source: 'Código fuente en GitHub'
  },
  // Short strings used by the page's script, keyed by the English text. {n}-style slots are filled in.
  str: {
    'Hydro-Shield Water Map': 'Hydro-Shield: mapa del agua',
    'Map': 'Mapa', 'Satellite': 'Satélite', 'Weather radar': 'Radar meteorológico',
    '{name} edition': 'Edición del {name}',
    'Street address in {name}, {state}': 'Dirección en el {name}, {state}',
    'We could not find that address. Check the spelling, or click your home on the map instead.': 'No encontramos esa dirección. Revise cómo está escrita o haga clic en su casa en el mapa.',
    'The map data servers are busy right now, so lakes, ponds and canals could not load here. Please try again in a few minutes.': 'Los servidores de datos del mapa están ocupados en este momento, así que no se pudieron cargar los lagos, estanques y canales de esta zona. Inténtelo de nuevo en unos minutos.',
    'The map data servers are slow right now. Still trying…': 'Los servidores de datos del mapa van lentos en este momento. Seguimos intentando…',
    'at home': 'en casa', 'Home': 'Casa', '{d} from home': 'a {d} de la casa', 'none': 'ninguna',
    'No mapped water in this radius. Check your street in person anyway.': 'No hay agua en el mapa dentro de este radio. Revise su calle en persona de todos modos.',
    'Lakes, ponds and canals did not load (map data servers busy). Try again in a few minutes, and check your street in person.': 'Los lagos, estanques y canales no cargaron (servidores de datos ocupados). Inténtelo de nuevo en unos minutos y revise su calle en persona.',
    'Loading water data around {label}…': 'Cargando el agua alrededor de {label}…',
    'Zoom in until you can see the streets, then tap the home.': 'Acerque el mapa hasta ver las calles y luego toque la casa.',
    'the map center': 'el centro del mapa', 'the point you clicked': 'el punto que tocó', 'your location': 'su ubicación',
    '{n} water hazards within {r}, nearest first.': '{n} peligros de agua a menos de {r}, del más cercano al más lejano.',
    'Showing only what did load: {n} water hazards within {r}.': 'Solo se muestra lo que sí cargó: {n} peligros de agua a menos de {r}.',
    '{n} pools from county records.': '{n} piscinas de registros del condado.',
    '{n} pools from OpenStreetMap (pool coverage here is partial).': '{n} piscinas de OpenStreetMap (aquí la cobertura de piscinas es parcial).',
    '{n} pools estimated from aerial photos (may include errors; please verify).': '{n} piscinas estimadas a partir de fotos aéreas (puede haber errores; verifíquelas, por favor).',
    'Tap the map where the water is…': 'Toque el mapa donde está el agua…',
    '+ Mark water I know about': '+ Marcar agua que conozco',
    'Enter a home address first.': 'Primero escriba la dirección de una casa.',
    'Finding the address…': 'Buscando la dirección…',
    'Link copied ✓': 'Enlace copiado ✓', 'Copy this link:': 'Copie este enlace:', 'Copy link': 'Copiar enlace',
    'Point on map ({lat}, {lon})': 'Punto en el mapa ({lat}, {lon})',
    'Your location ({lat}, {lon})': 'Su ubicación ({lat}, {lon})',
    'Pool': 'Piscina', 'Pond / other water': 'Estanque / otra agua', 'Our pool (OK with an adult)': 'Nuestra piscina (segura con un adulto)',
    'Saved as your pool: shown in green, still covered by the alarm when he is alone or at night.': 'Guardada como su piscina: aparece en verde y la alarma la sigue cubriendo cuando está solo o de noche.',
    'Saved on this device. It now counts in your water list.': 'Guardado en este dispositivo. Ya cuenta en su lista de agua.',
    'Finding your location…': 'Buscando su ubicación…',
    'Location is turned off for this app. Allow it in your phone settings, or type an address.': 'La ubicación está desactivada para esta app. Actívela en la configuración del teléfono o escriba una dirección.',
    'Could not get your location. Type an address or tap the map.': 'No se pudo obtener su ubicación. Escriba una dirección o toque el mapa.',
    'Tap Use my location, type an address, or tap the map.': 'Toque Usar mi ubicación, escriba una dirección o toque el mapa.',
    'Type a home address above, or click a home on the map.': 'Escriba arriba la dirección de una casa o haga clic en una casa en el mapa.',
    // Names and kinds of water (hazards.js and the page script name them in English).
    'Retention / stormwater pond': 'Estanque de retención / pluvial', 'Pond': 'Estanque', 'Lake': 'Lago', 'Reservoir': 'Embalse',
    'Canal': 'Canal', 'Drainage ditch': 'Zanja de drenaje', 'Drainage channel': 'Canal de drenaje', 'Stream / creek': 'Arroyo',
    'River': 'Río', 'Swimming pool': 'Piscina', 'Water park': 'Parque acuático', 'Fountain': 'Fuente', 'Open water': 'Agua abierta',
    'Wetland': 'Humedal', 'Private pool': 'Piscina privada',
    'Spa / hot tub (county record)': 'Spa / jacuzzi (registro del condado)', 'Pool (OpenStreetMap)': 'Piscina (OpenStreetMap)',
    'Pool (county record)': 'Piscina (registro del condado)', 'Pool (aerial estimate)': 'Piscina (estimación aérea)',
    'Our pool': 'Nuestra piscina', 'Pool you marked': 'Piscina que usted marcó', 'Water you marked': 'Agua que usted marcó',
    'Estimated from aerial photos. May be wrong; please verify.': 'Estimada a partir de fotos aéreas. Puede estar equivocada; verifíquela, por favor.',
    'Safe with an adult nearby. Alarm still covers it alone or at night.': 'Segura con un adulto cerca. La alarma la sigue cubriendo cuando está solo o de noche.'
  }
};

// Text in the current language. v fills {slots}.
function hsT(s, v) {
  var o = (HS_LANG === 'es' && HS_ES.str[s]) || s;
  if (v) o = o.replace(/\{(\w+)\}/g, function (m, k) { return v[k] != null ? v[k] : m; });
  return o;
}
// Swap the page's fixed text: data-i18n="key" (contents) and data-i18n-attr="attr:key;attr:key".
function hsApplyLang() {
  document.documentElement.lang = HS_LANG;
  document.querySelectorAll('[data-i18n]').forEach(function (el) {
    var k = el.getAttribute('data-i18n'); if (el._hsEn == null) el._hsEn = el.innerHTML;
    el.innerHTML = HS_LANG === 'es' && HS_ES.html[k] ? HS_ES.html[k] : el._hsEn;
  });
  document.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
    el._hsEnA = el._hsEnA || {};
    el.getAttribute('data-i18n-attr').split(';').forEach(function (pair) {
      var p = pair.split(':'), a = p[0], k = p[1];
      if (!(a in el._hsEnA)) el._hsEnA[a] = el.getAttribute(a);
      el.setAttribute(a, HS_LANG === 'es' && HS_ES.html[k] ? HS_ES.html[k] : el._hsEnA[a]);
    });
  });
}
