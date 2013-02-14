# LogHog

LogHog is a general purpose log storage/management system. Its main goal is to 
make log management easy, no matter what you use as your applicaiton platform.

LogHog consists of two main components: the logging daemon (loghogd) and your
application which utilizes a LogHog client. The LogHog daemon is responsible for
writing log messages to files, rotating the logs and keeping your logs secure
from anyone who is not authorized to view them.

Python's built-in logging using the FileHandler family does not prevent multiple processes from
writing to the same log file (often over each other). This is a typical issue with Django running
under apache2.

LogHog solves this by having all the processes log to a central server. The LogHog server takes care
of writing the messages one at a time, rotating and compressing files, deleting old log files, etc.

You can think of LogHog as a very secure and user friendly syslog + logrotate in one package.

## When to use LogHog

There are many situations when LogHog will come in handy. Here are some examples:

 * Your application runs on multiple servers and you want the data in one place
 * You have a multi-process application and you want every process to write to a single log file
 * You want to offload your logging to a different server
 * Your application writes logs

In fact there is almost no reason *not to* use LogHog. It is fast, simple,
secure, and it stays out of your way.

## Clients

Currently, there is a fully featured Python client. It is available on GitHub at
https://github.com/activefrequency/loghog-python. You can also install it from PyPI:

    pip install loghog

A PHP client is in the works, and the work-in-progress is available at
https://github.com/activefrequency/loghog-php

## Quickstart

**Step 1**: Install the LogHog server (loghogd). If you are using Ubuntu, run the following:

    sudo add-apt-repository ppa:activefrequency/ppa
    sudo apt-get update
    sudo apt-get install loghogd

If you are using Debian, run the following:

    echo 'deb http://ppa.launchpad.net/activefrequency/ppa/ubuntu lucid main' | sudo tee -a /etc/apt/sources.list.d/99-loghogd.list
    echo 'deb-src http://ppa.launchpad.net/activefrequency/ppa/ubuntu lucid main' | sudo tee -a /etc/apt/sources.list.d/99-loghogd.list
    
    gpg --keyserver hkp://keyserver.ubuntu.com/ --recv-keys F96CE604
    gpg -a --export F96CE604 | sudo apt-key add -
    
    sudo apt-get update
    sudo apt-get install loghogd

**Step 2**: List your application in the LogHog logging facilities. Put the following in */etc/loghogd/facilities.conf*:

    [my-first-app]
    rotate = 0 0 * * *
    backup_count = 14

And reload loghog:

    sudo /etc/init.d/loghogd reload

**Step 3**: Install LogHog Python Client (this codebase):

    pip install loghog

**Step 4**: Enable logging in your application. Add the following to your app startup:

    import logging
    from loghog import LoghogHandler

    logger = logging.getLogger()

    handler = LoghogHandler('my-first-app')

    handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    logger.info('Hello world!')

Start your app and look at /var/log/loghogd/my-first-app/ to see your application's log."

## Configuration

LogHog's configuration is split betweet two files: *loghogd.conf* and *facilities.conf*.
These are typically found in the /etc/loghogd/ directory. *loghogd.conf* specifies
general options for the daemon, such as what ports it will listen on, whether it
will support SSL connections, etc. *facilities.conf* file lists individual applications,
and their submodules as logging facilities. Let's take a look at some things you can
configure:

### loghogd.conf

This file is broken up into sections. Some sections are usually fine as-is, while others
may need some attention to get things working just right. The general rule of thumb for
this file is that safe and sane defaults are used.

The [main] section contains configuration about how the process will run. The most
visible item here is the *logdir* setting which tells LogHog where to put the log files.
Typically, you can leave this section alone.

The [log] section is for configuring the internal logger. You can specify where the logs
will be stored, how many days of logs to keep and what level of logging to use. Normally,
INFO or WARNING are safe.

The [compressor] section determines which compression method to use for the archived logs.
The default is xz, which is a fast and robust compressor with the commands compatible with
both gzip and bzip (xz, unxz, xzcat). Your other choices are gzip and bzip2. Note that
if your system does not come with an installation of xz, LogHog will fall back to gzip.
The *level* option lets you change the compression from 0 (fastest) to 9 (smallest size).

