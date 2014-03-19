
from __future__ import with_statement, print_function
import threading, logging, os, errno, re, gzip
from subprocess import Popen, PIPE
from collections import deque
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

from ext.groper import define_opt, options

FALLBACK_COMPRESSOR = 'gzip'
STREAM_COMPRESSOR = 'gzip'

# Try to use xz by default. It provides the best compression/speed ratio
define_opt('compressor', 'format', default='xz')
define_opt('compressor', 'level', type=int, default=6)
define_opt('compressor', 'compress_on_write', type=bool)

class CompressorStartupError(Exception):
    '''Raised by Compressor instances if a misconfigruation is detected.'''

class Compressor(object):
    '''Class used for compressing external files.
    
    Typically a single instance of this class will run in a separate thread.
    Requests for file compression will be sent to it via the input queue.'''

    COMPRESS_LIBS = set((
        'gzip',
        'bzip2',
        'xz',
    ))

    COMPRESS_EXTS = {
        'gzip': '.gz',
        'bzip2': '.bz2',
        'xz': '.xz',
    }

    def __init__(self, compress_cmd=None, level=None):
        '''Initializes the Compressor instance.'''

        self.queue = Queue()
        self.do_shutdown = False
        self.log = logging.getLogger('compressor')

        self.files_to_compress = deque()

        self.compress_cmd = compress_cmd or options.compressor.format

        if self.compress_cmd not in self.COMPRESS_LIBS:
            raise CompressorStartupError('{0} is not a valid compression format.'.format(self.compress_cmd))
    
        self.discover_available_compressors()

        self.compress_level = level or options.compressor.level
        if not (0 <= self.compress_level <= 9):
            raise CompressorStartupError('The compression level must be between 0 and 9 incluse. It is set to {0}.'.format(self.compress_level))

        if options.compressor.compress_on_write:
            # Note: this command will not actually be used. Instead
            # we will wrap the file object in the compressor of the appropriate type
            self.compress_cmd = STREAM_COMPRESSOR
            self.log.info('Streaming compression enabled using {0}'.format(STREAM_COMPRESSOR))

        self.extension = self.COMPRESS_EXTS[self.compress_cmd]

    def start(self):
        '''Starts the Compressor thread.'''

        t = threading.Thread(target=self.run)
        #t.daemon = True
        t.start()

    def shutdown(self):
        '''Signals the Compressor thread to shut down.
        
        Note that there are two ways to do this. First, we set do_shutdown to True.
        Second, we put None on the input queue. The reason for this is that we 
        don't always have to check the queue for the shutdown event.
        '''
        
        self.do_shutdown = True
        self.queue.put(None)

    def compress(self, filename):
        '''Requests compression for a given file.'''

        # Putting None on the queue means "shut down now"
        if filename:
            if not options.compressor.compress_on_write:
                self.queue.put(filename)

    def call(self, cmd, stdout=PIPE, stderr=PIPE):
        '''A wrapper around Popen. Returns (status, stdout, stderr).'''

        p = Popen(cmd, stdout=stdout, stderr=stderr)
        out, err = p.communicate()
        return (p.returncode, out, err)

    def run(self):
        '''Main evel loop for the Compressor thread.'''

        while True:
            try:
                if self.do_shutdown:
                    break

                if not self.files_to_compress:
                    filename = self.queue.get()

                    if self.do_shutdown:
                        break # Check after coming back from the queue

                    if filename not in self.files_to_compress:
                        self.files_to_compress.append(filename)

                filename = self.files_to_compress.popleft()
                if not os.path.exists(filename):
                    self.log.warning('File {0} not found. Messages coming in too fast?'.format(filename))
                    continue

                self.log.info('Compressing {0}'.format(filename))

                status, out, err = self.call([self.compress_cmd, filename])
                if self.do_shutdown:
                    self.log.info('Interrupted with shutdown signal while compressing {0}!'.format(filename))
                    break
                    
                if status:
                    self.log.info('Failing {0} failed. status was {1}\nstdout was:\n{2}\n\nstderr was:{3}\n'.format(filename, status, out, err))
                else:
                    self.log.info('Successfully compressed {0}'.format(filename))
            except Exception as e:
                self.log.exception(e)

    def find_uncompressed(self, path, regex):
        '''Finds files to compress in a given path using the regex and adds them to the compress queue.
        
        This is typically done at startup in case there were files that were 
        not fully compressed on shutdown.'''
        
        for root, dirs, files in os.walk(path):
            for filename in files:
                filename = os.path.join(root, filename)
                _, ext = os.path.splitext(filename)
                if ext in self.COMPRESS_EXTS.values():
                    continue

                if re.match(regex, filename):
                    self.compress(os.path.abspath(os.path.join(path, filename)))

    def discover_available_compressors(self):
        '''Discovers which compressors the system has available and raises if we cannot proceed.

        Typically, this method is run once at startup.'''

        missing_compressors = set()
        for exe in tuple(self.COMPRESS_LIBS):
            if not self.check_exec_exists(['which', exe]):
                missing_compressors.add(exe)

        if self.compress_cmd in missing_compressors and FALLBACK_COMPRESSOR not in missing_compressors:
            self.log.warning('Compressor {0} is missing from your system. Falling back to {1}.'.format(self.compress_cmd, FALLBACK_COMPRESSOR))
            self.compress_cmd = FALLBACK_COMPRESSOR
        elif self.compress_cmd in missing_compressors and FALLBACK_COMPRESSOR in missing_compressors:
            raise CompressorStartupError('Specified compressor {0} and default compressor {1} are not available.'.format(self.compress_cmd, FALLBACK_COMPRESSOR))

    def check_exec_exists(self, exe):
        '''Checks whether a given executable exists in the $PATH.'''

        try:
            with open(os.devnull, 'wb') as devnull:
                ret, _, _ = self.call(exe, stdout=devnull, stderr=devnull)
            return (ret == 0)
        except OSError as e:
            if e.errno == errno.ENOENT:
                return False
            else:
                raise
        finally:
            devnull.close()

    def wrap_fileobj(self, f, filename):
        '''If compress_on_write is enabled, wrap the file object into a GzipFile.
        
        If compress_on_write is disabled, return the original file object.

        param f : file object
            the file object to wrap
        param filename : string
            basename of the file. This goes into the gzip metadata
        '''

        if options.compressor.compress_on_write:
            return gzip.GzipFile(mode='ab', fileobj=f, compresslevel=options.compressor.level, filename=filename)

        return f

    def wrap_filename(self, filename):
        '''If compress_on_write is enabled, return a filename + .gz extension.
        
        If compress_on_write is disabled, return the original filename.
        '''

        if options.compressor.compress_on_write:
            return filename + self.extension 

        return filename

    def unwrap_filename(self, filename):
        '''If compress_on_write is enabled, remove the .gz extension.
        
        If compress_on_write is disabled, return the original filename.
        '''

        if options.compressor.compress_on_write:
            if filename.endswith(self.extension):
                return filename[:-len(self.extension)]

        return filename

