#! /usr/bin/env python

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Thunderbird autoconfig conversion tool.
#
# The Initial Developer of the Original Code is
# Mogens Isager <m@isager.net>.
#
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Blake Winton <bwinton@latte.ca>
#
# ***** END LICENSE BLOCK *****

import argparse
import codecs
import os.path
import sys
import xml.dom.minidom


def read_config(file, convertTime):
    return (xml.dom.minidom.parse(file),
            max(os.stat(file).st_mtime, convertTime))


def print_config(doc):
    print doc.toxml(encoding="UTF-8")


def write_config(outData, time, filename=None):
    if os.path.exists(filename) and os.stat(filename).st_mtime >= time:
        return

    print "Producing %s" % filename
    file = codecs.open(filename, "w")
    file.write(outData)
    file.close()


def write_domains(doc, time, output_dir="."):
    outData = doc.toxml(encoding="UTF-8")
    for d in doc.getElementsByTagName("domain"):
        write_config(outData, time, output_dir + "/" + d.childNodes[0].data)


def convert_11_to_10(doc):
    if doc.getElementsByTagName("clientConfig")[0].getAttribute("version"):
        doc.getElementsByTagName("clientConfig")[0].removeAttribute("version")

    # Change <authentication>password-cleartext</> to plain and
    # <authentication>password-encrypted</> to secure (from bug 525238).
    for a in doc.getElementsByTagName("authentication"):
        if a.childNodes[0].wholeText.find("password-cleartext") != -1:
            a.replaceChild(doc.createTextNode("plain"),
                           a.childNodes[0])
        if a.childNodes[0].wholeText.find("password-encrypted") != -1:
            a.replaceChild(doc.createTextNode("secure"),
                           a.childNodes[0])

    # Add <addThisServer>true</> and <useGlobalPreferredServer>false</>.
    a = doc.getElementsByTagName("outgoingServer")
    if a:
        a[0].appendChild(doc.createTextNode("  "))
        addThisServer = doc.createElement("addThisServer")
        addThisServer.appendChild(doc.createTextNode("true"))
        a[0].appendChild(addThisServer)
        a[0].appendChild(doc.createTextNode("\n      "))
        useServer = doc.createElement("useGlobalPreferredServer")
        useServer.appendChild(doc.createTextNode("false"))
        a[0].appendChild(useServer)
        a[0].appendChild(doc.createTextNode("\n    "))

    # Comment out all but the first of the incoming and outgoing servers.
    def commentRest(tagname):
        first = True
        for a in doc.getElementsByTagName(tagname):
            if first:
                first = False
            else:
                a.parentNode.replaceChild(doc.createComment(
                    "\n    " + a.toxml().replace("--", "- -") + "\n    "), a)
    commentRest("incomingServer")
    commentRest("outgoingServer")


def main():
    # parse command line options
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", choices=["1.0"],
                        help="convert input files to version 1.0")
    parser.add_argument("-d", metavar="dir",
                        help="output directory")
    parser.add_argument("-a", action="store_true",
                        help="write configuration files for all domains")
    parser.add_argument("file", nargs="*",
                        help="input file(s) to process, wildcards allowed")
    args = parser.parse_args(sys.argv[1:])

    # process arguments
    convertTime = os.stat(sys.argv[0]).st_mtime
    for f in args.file:
        doc, time = read_config(f, convertTime)

        if args.v == "1.0":
            convert_11_to_10(doc)

        if args.a:
            if args.d:
                write_domains(doc, time, args.d)
            else:
                print "When you want to write domain files you",
                print "should also specify an output directory",
                print "using -d dir"
                parser.print_usage()
                exit(2)
        elif args.d:
            write_config(doc, time, args.d + "/" + os.path.basename(f))
        else:
            print_config(doc)

        doc.unlink()


if __name__ == "__main__":
    main()
