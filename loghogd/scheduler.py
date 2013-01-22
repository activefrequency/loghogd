
import os.path
from ext.croniter import croniter
from ext.groper import define_opt, options
try:
    from dbm import ndbm as dbm
except ImportError:
    import dbm

define_opt('scheduler', 'db_filename', default='schedules')

class Scheduler(object):
    '''A job scheduler class. This class keeps the state of the recently executed
    jobs, and is able to use cron-like syntax for determining the next time a job
    should be executed. Usage is as follows:

    s = Scheduler()

    next_time = s.get_next_execution(job_id='x', schedule = '*/5 * * * *', now=time.time())

    while True:
        if next_time < time.time():
            execute_job()
            s.record_execution(job_id='x', time.time())
        else:
            time.sleep(TIMEOUT)

    '''

    def __init__(self, db_filename=None):
        '''Initializes the scheduler and opens the dbm file.'''

        db_filename = db_filename or options.scheduler.db_filename
        db_filename = os.path.join(options.main.workdir, db_filename)
        self.db = dbm.open(db_filename, 'c', 0o600)

    def get_next_execution(self, job_id, schedule, now):
        '''Calculates the next time the job should run.'''

        if job_id not in self.db:
            self.db[job_id] = str(now)

        last_executed = float(self.db[job_id])
        return croniter(schedule, last_executed).get_next()

    def get_last_execution(self, job_id):
        '''Returns a UNIX timestamp of when the job was last executed.'''

        return float(self.db[job_id])

    def record_execution(self, job_id, now):
        '''Records the fact that the job was executed.'''

        self.db[job_id] = str(now)