The [server] section is where you will likely end up doing most of the customization.
Here, you can list the addresses and ports on which LogHog will listen for data.
There are two sets of options here: listen\_ipv4/listen\_ipv6/default\_port and 
listen\_ipv4\_ssl/listen\_ipv6\_ssl/default\_port\_ssl. The frist set is used
for defining unencrypted TCP and UDP endpoints, while the second is used to
define the SSL/TLS endpoints (SSL/TLS only works over TCP since it requires
reliable streaming).

By default, LogHog only accepts log messages from localhost. To change that,
simply, update the addresses you want to listen on. The default installation
on Debain-like systems creates a server SSL certificate which will be enabled
by default. See the Security section below for details.

Note that you can specify a custom port for each address you listen on. For
example, you could specify 192.168.1.10:25566 or [::0]:25577. If and address
has a port specified after it, this port is used over then one specified by
default\_port/default\_ssl\_port.

### facilities.conf

This file lists individual applications which will send data to LogHog.
Each application will need at least one facility (called the root facility).
However, if your application has many different components, you might need
to have more than one logging facility. For example, you could log all the
web requests made to your application under root.web.requests (or just web.requests,
which is the same thing). The errors from your application could go to
root.web.errors. The logs from your cron jobs could go under root.cron, etc.

Typically, when specifying a facility, the "root" part is omitted, as it is
implied. So for your application called "my-app", you would have to specify
a section called [my-app], and optionally add [my-app:web.requests], 
[my-app:web.errors], [my-app:cron], etc. Each facility corresponds to one
log file (and its archived instances).

There are two parameters that are required for each facility: *rotate* and *backup_count*.
Normally, LogHog simply uses sane defaults that you can change, but these two
parameters are too important to guess: it would be a terrible thing if
LogHog deleted the logs it thought were too old, or crashed your server by
not rotating them frequently enough.

The *rotate* defines when the log is rotated. This can be done based on a schedule
(e.g.: hourly) or size (e.g.: when it reaches 10 MB). If it is based on size,
you must also specify the *max\_size* (in bytes). See Specifying File Rotation Frequency
section for more details on how to set the schedule.

The backup\_count option simply says how many backups of the given file to keep.

Other options include:

*flush\_every* - A number, specifying how often to flush the file to disk. The higher
this number, the more messages you could lose due to a system failure/power outage. The
lower this number, the more your disks will have to write data, potentially causing
slowdowns for really high volume situations. The safest value is 1, which is the default.

*file\_per\_host* - A boolean (yes or no) which tells LogHog whether to combine all messages
from all the servers sending it data or to write them to separate files. For example,
if you have athens.example.com and sparta.example.com both running my-app, do you
want athens-root.web.requests.log and sparta.web.requests.log or do you just want
root.web.requests.log

*secret* - An optional string. If this is specified the clients must, the clients must
sign their log messages using this secret. Behind the scenes HMAC-MD5 is used for this
purpose.

Note that *max\_size*, *flush\_every*, *file\_per\_host*, and *secret* are inherited from the root facility
for each application. In other words, if you specify [my-app] with a *secret* "foobar",
then [my-app:cron] does not have to specify a value for *secret*.

## Specifying File Rotation Frequency

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

## Security

LogHog provides two different security features: message signing and SSL/TLS support.

### Message signing

If facilities.conf lists a *secret* for a facility (app ID + optional submodule). Then
the clients are required to sign their messages using the same shared secret. This
feature provides a limited protection against message forging. Note that it does not
prevent replay attacks, since a message that was valid once will continue being valid.
The advantage of this feature is that it is compatible with sending messages over UDP,
since no state other than the secret needs to be established between the client and
the server.

### SSL/TLS support

SSL/TLS support means that a secure stream connection is established between the client
and the server. When such a stream is established, both the client and the server
verify each other using a Certificate Authority. This means that the client and the
server certificates must be signed by the same CA. LogHog comes with a set of scripts
to make creating and signing these certificates simple.

