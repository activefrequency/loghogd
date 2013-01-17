
import re, socket

str_to_addrs = lambda s: tuple(filter(lambda x: x, map(lambda a: a.strip(), s.strip().split(','))))

def parse_addrs(addrs_str, default_port):
    addrs = str_to_addrs(addrs_str)
    
    normalize = lambda a: normalize_inet_addr(a, default_port)

    return map(normalize, addrs)
    
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

def format_connection_message(address, family, proto):
    '''Returns a formatted log message based on the given connection parameters.'''

    FAM_STRS = {
        socket.AF_INET: 'IPv4',
        socket.AF_INET6: 'IPv6',
        socket.AF_UNIX: 'UNIX',
    }

    PROTO_STRS = {
        (socket.AF_INET, socket.SOCK_STREAM): 'TCP',
        (socket.AF_INET6, socket.SOCK_STREAM): 'TCP',
        (socket.AF_UNIX, socket.SOCK_STREAM): 'Stream',

        (socket.AF_INET, socket.SOCK_DGRAM): 'UDP',
        (socket.AF_INET6, socket.SOCK_DGRAM): 'UDP',
        (socket.AF_UNIX, socket.SOCK_DGRAM): 'Datagram',
    }

    ADDR_FORMATTER = {
        socket.AF_INET: lambda a: '{}:{}'.format(*address),
        socket.AF_INET6: lambda a: '[{}]:{}'.format(*address),
        socket.AF_UNIX: lambda a: a,
    }

    return 'Listening on a {} {} socket on {}.'.format(FAM_STRS[family], PROTO_STRS[family, proto], ADDR_FORMATTER[family](address))

def pretty_addr(addr):
    '''Converts a full address as returned by socket.accept() to a human-readable format.'''

    if len(addr) == 2:
        return '{}:{}'.format(*addr)

    if len(addr) == 4:
        return '[{}]:{}'.format(*addr[:2])

