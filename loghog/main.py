
from __future__ import print_function
import signal, atexit, os, logging, logging.handlers, sys, pwd, errno
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from server import Server
from writer import Writer
from processor import Processor
from facilities import FacilityDB, FacilityError
from daemon import daemonize, write_pid, drop_privileges

from ext.groper import define_opt, options, init_options, generate_sample_config

define_opt('main', 'help', type=bool, cmd_name='help', cmd_short_name='h', cmd_group='help', is_help=True)
define_opt('main', 'generate_config', type=bool, cmd_name='gen-config', cmd_group='gen-config', cmd_only=True)

define_opt('main', 'check_config', type=bool, cmd_name='check-config', cmd_only=True)
define_opt('main', 'config', cmd_name='config', cmd_short_name='c', is_config_file=True, cmd_only=True)
define_opt('main', 'facilities_config', cmd_name='facilities-config', cmd_short_name='F')
define_opt('main', 'pidfile', cmd_name='pid', cmd_short_name='p', default='loghogd.pid')
define_opt('main', 'daemon', type=bool, cmd_name='daemon', cmd_short_name='d')
define_opt('main', 'user', cmd_name='user', default='loghog')

define_opt('main', 'logdir', cmd_name='log-dir', cmd_short_name='L', default='/var/log/loghogd')
define_opt('main', 'workdir', cmd_name='work-dir', default='/var/lib/loghogd')
define_opt('main', 'rundir', cmd_name='work-dir', default='/var/run/loghogd')

define_opt('log', 'filename', cmd_name='log', cmd_short_name='l', default='/var/log/loghogd/loghogd.log')
define_opt('log', 'backup_count', type=int, default=14)
define_opt('log', 'when', default='midnight')

def shutdown(signum, server, writer):
    logger = logging.getLogger()
    logger.info('Recevied signal %d. Shutting down.', signum)
    server.close()
    writer.close()
    logger.info('Shutdown complete. Exiting.')

def reload_config(signum, facility_db, writer):
    logger = logging.getLogger()
    logger.info('Recevied signal %d. Reloading.', signum)
    facility_db.reload()
    writer.reload()
    logger.info('Reload complete.')

# These simply change the function signature, creating necessary closures
make_shutdown_handler = lambda server, writer: lambda signum, frame: shutdown(signum, server, writer)
make_reload_handler = lambda facility_db, writer: lambda signum, frame: reload_config(signum, facility_db, writer)

def exit_handler():
    if options.main.pidfile:
        try:
            os.unlink(options.main.pidfile)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass # No such file or directory

def setup_logging():
    logger = logging.getLogger()

    handler = logging.handlers.TimedRotatingFileHandler(filename=options.log.filename, when=options.log.when, backupCount=options.log.backup_count, utc=True)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if not options.main.daemon:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(logging.DEBUG)

def create_dirs():
    '''Pre-creates necessary directories and chowns them if necessary.'''

    dirs = [
        os.path.dirname(options.log.filename),
        options.main.rundir,
        options.main.logdir,
        options.main.workdir,
    ]

    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)

    pwnam = pwd.getpwnam(options.main.user)
    uid, gid = (pwnam[2], pwnam[3])

    if uid != os.getuid() or gid != os.getgid():
        for d in dirs:
            for root, subdirs, files in os.walk(d):
                for x in dirs + files:
                    os.chown(os.path.join(root, x), uid, gid)

def main():
    init_options()
    atexit.register(exit_handler)
    
    if options.main.generate_config:
        print(generate_sample_config()) # XXX: this doesn't yet work properly because of groper
        sys.exit()

    facility_db = FacilityDB()
    try:
        facility_db.load_config(options.main.facilities_config)
    except (FacilityError, configparser.Error) as e:
        sys.stderr.write("{} contains errors:\n\n".format(options.main.facilities_config))

        if hasattr(e, 'lineno'):
            e = 'Error on line {}: {}'.format(e.lineno, e.message.split("\n")[0].strip())

        sys.stderr.write("{}\n\n".format(e))
        sys.stderr.write("Exiting now.\n")
        sys.stderr.flush()
        sys.exit(os.EX_CONFIG)

    if options.main.check_config:
        sys.exit() # We are just checking the config file, so exit here.

    create_dirs()

    if options.main.daemon:
        daemonize()

    if options.main.pidfile:
        write_pid(options.main.pidfile)

    if options.main.user:
        drop_privileges(options.main.user)

    setup_logging()

    try:
        logging.getLogger().info("Starting loghogd.")

        writer = Writer(facility_db, options.main.logdir)
        processor = Processor(facility_db, writer)

        server = Server(
            processor.on_message,
            ipv6_addrs=[('::1', 8888)],
            ipv4_addrs=[('127.0.0.1', 8888)],
            unix_sockets=['/var/tmp/loghog.sock',],
            keyfile='thestral.local.key',
            certfile='thestral.local.crt',
            cafile=None
        )

        signal_handler = make_shutdown_handler(server, writer)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        signal.signal(signal.SIGHUP, make_reload_handler(facility_db, writer))

        server.run()
    except Exception as e:
        logging.getLogger().exception(e)
        logging.getLogger().error('Exiting abnormally due to an error.')
        raise

if __name__ == '__main__':
    main()

