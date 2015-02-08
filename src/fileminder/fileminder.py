#!/usr/bin/env python
# encoding: utf-8
'''

FileMinder tails a text file searching for a match on a regular expression.
If the regular expression matches, the matching line together with a specified
number of lines of preceding context will be output by email to a SMTP server,
or displayed on the screen.

@author:     Michael Eng

@copyright:  Copyright 2015 Michael Eng. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

'''

import sys
import os

import email.mime.text,email.mime.multipart,smtplib,re,socket,cgi,time

from optparse import OptionParser

__all__ = []
__version__ = 0.1
__date__ = '2015-01-02'
__updated__ = '2015-01-02'

DEBUG = 0
TESTRUN = 0
PROFILE = 0


def sendmail(opts, msg):
    s = smtplib.SMTP(opts.smtp, opts.smtp_port)
    s.ehlo()
    s.starttls()
    s.sendmail(opts.mail_from, [opts.mail_to], msg.as_string())
    s.quit()


def report_match_screen(opts, context, extratext=None, subj_prefix=None):
    if not subj_prefix: subj_prefix=opts.mail_subject
    print "\n\n\n----- %s: %s [%s:%s]" % (time.asctime(), subj_prefix, opts.hostname, opts.infile)
    if extratext: print extratext
    print "\n".join(context)


def format_mail(opts, context):
    msg_text = email.mime.text.MIMEText("\n".join(context), 'plain')
    msg_html = email.mime.text.MIMEText("<html><head/><body><tt>%s</tt></body></html>" % "<br>\n".join(map(cgi.escape, context)), 'html')

    msg = email.mime.multipart.MIMEMultipart('alternative')
    msg['Subject'] = "%s [%s:%s] %s" % (opts.mail_subject, opts.hostname, opts.infile, context[len(context) - 1])
    msg['From'] = opts.mail_from
    msg['To'] = opts.mail_to
    msg.attach(msg_text)
    msg.attach(msg_html)
    return msg

def report_match(opts,context,match_span):
    
    
    if opts.smtp:
        
        msg = format_mail(opts, context)
        try:
            sendmail(opts, msg)
        except Exception, e:
            report_match_screen(opts, context, repr(e))
    else:
        report_match_screen(opts, context)


def report_fail(opts,message):
    if opts.smtp:
        

        msg = email.mime.text.MIMEText(message, 'plain')
        msg['Subject'] = "Failed [%s:%s] %s" % (opts.hostname, opts.infile, message)
        msg['From'] = opts.mail_from
        msg['To'] = opts.mail_to

        try:
            sendmail(opts, msg)
        except Exception, e:
            report_match_screen(opts, [message], repr(e), "Failed")
    else:
        report_match_screen(opts, [message], subj_prefix="Failed")    

def watchfile(opts):

    fn=opts.infile
    fp = open(fn,'r')

    st_size = os.stat(fn)[6]
    fp.seek(st_size)

    matcher=re.compile(opts.regexp,re.IGNORECASE)
    contextbuf=[]
    if opts.preceding!=None and int(opts.preceding)>0:
        preceding=int(opts.preceding)
    else:
        preceding=0
        
    while True:
        where = fp.tell()
        line = fp.readline()
        if not line:
            time.sleep(1)
            fp.seek(where)
            try:
                stat=os.stat(fn)
                if stat[6] < where:
                    report_fail(opts,"File restarted, my position=%i, stat=%s" % (where, os.stat(fn)))
                    sys.exit(1)
            except OSError, e:
                report_fail(opts,"File disappeared: %s"%repr(e))
                sys.exit(1)

        else:
            line=line.strip()
            contextbuf.append(line)
            match=matcher.search(line)
            if match:
                report_match(opts,contextbuf,match.span())
        
            while (len(contextbuf)>preceding):
                del contextbuf[0]


def main(argv=None):
    '''Command line options.'''

    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.1"
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    program_description = """FileMinder tails a text file searching for a match on a regular expression.
If the regular expression matches, the matching line together with a specified
number of lines of preceding context will be output by email to a SMTP server,
or displayed on the screen if the SMTP server is not specified."""

    if argv is None:
        argv = sys.argv[1:]
    try:
        # setup option parser
        parser = OptionParser(version=program_version_string, description=program_description)
        parser.add_option("-i", "--in", dest="infile", help="set input file [default: %default]", metavar="FILE")
        parser.add_option("-r", "--regexp", dest="regexp", help="set expression to match [default: %default]", metavar="EXPRESSION")
        parser.add_option("-m", "--mailserver", dest="smtp", help="mail server hostname [default: %default]", metavar="HOST")
        parser.add_option("-p", "--mailserverport", dest="smtp_port", help="mail server port [default: %default]", metavar="PORT")
        
        parser.add_option("-f", "--from", dest="mail_from", help="mail from address [default: %default]", metavar="ADDRESS")
        parser.add_option("-t", "--to", dest="mail_to", help="mail to address [default: %default]", metavar="ADDRESS")
        parser.add_option("-s", "--subject", dest="mail_subject", help="subject line prefix [default: %default]", metavar="TEXT")
        parser.add_option("-c", "--context", dest="preceding", help="output lines of preceding context [default: %default]", metavar="NUM")

        parser.add_option("-H", "--hostname", dest="hostname", help="reported hostname [default: %default]", metavar="HOST")
        parser.add_option("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %default]")

        # set defaults
        parser.set_defaults(infile="%s.txt"%time.strftime("%Y%m%d"),
                            hostname=socket.gethostname(),
                            mail_subject="Matched",
                            preceding=10,
                            smtp_port=25)

        # process options
        (opts, args) = parser.parse_args(argv)

        # MAIN BODY #
        
        watchfile(opts)

    except Exception, e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help\n")
        return 2


if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'fileminder.fileminder_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())