
'''
Registered:
pingbrigade:root
pingbrigade:root.web
pingbrigade:root.cron
pingbrigade:root.django
pingbrigade:root.django.requests
pingbrigade:root.celery.tasks

Examples:
pingbrigade:root.django.requests.foo
pingbrigade:root.django.foo
pingbrigade:root.django2
pingbrigade:
pingbrigade:root
pingbrigade:root.bar
pingbrigade:root.celery.beat

'''

from ext.croniter import croniter
from ConfigParser import RawConfigParser
import os.path

def _parse_mod_id(mod_str):
    mod_list = mod_str.strip().split('.')

    result = []
    if mod_list[0] != 'root':
        result = ['root']

    result.extend(s for s in mod_list if s)

    return tuple(result)

def _pretty_mod_id(mod_id):
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
        self.mod_str = _pretty_mod_id(mod_id)

        if not app_id:
            raise FacilityError('app_id is required in the facility configuration file')

        if rotate in self.ROTATE_MODE_TRANSLATIONS:
            rotate = self.ROTATE_MODE_TRANSLATIONS[rotate]

        if rotate == 'size':
            if not max_size:
                raise FacilityError('Error parsing facility for {}:{}: rotation mode is "size", but no max_size is specified'.format(app_id, self.mod_str))
        else:
            try:
                croniter(rotate)
            except:
                raise FacilityError('Error parsing facility for {}:{}: "{}" is not a valid rotation mode'.format(app_id, self.mod_str, rotate))

        if not isinstance(backup_count, int) or backup_count <= 0: 
            raise FacilityError('Error parsing facility for {}:{}: backup_count must be a positive integer'.format(app_id, self.mod_str))

        if max_size and (not isinstance(max_size, int) or max_size <= 0): 
            raise FacilityError('Error parsing facility for {}:{}: if specified, max_size must be a positive integer'.format(app_id, self.mod_str))

        if flush_every and (not isinstance(flush_every, int) or flush_every <= 0): 
            raise FacilityError('Error parsing facility for {}:{}: if specified, flush_every must be a positive integer'.format(app_id, self.mod_str))

        self.rotate = rotate
        self.backup_count = int(backup_count)
        self.secret = secret
        self.max_size = max_size
        self.flush_every = flush_every
        self.file_per_host = file_per_host

    def __repr__(self):
        return u'<{}: {}:{}>'.format(self.__class__.__name__, self.app_id, '.'.join(self.mod_id))

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
            mod_id = _parse_mod_id(mod_str)
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
        cp.read(filename)

        for section in cp.sections():
            app_id, _, mod_str = section.partition(':')

            settings = {}
            settings['app_id'] = app_id
            settings['mod_id'] = _parse_mod_id(mod_str)
            settings['rotate'] = cp.get(section, 'rotate')
            settings['backup_count'] = cp.getint(section, 'backup_count')
            settings['secret'] = cp.get(section, 'secret') if cp.has_option(section, 'secret') else None
            settings['max_size'] = cp.getint(section, 'max_size') if cp.has_option(section, 'max_size') else None
            settings['file_per_host'] = cp.getboolean(section, 'file_per_host') if cp.has_option(section, 'file_per_host') else False

            if cp.has_option(section, 'flush_every'):
                settings['flush_every'] = cp.getint(section, 'flush_every')

            db.add_facility(Facility(**settings))

        db.validate()

        self.facilities = db.facilities
        self.filename = filename

    def reload(self):
        '''Reloads facilities using config information supplied previously.'''

        self.load_config(self.filename)

    def validate(self):
        '''Validates facilities, ensuring that all root modules exist.'''

        root_id = ('root',) 
        for app_id in self.get_applications():
            if root_id not in self.facilities[app_id]:
                raise FacilityError('Application {} lacks a root module. Define [{}] section in the facility config file.'.format(app_id, app_id))

