
# LogHog

Loghog is a general purpose log storage/management system. Its main goal is to 
make log management easy, no matter what you use as your applicaiton platform.

LogHog consists of two main components: the logging daemon (loghogd) and your
application which utilizes a LogHog client. The LogHog daemon is responsible for
writing log messages to files, rotating the logs and keeping your logs secure
from anyone who is not authorized to view them.

## Examples

First, install loghog (TODO: elaborate once we have places to download).

Start it:

    $ loghogd -c examples/conf/loghogd.conf

In a different terminal start an example client app:

    $ python examples/python-simple.py

Watch the output on the first console, and the contents of
/tmp/logs/my-first-app/root.log

Notice that the files will be rotated every so often.

## Specifying Frequency

There are several ways to specify when the logs should be rotated. Here are
some simple example:

    rotate = hourly ; At the top of the hour
    rotate = daily ; At migdnight (default value)
    rotate = midnight ; Same as daily
    rotate = weekly ; At midnight between Sunday and Monday
    rotate = monthly ; At midnight between last day and first day of two months
    rotate = yearly ; At midnight between last day and first day of two years
    rotate = annually ; Same as yearly

Nearly full cron syntax is also supported:

    rotate = 55 22 * * * ; At 10:55 pm every day
    rotate = */15 * * * ; Every 15 minutes
    rotate = 33 12 * * 1-5 ; At 12:33 pm, Monday-Friday

NOTE: cron supports a "reboot" time, but that doesn't make sense in the
context of this application, so it is not supported.

