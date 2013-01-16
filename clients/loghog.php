<?php

class Loghog {
    
    const LVL_DEBUG = 0;
    const LVL_INFO = 1;
    const LVL_WARNING = 2;
    const LVL_ERROR = 3;
    const LVL_CRITICAL = 4;

    const VERSION = 1;
    const DGRAM = 0x01;
    const STREAM = 0x02;

    const USE_GZIP = 0x01;

    const _FLAGS_GZIP = 0x01;

    const FORMAT = 'NNa%d';


    public function __construct($app_name, $address='localhost', $port=5566, $mode=Loghog::STREAM, $secret=null, $compression=false, $hostname=null, $ssl_info=null) {
        $this->app_name = $app_name;
        $this->address = $address;
        $this->port = $port;
        $this->mode = $mode;
        $this->secret = $secret;
        $this->compression = $compression;
        $this->hostname = $hostname;

        $this->keyfile = null;
        $this->certfile = null;
        $this->cafile = null;
        
        $this->flags = 0;
        if ($this->compression) {
            $this->flags |= self::FLAGS_GZIP;
        }
        
        $this->sock = null;
    }

    protected function make_socket($timeout=1.0) {
        if ($this->sock) {
            return;
        }

        $type = $this->mode == self::STREAM ? SOCK_STREAM : SOCK_DGRAM;
        $proto = $this->mode == self::STREAM ? SOL_TCP : SOL_UDP;

        $sock = socket_create(AF_INET, $type, $proto);
        if (!$sock) {
            return;
        }

        if (!socket_connect($sock, $this->address, $this->port)) {
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

        $payload = json_encode($data);

        if ($this->compression == self::USE_GZIP) {
            # XXX: implemnet
        }

        $size = strlen($payload);

        return pack(sprintf(self::FORMAT, $size), $size, $this->flags, $payload);
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

        if ($this->mode == self::STREAM) {
            $n = socket_write($this->sock, $msg, strlen($msg)); // XXX: need sendall
        }
        else if ($this->mode == self::DGRAM) {
            $n = socket_sendto($this->sock, $msg, strlen($msg), 0, $this->address, $this->port);
            if ($n === false) {
                socket_close($this->sock);
                $this->sock = null;
            }
        }

        echo $msg . "\n";
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

