

import signal, atexit, os, logging, logging.handlers, sys
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from server import Server
from writer import Writer
from processor import Processor
from facilities import FacilityDB, FacilityError
from daemon import daemonize, write_pid

from ext.groper import define_opt, options, init_options

define_opt('main', 'check_config', type=bool, cmd_name='check-config')
define_opt('main', 'facilities_config', cmd_name='facilities-config', cmd_short_name='F')
define_opt('main', 'pidfile', cmd_name='pid', cmd_short_name='p', default=None)
define_opt('main', 'daemon', type=bool, cmd_name='daemon', cmd_short_name='d')
define_opt('main', 'logdir', cmd_name='log-dir', cmd_short_name='L', default='/var/tmp/qqq')

define_opt('log', 'filename', cmd_name='log', cmd_short_name='l', default='/var/tmp/loghog.log')
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
        os.unlink(options.main.pidfile)

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

def main():
    init_options()
    atexit.register(exit_handler)

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

    if options.main.daemon:
        daemonize()

    if options.main.pidfile:
        write_pid(options.main.pidfile)

    setup_logging()

    try:
        logging.getLogger().info("Starting loghog.")

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

