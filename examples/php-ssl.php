<?php

$CURDIR = dirname(__file__);
require_once( dirname($CURDIR) . '/clients/loghog.php');

$logger = new Loghog('my-first-app', array(
    'port' => 5577,
    'pemfile' => $CURDIR . '/conf/certs/test-client.pem',
    'cacert' => $CURDIR . '/conf/certs/loghog-ca.cert'
));

while (1) {
    $logger->debug('And %s and %s and %s', '1', 'b', 'C');
    sleep(1);
}