Note: you do not need to purchase SSL certificates the way you do for hosting websites.
As self-signed certificate authority is fine for our purposes.

When you install the LogHog server, a CA private key, CA certificate, and server PEM file
will automatically be created. On Debian/Ubuntu you can find them under */etc/loghogd/certs*.
You can regenerate these using the **loghog-server-cert(1)** command.

To generate a client certificate you should use the **loghog-client-cert(1)** command.
This command should be invoked as root or via sudo, since it needs access the the private
CA key (which should be kept as private as possible). Here is a list of files involved:

/etc/loghogd/certs/loghog-ca.key - the private CA key generated by **loghog-server-cert(1)**.
Keep this private.

/etc/loghogd/certs/loghog-ca.cert - the public self-signed CA certificate generated by 
**loghog-server-cert(1)**. This file will be distributed to all the clients.

/etc/loghogd/certs/loghog-server.pem - combination private key and public certificate
used by the server and generated by **loghog-server-cert(1)**. Since this file contains
the server's private key it should be kept private (permissions 0600 are appropriate),
and readable by the user which will run the LogHog server (usually loghog).

\`hostname\`.pem - a client certificate. You can generate one certificate per host, or
one certificate per application. To generate these run the following on the server
where the LogHog server is installed:

    sudo loghog-client-cert `hostname`

This will create a \`hostname\`.pem file which is a combination private key and public
certificate signed by our self-signed certificate authority.

The generated file should be kept private and readable by the user which will run
your application(s).

The server comes pre-configured to use the automatically generated CA and server PEM
files. If you want to change the location of these files, edit /etc/loghogd/loghogd.conf,
and change the settings for *cacert* and  *pemfile*.

See client documentation for how to supply the client with the equivalent options.

Note: the certificates generated by the above mentioned scripts are valid for
1000 years. If you need to use LogHog past that, simply regenerate the certificates.

## Unexpected behavior

Normally, LogHog strives to not have unexpected behavior. The defaults are safe,
though possibly too conservative for some high volume workloads. There are a few places,
where this is not the case. This section documents them.

### Log rotation at low volume

Log rotation is triggered by receiving log messages. In other words, if an application
is not sending you messages, the files will not be rotated. If the application starts
sending messages, the rotation will resume as normal. However, keep in mind that the
value of *backup\_count* is taken literally: this many files will be kept. It does not
matter when they were generated.

### Internal logs

Internal logging is handled by Python's built-in logging module. This means that if
loghogd is not running when the logs are supposed to be rotate, they will not be.
This is a limitiation of the Python Standard Library's implementation, not LogHog's.
Normally, this is not a problem, but can be unexpected.

### Log message limit

Currently, individual log messages cannot exceed 8KB in size.

### Log file creation

Log files are created when the first message is received, not on startup.
This is done to accomodate the *file\_per\_host* setting, where filenames
are not known ahead of time.

## Development

If you want to do some hacking on this code, simply check out the sourcetree,
init and update submodules, create a virtual env, and run $ setup.py develop:

    git clone git://github.com/activefrequency/loghogd.git
    git submodule init
    git submodule update
    mkvirtualenv --system-site-packages loghogd
    python setup.py develop

Note that you may also need to install python-dateutil using either your OS's
package manager, or pip.

We welcome pull requests, so please feel free to send them!

## Testing

LogHog comes with basic unit tests as well as build tests. Build tests are
performed using Vagrant (http://vagrantup.com). To run regular unit tests,
set up the development environment as described above; then run:

    python tests/run.py

If you want to run the build tests, install Vagrant, then run:

    python tests/run.py --all

Note that build tests will take a very long time (up to an hour the first
time), and will download large VirtualBox images into ~/.vagrant.

## License

This code is released under the Apache 2 license. See *LICENSE* for more details.

## Contributing

Feel free to fork this code and submit pull requests. If you are new to GitHub,
feel free to send patches via email to igor@activefrequency.com.

## Credits

Credit goes to Active Frequency, LLC (http://activefrequency.com/) for sponsoring this project.

