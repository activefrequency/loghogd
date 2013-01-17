<?php

require_once( dirname(dirname(__file__)) . '/clients/loghog.php');


$logger = new Loghog('proga', array('secret' => 'qqq1', 'mode' => Loghog::STREAM));

while (1) {
    $logger->debug('And %s and %s and %s', '1', 'b', 'C');
    sleep(1);
}
