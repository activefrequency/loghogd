<?php

class Loghog {
    
    const LVL_DEBUG = 0;
    const LVL_INFO = 1;
    const LVL_WARNING = 2;
    const LVL_ERROR = 3;
    const LVL_CRITICAL = 4;

    const VERSION = 1;

    const HMAC_DIGEST_ALGO = 'md5';

    protected static $HASHABLE_FIELDS = array('app_id', 'module', 'stamp', 'nsecs', 'body');

    const USE_GZIP = 0x01;

    const _FLAGS_GZIP = 0x01;

    const FORMAT = 'NNa*';

    const DEFAULT_PORT = 5566;


    public function __construct($app_name, $options = array()) {
        $this->app_name = $app_name;

        $this->address = isset($options['address']) ? $options['address'] : 'localhost';
        $this->port = isset($options['port']) ? $options['port'] : self::DEFAULT_PORT;
        $this->stream = isset($options['stream']) ? (bool) $options['stream'] : true;
        $this->secret = isset($options['secret']) ? $options['secret'] : null;
        $this->compression = isset($options['compression']) ? $options['compression'] : null;
        $this->hostname = isset($options['hostname']) ? $options['hostname'] : php_uname('n');

        $this->pemfile = isset($options['pemfile']) ? $options['pemfile'] : null;
        $this->cacert = isset($options['cacert']) ? $options['cacert'] : null;

        $this->flags = 0;
        if ($this->compression) {
            $this->flags |= self::FLAGS_GZIP;
        }
        
        $this->sock = null;
    }

    protected function resolve($address) {
        $records = dns_get_record($this->address);
        shuffle($records);

        foreach ($records as $record) {
            if ($record['type'] == 'A' ||  $record['type'] == 'AAAA') {
                return array(
                    'ip' => $record['type'] == 'A' ? $record['ip'] : $record['ipv6'],
                    'af' => $record['type'] == 'A' ? AF_INET : AF_INET6
                );
            }
        }

        return null;
    }

    protected function make_socket($timeout=1.0) {
        if ($this->sock) {
            return;
        }

        if ($this->pemfile) {
            $opts = array(
                'ssl' => array(
                    'allow_self_signed' => false,
                    'verify_peer' => true,
                    'cafile' => $this->cacert,
                    'local_cert' => $this->pemfile
                )
            );
            $sc = stream_context_create($opts);

            $addr = sprintf('tls://%s:%d', $this->address, $this->port);
            $sock = @stream_socket_client($addr, $errno, $errstr, 1, STREAM_CLIENT_CONNECT, $sc);
        }
        else {
            if ($this->stream) {
                $addr = sprintf('tcp://%s:%d', $this->address, $this->port);
                $sock = @stream_socket_client($addr);
            }
            else {
                $addr = sprintf('udp://%s', $this->address);
                $sock = @fsockopen($addr, $this->port);
            }
        }

        if (!$sock) {
            return;
        }

        $this->sock = $sock;
    }

    private function encode($msg) {
        $time = microtime(true);
        $secs = (int) $time;
        $msecs = $time - $secs;

        $data = array(
            'version' => self::VERSION,
            'app_id' => $this->app_name,
            'module' => '', # XXX
            'stamp' => $secs,
            'nsecs' => (int) ($msecs * pow(10, 9)),
            'hostname' => $this->hostname,
            'body' => $msg 
        );

        if ($this->secret) {
            foreach (self::$HASHABLE_FIELDS as $field) {
                $hashable[$field] = (string) $data[$field];
            }
            $hashable = implode('', $hashable);
            $data['signature'] = hash_hmac(self::HMAC_DIGEST_ALGO, $hashable, $this->secret);
        }

        $payload = json_encode($data);

        if ($this->compression == self::USE_GZIP) {
            $payload = gzcompress($payload);
        }

        $size = strlen($payload);

        return pack(self::FORMAT, $size, $this->flags, $payload);
    }

    protected function emit($level, $args) {
        if ($level < 0) {
            return; # XXX
        }

        $msg = $this->format($args);
        $encoded = $this->encode($msg);

        $this->send($encoded);
    }

    protected function send($msg) {
        $this->make_socket(); // XXX: Add exponential backoff
        if (!$this->sock) {
            return;
        }

        if ($this->stream) {
            $n = @fwrite($this->sock, $msg);
        }
        else {
            $n = @fwrite($this->sock, $msg);
        }
        
        if (!$n) {
            fclose($this->sock);
            $this->sock = null;
        }
    }

    protected function format($args) {
        return vsprintf($args[0], array_slice($args, 1));
    }

    public function debug() {
        $this->emit(self::LVL_DEBUG, func_get_args());
    }

    public function info() {
        $this->emit(self::LVL_DEBUG, func_get_args());
    }

    public function warning() {
        $this->emit(self::LVL_DEBUG, func_get_args());
    }

    public function error() {
        $this->emit(self::LVL_DEBUG, func_get_args());
    }

    public function critical() {
        $this->emit(self::LVL_DEBUG, func_get_args());
    }

    public function exception() {
        $this->emit(self::LVL_ERROR, func_get_args());
    }

}

