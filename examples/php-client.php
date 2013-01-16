<?php

require_once( dirname(dirname(__file__)) . '/clients/loghog.php');


$logger = new Loghog('qq');

$logger->debug('And %s and %s and %s', '1', 'b', 'C');

