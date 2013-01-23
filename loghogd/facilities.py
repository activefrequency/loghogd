from ext.croniter import croniter
from ConfigParser import RawConfigParser
import os.path

def parse_mod_id(mod_str):
    mod_list = mod_str.strip().split('.')

    result = []
    if mod_list[0] != 'root':
        result = ['root']

    result.extend(s for s in mod_list if s)

    return tuple(result)

def pretty_mod_id(mod_id):
    if len(mod_id) > 1:
        return '.'.join(mod_id[1:])
    else:
        return '.'.join(mod_id)

class FacilityError(Exception):
    pass

class Facility(object):

    ROTATE_MODE_TRANSLATIONS = {
        'hourly': '0 * * * *',
        'daily': '0 0 * * *',
        'midnight': '0 0 * * *',
        'weekly': '0 0 * * 1',
        'monthly': '0 0 1 * *',
        'yearly': '0 0 1 1 *',
        'annually': '0 0 1 1 *',
    }


    def __init__(self, app_id, mod_id, rotate, backup_count, max_size=None, secret=None, flush_every=1, file_per_host=False):
        '''Initializes a facility instance and validtes the input.'''

        self.app_id = app_id
        self.mod_id = mod_id
        self.mod_str = pretty_mod_id(mod_id)

        if not app_id:
            raise FacilityError('app_id is required in the facility configuration file')

        if rotate in self.ROTATE_MODE_TRANSLATIONS:
            rotate = self.ROTATE_MODE_TRANSLATIONS[rotate]

        if rotate == 'size':
            if not max_size:
                raise FacilityError('Error parsing facility for {0}:{1}: rotation mode is "size", but no max_size is specified'.format(app_id, self.mod_str))
        else:
            try:
                croniter(rotate)
            except:
                raise FacilityError('Error parsing facility for {0}:{1}: "{2}" is not a valid rotation mode'.format(app_id, self.mod_str, rotate))

        if not isinstance(backup_count, int) or backup_count <= 0: 
            raise FacilityError('Error parsing facility for {0}:{1}: backup_count must be a positive integer'.format(app_id, self.mod_str))

        if max_size and (not isinstance(max_size, int) or max_size <= 0): 
            raise FacilityError('Error parsing facility for {0}:{1}: if specified, max_size must be a positive integer'.format(app_id, self.mod_str))

        if flush_every and (not isinstance(flush_every, int) or flush_every <= 0): 
            raise FacilityError('Error parsing facility for {0}:{1}: if specified, flush_every must be a positive integer'.format(app_id, self.mod_str))

        self.rotate = rotate
        self.backup_count = int(backup_count)
        self.secret = secret
        self.max_size = max_size
        self.flush_every = flush_every
        self.file_per_host = file_per_host

    def __repr__(self):
        return u'<{0}: {1}:{2}>'.format(self.__class__.__name__, self.app_id, '.'.join(self.mod_id))

class FacilityDB(object):

    def __init__(self):
        '''Initializes an empty FacilityDB.'''

        self.facilities = {}

    def add_facility(self, facility):
        '''Registers a facility with the database.'''

        if facility.app_id not in self.facilities:
            self.facilities[facility.app_id] = {}

        self.facilities[facility.app_id][facility.mod_id] = facility

    def get_applications(self):
        '''Enumerates all application IDs.'''

        return self.facilities.keys()

    def get_facilities(self):
        '''Enumerates all facilities.'''

        result = []
        for app in self.facilities:
            for mod_id, facility in self.facilities[app].iteritems():
                result.append((app, mod_id, facility))

        return result

    def get_facility(self, app, mod_str):
        '''Searches facilities and returns the most specific match.

        For example, if mod_str is 'foo.bar', and we have the following facilities defined:
         - root.foo
         - root.baz
         - root

        then root.foo will be returned. If we have the same facilities defined and
        mod_str is 'bam.tee', then root will be returned.

        returns a Facility instance.
        '''

        if isinstance(mod_str, basestring):
            mod_id = parse_mod_id(mod_str)
        else:
            mod_id = mod_str

        app_facilities = self.facilities.get(app, None)

        if not app_facilities:
            return None

        while mod_id:
            if mod_id in app_facilities.keys():
                return app_facilities[mod_id]
            mod_id = mod_id[:-1]
 
        assert False, "This should never happen"

    def load_config(self, filename):
        '''Loads facility definitions from a config file.'''

        db = self.__class__()

        cp = RawConfigParser()

        # NOTE: apparently, cp.read() will happily do nothing if the file doesn't exist.
        # Thus, we use cp.readfp() instead, letting open() fail if something is wrong.
        f = open(filename, 'r')
        cp.readfp(f, filename)
        f.close()

        root_facilities = {}
        # First we add all root facilities
        for section in cp.sections():
            app_id, _, mod_str = section.partition(':')
            if mod_str:
                # Skip non-root facilities
                continue

            facility = self.parse_section(cp, section)
            db.add_facility(facility)
            root_facilities[app_id] = facility
        
        for section in cp.sections():
            app_id, _, mod_str = section.partition(':')
            if not mod_str:
                # Skip root facilities
                continue

            try:
                root_facility = root_facilities[app_id]
            except KeyError:
                raise FacilityError('Application {0} lacks a root module. Define [{0}] section in the facility config file.'.format(app_id, app_id))

            facility = self.parse_section(cp, section, root_facility=root_facility)
            db.add_facility(facility)

        self.facilities = db.facilities
        self.filename = filename

    def parse_section(self, cp, section, root_facility=None):
        '''Parses a ConfigParser section and returns a Facility instance.'''

        app_id, _, mod_str = section.partition(':')

        # These options are defined directly
        settings = {}
        settings['app_id'] = app_id
        settings['mod_id'] = parse_mod_id(mod_str)
        settings['rotate'] = cp.get(section, 'rotate')
        settings['backup_count'] = cp.getint(section, 'backup_count')
        
        # Figure out values of inherited params
        def_secret = None
        def_max_size = None
        def_file_per_host = False
        def_flush_every = 1

        if root_facility:
            def_secret = root_facility.secret
            def_max_size = root_facility.max_size
            def_file_per_host = root_facility.file_per_host
            def_flush_every = root_facility.flush_every

        # These options can be inherited
        settings['secret'] = cp.get(section, 'secret') if cp.has_option(section, 'secret') else def_secret
        settings['max_size'] = cp.getint(section, 'max_size') if cp.has_option(section, 'max_size') else def_max_size
        settings['file_per_host'] = cp.getboolean(section, 'file_per_host') if cp.has_option(section, 'file_per_host') else def_file_per_host
        settings['flush_every'] = cp.getint(section, 'flush_every') if cp.has_option(section, 'flush_every') else def_flush_every

        return Facility(**settings)

    def reload(self):
        '''Reloads facilities using config information supplied previously.'''

        self.load_config(self.filename)

