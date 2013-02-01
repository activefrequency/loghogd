
import re, socket, os.path, hashlib

str_to_addrs = lambda s: tuple([x for x in [a.strip() for a in s.strip().split(',')] if x])

def parse_addrs(addrs_str, default_port):
    '''Parses comma separated list of addresses into an iterable of normalized address dicts.

    Examples of params and results are:
        ('[::1], [::2]', 5566) => [{'host': '::1', 'port': 5566}, {'host': '::2', 'port': 5566}]
        ('[::1]:6677, [::2]', 5566) => [{'host': '::1', 'port': 6677}, {'host': '::2', 'port': 5566}]
    '''

    addrs = str_to_addrs(addrs_str)
    
    normalize = lambda a: normalize_inet_addr(a, default_port)

    result = []
    for (address, port) in map(normalize, addrs):
        result.append({'host': address, 'port': port, })

    return result
    
def normalize_inet_addr(addr, default_port):
    '''Takes in an IP address string and a default port and returns a normalized (addr, port) tuple.'''

    addr = addr.strip()

    IPV6_RE = r'\[([0-9:]+)\](?:\:(\d+))?'
    
    v6matches = re.match(IPV6_RE, addr)
    
    if v6matches:
        # IPv6 address
        addr, port_str = v6matches.groups()
        port = int(port_str) if port_str else default_port
    else:
        # IPv4 or hostname
        parts = addr.split(':')
        if len(parts) == 1:
            parts.append(default_port)

        addr, port = parts[0], int(parts[1])

    return addr, port

def format_connection_message(address, family, proto, use_ssl):
    '''Returns a formatted log message based on the given connection parameters.'''

    FAM_STRS = {
        socket.AF_INET: 'IPv4',
        socket.AF_INET6: 'IPv6',
        socket.AF_UNIX: 'UNIX',
    }

    PROTO_STRS = {
        (socket.AF_INET, socket.SOCK_STREAM, True): 'SSL/TLS',
        (socket.AF_INET6, socket.SOCK_STREAM, True): 'SSL/TLS',

        (socket.AF_INET, socket.SOCK_STREAM, False): 'TCP',
        (socket.AF_INET6, socket.SOCK_STREAM, False): 'TCP',
        (socket.AF_UNIX, socket.SOCK_STREAM, False): 'Stream',

        (socket.AF_INET, socket.SOCK_DGRAM, False): 'UDP',
        (socket.AF_INET6, socket.SOCK_DGRAM, False): 'UDP',
        (socket.AF_UNIX, socket.SOCK_DGRAM, False): 'Datagram',
    }

    ADDR_FORMATTER = {
        socket.AF_INET: lambda a: '{host}:{port}'.format(**address),
        socket.AF_INET6: lambda a: '[{host}]:{port}'.format(**address),
        socket.AF_UNIX: lambda a: a['filename'],
    }

    return 'Listening on a {0} {1} socket on {2}.'.format(FAM_STRS[family], PROTO_STRS[family, proto, use_ssl], ADDR_FORMATTER[family](address))

def pretty_addr(addr):
    '''Converts a full address as returned by socket.accept() to a human-readable format.'''

    if len(addr) == 2:
        return '{0}:{1}'.format(*addr)

    if len(addr) == 4:
        return '[{0}]:{1}'.format(*addr[:2])

def normalize_path(filename, conf_root):
    '''Returns the absolute path to a file.

    param filename : unicode
        If filename is an absolute path it is returned as is. Otherwise, it is 
        combined with conf_root to form an absolute path.
    param conf_root : unicode
        A directory where loghogd.conf lives.
    '''

    if os.path.isabs(filename):
        return filename

    return os.path.join(conf_root, filename)

def get_file_md5(filename):
    '''Returns the md5sum of a given file.'''

    with open(filename, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

