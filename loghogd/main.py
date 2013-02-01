
from __future__ import print_function, with_statement
import signal, atexit, os, logging, logging.handlers, sys, pwd, errno
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from server import Server
from writer import Writer
from processor import Processor
from facilities import FacilityDB, FacilityError
from compressor import Compressor
from daemon import daemonize, write_pid, drop_privileges
from util import normalize_path, get_file_md5

from ext.groper import define_opt, options, init_options, generate_sample_config, OptionsError, usage

define_opt('main', 'help', type=bool, cmd_name='help', cmd_short_name='h', cmd_group='help', is_help=True)
define_opt('main', 'generate_config', type=bool, cmd_name='gen-config', cmd_group='gen-config', cmd_only=True)

define_opt('main', 'check_config', type=bool, cmd_name='check-config', cmd_only=True)
define_opt('main', 'config', cmd_name='config', cmd_short_name='c', is_config_file=True, cmd_only=True)
define_opt('main', 'facilities_config', cmd_name='facilities-config', cmd_short_name='F')
define_opt('main', 'pidfile', cmd_name='pid', cmd_short_name='p', default='loghogd.pid')
define_opt('main', 'daemon', type=bool, cmd_name='daemon', cmd_short_name='d')
define_opt('main', 'user', cmd_name='user', default=None)

define_opt('main', 'logdir', cmd_name='log-dir', cmd_short_name='L', default='/var/log/loghogd')
define_opt('main', 'workdir', cmd_name='work-dir', default='/var/lib/loghogd')
define_opt('main', 'rundir', cmd_name='run-dir', default='/var/run/loghogd')

define_opt('log', 'filename', cmd_name='log', cmd_short_name='l', default='/var/log/loghogd/loghogd.log')
define_opt('log', 'backup_count', type=int, default=14)
define_opt('log', 'when', default='midnight')
define_opt('log', 'level', default='INFO')

cached_config_md5 = None

def shutdown(signum, server, writer, compressor):
    '''Gracefully shuts down LogHog.'''

    if signum:
        logging.getLogger().info('Recevied signal {}. Shutting down.'.format(signum))
    server.shutdown()
    writer.close()
    compressor.shutdown()

def reload_config(signum, facility_db, writer):
    '''Reloads process configuration if possible.'''

    logger = logging.getLogger()
    logger.info('Recevied signal %d.', signum)

    if get_file_md5(options.main.config) != cached_config_md5:
        logger.warning('The main config file ({0}) has changed.'.format(options.main.config))
        logger.warning('Online reloading of the config file is not supported.')
        logger.warning('Please restart the process instead.')
        return

    facility_db.reload()
    writer.reload()
    logger.info('Reload complete.')

# These simply change the function signature, creating necessary closures
make_shutdown_handler = lambda server, writer, compressor: lambda signum, frame: shutdown(signum, server, writer, compressor)
make_reload_handler = lambda facility_db, writer: lambda signum, frame: reload_config(signum, facility_db, writer)

def exit_handler():
    '''Cleanup routine. This function runs right before loghogd is about to exit.'''

    if options.main.pidfile:
        try:
            os.unlink(options.main.pidfile)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass # No such file or directory

def setup_logging():
    '''Sets up internal logging. Run this once at startup.'''

    logger = logging.getLogger()

    handler = logging.handlers.TimedRotatingFileHandler(filename=options.log.filename, when=options.log.when, backupCount=options.log.backup_count, utc=True)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if not options.main.daemon:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    level = getattr(logging, options.log.level.upper())
    logger.setLevel(level)

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

    if not options.main.user:
        return

    pwnam = pwd.getpwnam(options.main.user)
    uid, gid = (pwnam[2], pwnam[3])

    if uid != os.getuid() or gid != os.getgid():
        for d in dirs:
            for root, subdirs, files in os.walk(d):
                for x in dirs + files:
                    os.chown(os.path.join(root, x), uid, gid)

def cache_config_checksum():
    '''Cached the checksum of the config file in case we receive SIGHUP.'''

    global cached_config_md5
    cached_config_md5 = get_file_md5(options.main.config)

def main():
    try:
        init_options()
    except OptionsError as e:
        sys.stderr.write("Error: {0}\n\n".format(e))
        sys.stderr.write(usage())
        sys.stderr.write("\n");
        sys.stderr.flush()
        sys.exit(os.EX_CONFIG)
        
    if options.main.generate_config:
        print(generate_sample_config()) # XXX: this doesn't yet work properly because of groper
        sys.exit()

    conf_root = os.path.dirname(os.path.abspath(options.main.config))

    facility_db = FacilityDB()
    try:
        facility_db.load_config(normalize_path(options.main.facilities_config, conf_root))
    except (IOError) as e:
        sys.stderr.write("Error reading {0}: {1}\n".format(options.main.facilities_config, e))
        sys.stderr.flush()
        sys.exit(os.EX_CONFIG)
    except (FacilityError, configparser.Error) as e:
        sys.stderr.write("{0} contains errors:\n\n".format(options.main.facilities_config))

        if hasattr(e, 'lineno'):
            e = 'Error on line {0}: {1}'.format(e.lineno, e.message.split("\n")[0].strip())

        sys.stderr.write("{0}\n\n".format(e))
        sys.stderr.write("Exiting now.\n")
        sys.stderr.flush()
        sys.exit(os.EX_CONFIG)

    if options.main.check_config:
        sys.exit() # We are just checking the config file, so exit here.

    cache_config_checksum()
    create_dirs()

    if options.main.daemon:
        daemonize()

    if options.main.user:
        drop_privileges(options.main.user)

    if options.main.pidfile:
        write_pid(options.main.pidfile)
        atexit.register(exit_handler)

    setup_logging()

    try:
        logging.getLogger().info("Starting loghogd.")

        compressor = Compressor()
        compressor.find_uncompressed(options.main.logdir, r'.+\.log\..+')

        writer = Writer(facility_db, compressor, options.main.logdir)
        processor = Processor(facility_db, writer)

        server = Server(processor.on_message, conf_root)

        signal_handler = make_shutdown_handler(server, writer, compressor)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        signal.signal(signal.SIGHUP, make_reload_handler(facility_db, writer))
    except Exception as e:
        logging.getLogger().error(e)
        logging.getLogger().error('Exiting abnormally due to an error at startup.')
        sys.exit(os.EX_CONFIG)

    try:
        compressor.start()
        server.run()
    except Exception as e:
        logging.getLogger().exception(e)
        logging.getLogger().error('Exiting abnormally due to an error at runtime.')
        shutdown(None, server, writer, compressor)
        sys.exit(os.EX_SOFTWARE)
    
    logging.getLogger().info('Shutdown complete. Exiting.')

if __name__ == '__main__':
    main()

