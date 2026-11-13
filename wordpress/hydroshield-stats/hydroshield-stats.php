<?php
/**
 * Plugin Name: Hydro-Shield Stats
 * Description: Counts how often the Hydro-Shield Water Map is opened and searched, and how often "If found" cards are viewed. Stores only daily totals: no addresses, IP addresses, cookies or locations. Totals update once an hour.
 * Version: 1.1.0
 * Author: Give Kids A Voice
 */
if (!defined('ABSPATH')) exit;

const HSS_OPTION = 'hydroshield_stats_daily';           // [ 'YYYY-MM-DD' => [ 'view' => n, 'search' => n, 'card' => n ] ]
const HSS_EVENTS = ['view' => 'Map opened', 'search' => 'Searches', 'card' => '"If found" cards viewed'];
const HSS_ORIGINS = ['https://hydroshield.givekidsavoice.org', 'https://give-kids-a-voice.github.io'];

add_action('rest_api_init', function () {
    register_rest_route('hydroshield/v1', '/hit', [
        'methods' => ['POST', 'GET'],
        'permission_callback' => '__return_true',
        'callback' => 'hss_hit',
    ]);
});

// Pings are counted in small per-hour files (one byte per ping), by hit.php in this folder (the map's address
// for the ping, which skips loading WordPress) and by this older REST address, still used by copies of the
// map installed before version 1.1. Once an hour the finished hours are added to the daily totals.
function hss_dir() { return WP_CONTENT_DIR . '/uploads/hydroshield-hits'; }

function hss_hit(WP_REST_Request $r) {
    $e = sanitize_key($r->get_param('e'));
    if (!isset(HSS_EVENTS[$e])) return new WP_REST_Response(null, 204);
    // Count only. Nothing about the visitor is read or stored.
    $dir = hss_dir();
    if (is_dir($dir) || wp_mkdir_p($dir)) @file_put_contents($dir . '/' . $e . '-' . gmdate('YmdH'), '.', FILE_APPEND | LOCK_EX);
    return new WP_REST_Response(null, 204);
}

// Add every finished hour's counts to the daily totals, then delete those files.
function hss_fold() {
    $dir = hss_dir();
    if (!is_dir($dir)) return;
    if (!file_exists($dir . '/index.php')) @file_put_contents($dir . '/index.php', "<?php // Silence.\n");
    if (!file_exists($dir . '/.htaccess')) @file_put_contents($dir . '/.htaccess', "<IfModule mod_authz_core.c>\nRequire all denied\n</IfModule>\n<IfModule !mod_authz_core.c>\nDeny from all\n</IfModule>\n");
    $hour = gmdate('YmdH'); $minute = gmdate('YmdHi');
    $add = [];
    foreach ((array) scandir($dir) as $f) {
        if (preg_match('/^m-(\d{12})$/', $f, $m)) { if ($m[1] < $minute) @unlink("$dir/$f"); continue; }
        if (!preg_match('/^([a-z]+)-(\d{10})$/', $f, $m) || !isset(HSS_EVENTS[$m[1]]) || $m[2] >= $hour) continue;
        clearstatcache(true, "$dir/$f");
        $n = intval(@filesize("$dir/$f"));
        $t = DateTime::createFromFormat('YmdH', $m[2], new DateTimeZone('UTC'));
        if ($t) { $day = wp_date('Y-m-d', $t->getTimestamp()); $add[$day][$m[1]] = ($add[$day][$m[1]] ?? 0) + $n; }
        @unlink("$dir/$f");
    }
    if (!$add) return;
    $d = get_option(HSS_OPTION, []);
    if (!is_array($d)) $d = [];
    foreach ($add as $day => $c) foreach ($c as $e => $n) $d[$day][$e] = intval($d[$day][$e] ?? 0) + $n;
    if (count($d) > 800) { ksort($d); $d = array_slice($d, -800, null, true); }   // keep ~2 years of daily totals
    update_option(HSS_OPTION, $d, false);
}
add_action('hss_fold', 'hss_fold');
// A plugin update doesn't run the activation hook, so make sure the hourly job exists on every load.
add_action('init', function () { if (!wp_next_scheduled('hss_fold')) wp_schedule_event(time() + 300, 'hourly', 'hss_fold'); });
register_activation_hook(__FILE__, function () { wp_mkdir_p(hss_dir()); });
register_deactivation_hook(__FILE__, function () { hss_fold(); wp_clear_scheduled_hook('hss_fold'); });

// Allow the map's domain to send the counter ping
add_filter('rest_pre_serve_request', function ($served, $result, $request) {
    if (strpos($request->get_route(), '/hydroshield/v1/') === 0) {
        $o = $_SERVER['HTTP_ORIGIN'] ?? '';
        if (in_array($o, HSS_ORIGINS, true)) {
            header('Access-Control-Allow-Origin: ' . $o);
            header('Vary: Origin');
        }
    }
    return $served;
}, 10, 3);

function hss_sum($d, $days) {
    $out = array_fill_keys(array_keys(HSS_EVENTS), 0);
    $since = $days ? wp_date('Y-m-d', strtotime('-' . ($days - 1) . ' days', current_time('timestamp'))) : '0000-00-00';
    foreach ($d as $day => $c) if ($day >= $since) foreach ($out as $k => $_) $out[$k] += intval($c[$k] ?? 0);
    return $out;
}

add_action('wp_dashboard_setup', function () {
    if (!current_user_can('edit_posts')) return;
    wp_add_dashboard_widget('hydroshield_stats', 'Hydro-Shield Water Map use', function () {
        hss_fold();
        $d = get_option(HSS_OPTION, []); if (!is_array($d)) $d = [];
        $rows = ['Today' => 1, 'Last 7 days' => 7, 'Last 30 days' => 30, 'All time' => 0];
        echo '<table class="widefat striped" style="margin-bottom:10px"><thead><tr><th></th>';
        foreach (HSS_EVENTS as $label) echo '<th style="text-align:right">' . esc_html($label) . '</th>';
        echo '</tr></thead><tbody>';
        foreach ($rows as $label => $days) {
            $s = hss_sum($d, $days);
            echo '<tr><td>' . esc_html($label) . '</td>';
            foreach ($s as $v) echo '<td style="text-align:right;font-variant-numeric:tabular-nums">' . number_format_i18n($v) . '</td>';
            echo '</tr>';
        }
        echo '</tbody></table>';
        // Last 14 days of searches as a simple bar list
        $max = 1; $days14 = [];
        for ($i = 13; $i >= 0; $i--) { $k = wp_date('Y-m-d', strtotime("-$i days", current_time('timestamp'))); $v = intval($d[$k]['search'] ?? 0); $days14[$k] = $v; $max = max($max, $v); }
        echo '<p style="margin:6px 0 4px"><strong>Searches, last 14 days</strong></p><div style="display:flex;align-items:flex-end;gap:3px;height:60px">';
        foreach ($days14 as $k => $v) echo '<div title="' . esc_attr($k . ': ' . $v) . '" style="flex:1;background:#1f78b4;height:' . max(2, round(56 * $v / $max)) . 'px;border-radius:2px"></div>';
        echo '</div><p class="description" style="margin-top:8px">Totals update once an hour. Counts only. The map sends no addresses, IP addresses, cookies or locations. <a href="https://hydroshield.givekidsavoice.org" target="_blank" rel="noopener">Open the map</a></p>';
    });
});
