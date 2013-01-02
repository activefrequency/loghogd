

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

