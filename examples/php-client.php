<?php

$CURDIR = dirname(__file__);
require_once( dirname($CURDIR) . '/clients/loghog.php');

$logger = new Loghog('proga', array(
    'secret' => 'qqq1',
    'mode' => Loghog::STREAM,
    'pemfile' => $CURDIR . '/certs/test-client.pem',
    'cafile' => $CURDIR . '/certs/loghog-ca.cert'
));

while (1) {
    $logger->debug('And %s and %s and %s', '1', 'b', 'C');
    sleep(1);
}
