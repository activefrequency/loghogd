
from __future__ import print_function
import os, datetime, time, logging, errno

from scheduler import Scheduler

class LogFile(object):
    '''Instances of this class represent log files and their backups.

    This class is able to write to the corresponding log file and rotate it.
    '''

    def __init__(self, filename, scheduler, compressed_extension, backup_count, max_size, rotate, flush_every):
        '''Initializes and opens a LogFile instance.'''
        
        self.log = logging.getLogger('writer.log_file') # internal logger

        self.filename = filename
        self.scheduler = scheduler
        self.compressed_extension = compressed_extension
        self.backup_count = backup_count
        self.max_size = max_size
        self.rotate = rotate
        self.flush_every = flush_every

        self.dirty_writes = 0
        self.size = 0
        self.file = None

        self.open()

    def open(self):
        '''Opens a file and creates the necessary records in the dbm database.'''

        try:
            os.makedirs(os.path.dirname(self.filename))
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass # Dir already exists
            else:
                raise
        try:
            fd = os.open(self.filename, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o644)
            
            # File does not exist
            self.scheduler.record_execution(self.filename, time.time())
            self.file = os.fdopen(fd, 'a', 0o644)
        except OSError as e:
            if e.errno == errno.EEXIST: # File exists
                self.file = open(self.filename, 'a', 0o644)
            else:
                raise

        self.size = os.stat(self.filename).st_size

    def close(self):
        '''Closes the log file.'''

        self.file.close()

    def write(self, data):
        '''Writes data to the file.'''
        
        self.file.write(data)
        self.dirty_writes += 1
        self.size += len(data)
        
        if self.dirty_writes >= self.flush_every:
            self.file.flush()
            self.dirty_writes = 0

    def should_rotate(self):
        '''Figures out if the given file should be rotated.

        :param f: file dict, as generated in Writer.open()
        :return: bool
        '''

        if self.rotate == 'size':
            return self.size >= self.max_size

        now = time.time()
        
        next_rotation_at = self.scheduler.get_next_execution(self.filename, self.rotate, now)

        return next_rotation_at < now

    def do_rotate(self):
        '''Performs the file rotation.'''

        self.log.info('Rotating {0} based on "{1}"'.format(self.filename, self.rotate))
        
        try:
            # Close the file before renaming it
            self.close()

            last_rotation_dt = datetime.datetime.fromtimestamp(self.scheduler.get_last_execution(self.filename))
            new_name = '{0}.{1}'.format(self.filename, last_rotation_dt.strftime('%Y-%m-%d-%H-%M-%S-%f'))
            self._rename(self.filename, new_name)

            self.remove_old_backups()

            return new_name
        finally:
            # Make sure that no matter what we try to open the file
            self.open()

    def remove_old_backups(self):
        '''Removes old backups after a file rotation.'''

        prefix = os.path.basename(self.filename)
        all_files = []
        for root, dirs, files in os.walk(os.path.dirname(self.filename)):
            for filename in files:
                if filename.startswith(prefix):
                    filename = os.path.join(root, filename)
                    all_files.append(filename)

        all_files.sort()

        to_remove = all_files[:-self.backup_count]

        for filename in to_remove:
            os.unlink(filename)

    def _rename(self, src, dst):
        '''Renames src to dst if src exists.'''

        try:
            os.rename(src, dst)
        except OSError as e:
            if e.errno == errno.ENOENT:
                return # No such file or directory
            else:
                raise

        self.log.debug('Renamed {0} to {1}'.format(src, dst))

class Writer(object):
    '''Main writer class.

    A single instance of this class is typically used to dispatch writes to
    the appropriate LogFile instances.
    '''

    def __init__(self, facility_db, compressor, log_dir):
        '''Initializes a Writer instance.
        
        Take care not to initialize multiple writer instances for the same files.'''

        self.facility_db = facility_db
        self.files = {}

        self.log_dir = log_dir

        self.scheduler = Scheduler()

        self.compressor = compressor

        self.log = logging.getLogger('writer') # internal logger

    def write(self, app_id, mod_id, msg):
        '''Write the message to the appropriate file.'''

        facility = self.facility_db.get_facility(app_id, mod_id)

        log_file = self.get_file(msg['hostname'], facility)

        if log_file.should_rotate():
            rotated_filename = log_file.do_rotate()
            self.compressor.compress(rotated_filename)

        s = u'{0!s} - {1!s} - {2!s}\n'.format(datetime.datetime.now(), msg['hostname'], msg['body']).encode('utf8')

        log_file.write(s)

    def get_filename(self, hostname, facility):
        '''Returns the log filename given a hostname.'''

        if facility.file_per_host:
            return os.path.join(self.log_dir, facility.app_id, '{0}-{1}.log'.format(hostname, facility.mod_str))
        else:
            return os.path.join(self.log_dir, facility.app_id, '{0}.log'.format(facility.mod_str))

    def get_file(self, hostname, facility):
        '''Returns a LogFile instance that should be used.

        Uses the hostname and the Facility instance to determine which filename
        should be used, and if it is not already present creates an instance of
        LogFile.
        '''

        filename = self.get_filename(hostname, facility)

        if filename not in self.files:
            self.files[filename] = LogFile(
                filename=filename,
                scheduler=self.scheduler,
                compressed_extension=self.compressor.extension,
                backup_count=facility.backup_count,
                max_size=facility.max_size,
                rotate=facility.rotate,
                flush_every=facility.flush_every
            )

        return self.files[filename] 

    def reload(self):
        '''Closes and re-opens all files. Useful during a config reload.'''

        self.close()

    def close(self):
        '''Close all files.'''

        for filename, log_file in self.files.items():
            log_file.close()

            del self.files[filename]

