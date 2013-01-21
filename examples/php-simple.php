<?php

$CURDIR = dirname(__file__);
require_once( dirname($CURDIR) . '/clients/loghog.php');

$logger = new Loghog('my-first-app');

while (1) {
    $logger->debug('And %s and %s and %s', '1', 'b', 'C');
    sleep(1);
}
