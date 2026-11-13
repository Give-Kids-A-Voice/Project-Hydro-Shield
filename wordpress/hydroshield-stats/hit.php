<?php
/**
 * Hydro-Shield Stats: the map's counter ping, answered without loading WordPress so a burst of traffic
 * can't slow the site down. Each ping adds one byte to a file for that event and hour (the file's size is
 * the count); the plugin folds finished hours into its daily totals once an hour.
 * Reads nothing about the visitor: no IP address, cookies, address or location.
 */
$events = ['view' => 1, 'search' => 1, 'card' => 1];
$e = isset($_GET['e']) ? (string) $_GET['e'] : '';
http_response_code(204);
header('Cache-Control: no-store');
if (!isset($events[$e])) exit;

$dir = dirname(__DIR__, 2) . '/uploads/hydroshield-hits';   // wp-content/uploads/hydroshield-hits
if (!is_dir($dir) && !@mkdir($dir, 0755, true)) exit;

// Flood guard: past 3,000 pings in one minute (bots, not families), stop counting until the next minute.
$minute = $dir . '/m-' . gmdate('YmdHi');
clearstatcache(true, $minute);
if (@filesize($minute) >= 3000) exit;
@file_put_contents($minute, '.', FILE_APPEND | LOCK_EX);
@file_put_contents($dir . '/' . $e . '-' . gmdate('YmdH'), '.', FILE_APPEND | LOCK_EX);
