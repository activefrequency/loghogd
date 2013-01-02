
import os, sys, resource, errno

MAXFD = 2048

def close_open_files():
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd == resource.RLIM_INFINITY:
        maxfd = MAXFD

    for fd in reversed(range(maxfd)):
        try:
            os.close(fd)
        except OSError, e:
            if e.errno == errno.EBADF:
                pass # File not open
            else:
                raise Exception("Failed to close file descriptor %d: %s" % (fd, e))

def daemonize():
    try:
        os.umask(0o22)
    except Exception, e:
        raise Exception("Unable to change file creation mask: %s" % e)
    
    os.chdir('/')

    # First fork
    try:
        pid = os.fork()
        if pid > 0:
            os._exit(0)
    except OSError, e:
        raise Exception("Error on first fork: [%d] %s" % (e.errno, e.strerr,))
    
    os.setsid()
    
    # Second fork
    try:
        pid = os.fork()
        if pid > 0:
            os._exit(0)
    except OSError, e:
        raise Exception("Error on second fork: [%d] %s" % (e.errno, e.strerr,))
    
    close_open_files()
    os.dup2(os.open(os.devnull, os.O_RDWR), sys.stdin.fileno())
    os.dup2(os.open(os.devnull, os.O_RDWR), sys.stdout.fileno())
    os.dup2(os.open(os.devnull, os.O_RDWR), sys.stderr.fileno())

def write_pid(filename):
    fd = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_RDWR)
    os.write(fd, str(os.getpid()))
    os.close(fd)

