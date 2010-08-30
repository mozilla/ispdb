#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import date, timedelta
import DNS
import etld # <http://www.stillhq.com/python/etld/etld.py>
from optparse import OptionParser
import os
import pickle
import re
import sys


# Constants.

# Utility functions.

def readPrevious(pickleName):
  """Read the previous data from the specified pickle."""
  prevHits = None
  prevMisses = None
  mxs = {}
  if os.path.exists(pickleName):
    data = open(pickleName)
    prevHits = pickle.load(data)
    prevMisses = pickle.load(data)
    try:
      mxs = pickle.load(data)
    except EOFError:
      pass
  return prevHits, prevMisses, mxs

def writeNext(pickleName, hits, misses, mxs):
  """Write the current data to the specified pickle."""
  out = open(pickleName, "w")
  pickle.dump(hits, out, -1)
  pickle.dump(misses, out, -1)
  pickle.dump(mxs, out, -1)
  out.close()

def gatherData(files, mxs):
  """Gather all the data."""
  domains = []
  domain2count = {}
  countsperIP = {}
  regex = re.compile(r"(\d+.\d+\d.\d+).*?live.mozillamessaging.com/autoconfig/(\S*) HTTP/1.\d\" (\d*)")
  for infile in files:
    for line in open(infile).readlines():
      if not line: continue
      found = regex.search(line)
      if not found: continue
      ip, domain, code = found.groups()
      if ip not in countsperIP:
        countsperIP[ip] = 1
      else:
        countsperIP[ip] += 1
      if not domain: continue
      domain = domain.split("?")[0]
      if (domain,code) in domain2count:
        domain2count[(domain,code)] += 1
      else:
        domains.append(dict(domain=domain, code=code))
        domain2count[(domain,code)] = 1
    for domain in domains:
      domain["count"] = domain2count[(domain["domain"],domain["code"])]

  # So, now we've got all the lines, but some of the failures will actually
  # be hits on the MX, so let's try to remove those.
  domainsDict = dictify(domains)
  mx_hits = [];
  for domain in domains:
    if domain["code"] == "404":
      # We've got a missing domain, so let's check for the MX record.
      values = domain["domain"].split("/")
      prefix = ""
      name = values[-1]
      if len(values) > 1:
        prefix = values[-2]
      mx = getMX(mxs, name)
      if mx and (mx in domainsDict or (prefix + "/" + mx) in domainsDict):
        mx_hits.append(domain["count"])
        domains.remove(domain)

  ip_histogram = {}
  for ip, count in countsperIP.items():
    ip_histogram[count] = ip_histogram.setdefault(count, 0) + 1

  counts = ip_histogram.keys()
  counts.sort()
  return domains, counts, mx_hits, ip_histogram

def dictify(data):
  """Change a list of domains, counts, and codes into a dict of the same."""
  retval = {}
  for d in data:
    domain = d["domain"]
    count = d["count"]
    retval[domain] = retval.get(domain, 0) + count
  return retval

def printDetails(data, total_queries, hitPrefix=""):
  """Print the details lines for each domain in data."""
  retval = 0
  for domain,count in data:
    percent = 100.0*count/total_queries
    retval += percent
    print "  %s (%s%d hits, aka %3.1f%%)" % (domain, hitPrefix, count, percent)
  return retval

def rank_by_count(a,b):
  return -(a[1] - b[1])

def calculateDiffs(prevData, data):
  """For each domain in data, calculate the delta between it and the
     domain in prevData."""
  retval = []
  for domain,count in data.iteritems():
    prevValue = prevData.get(domain, 0)
    count -= prevValue
    retval.append((domain,count))
  retval.sort(rank_by_count)
  return retval

etldService = etld.etld()

def getSLD(domain):
  """Get the "second level domain", e.g. "mozilla.org" or "bbc.co.uk" """
  try:
    sp = etldService.parse(domain) # returns ("5.4.bbc", "co.uk")
    sld = sp[0].rsplit(".", 1)[-1]
    tld = sp[1]
    return sld + "." + tld
  except etld.EtldException:
    return domain


mx_queries = 0
mx_cache_hit = 0

def getMX(mxs, name):
  """ You pass in domain |name| and it returns the hostname of the MX server.
  It either uses the cache |mxs| or does a lookup via DNS over the Internet
  (and populates the cache)."""
  global mx_queries
  global mx_cache_hit
  if name not in mxs:
    possible_mxs = []
    try:
      possible_mxs = DNS.mxlookup(name.encode("utf-8"))
      mx_queries += 1
    except DNS.DNSError:
      pass
    except UnicodeError:
      pass
    if len(possible_mxs) < 1:
      possible_mxs = [(0, "")]
    mxs[name] = getSLD(possible_mxs[0][1])
  else:
    mx_cache_hit += 1 

  return mxs[name]

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


# Main method.

def main(argv=None):
  if argv is None:
    argv = sys.argv

  usage = """%prog [options] logfile [...]
  logfile               Apache logfile"""
  parser = OptionParser(usage=usage)
  parser.add_option("-p", "--previous", dest="previous",
                    default=None, #set below
                    help="Where to get the cache data of the previous run"
                         "of this script esp. DNS MX lookups, which can"
                         "take hours.  <filename-1>.pickle by default.")
  parser.add_option("-n", "--next", dest="next",
                    default=None, # set below
                    help="Where to write the new cache data of this run of"
                         "this script.  <filename>.pickle by default.")
  (options, logfiles) = parser.parse_args()

  if len(logfiles) < 1:
    parser.print_usage()
    exit(1)

  if not options.next:
    options.next = os.path.splitext(logfiles[0])[0]+".pickle"
  if not options.previous:
    try:
      name = os.path.splitext(logfiles[0])[0]
      d = date(int(name[0:4]), int(name[4:6]), int(name[6:8]))
      d -= timedelta(days=1)
      name = d.strftime("%Y%m%d")
      options.previous = name+".pickle"
    except:
      options.previous = options.next

  prevHits, prevMisses, mxs = readPrevious(options.previous)

  domains, counts, mx_hits, ip_histogram = gatherData(logfiles, mxs)

  print "# of requests per single IP:"
  for c in counts[:9]:
    print "%4d %d" %(c, ip_histogram[c])
  if len(counts) > 9:
    print "%3d+" %(counts[9],), sum([ip_histogram[i] for i in counts[9:]])

  print ""

  hits = dictify(d for d in domains if d["code"] in ("200","304"))
  misses = dictify(d for d in domains if d["code"] == "404")
  weirdos = sorted(d for d in domains if d["code"] not in ("200","304","404"))

  miss_total = sum(misses.values())
  weirdo_total = sum(x["count"] for x in weirdos)
  hit_total = sum(hits.values())
  mx_total = sum(mx_hits)
  total_queries = miss_total + hit_total + weirdo_total
  if total_queries != sum([d["count"] for d in domains]):
    print "Error: total_queries (%d) != sum of domain counts (%d)." % (
      total_queries, sum([d["count"] for d in domains]))


  print "HITS: %d domains, accounting for %d successes, or %3.1f%% success rate" % (len(hits), hit_total, 100.*hit_total/total_queries)
  print "  MX: %d domains, accounting for %d hits." % (len(mx_hits), mx_total)
  print "MISSES: %d domains, accounting for %d failures, or %3.1f%% fail rate" % (len(misses), miss_total, 100.*miss_total/total_queries)
  print "WEIRDOS: %d domains, accounting for %d oddities, or %3.1f%% strangeness rate" % (len(weirdos), weirdo_total, 100.*weirdo_total/total_queries)
  print "\n".join("  %(domain)s (%(count)s hits, returned %(code)s)" % x for x in weirdos)
  print


  # Print the details.

  hitlist = sorted(hits.iteritems(), rank_by_count)
  misslist = sorted(misses.iteritems(), rank_by_count)

  print "Top 10 hits:"
  printDetails(hitlist[:10], total_queries)
  print

  print "Top 20 misses:"
  top_20_percent = printDetails(misslist[:20], total_queries)
  print "adding all 20 would boost our HIT rate by %3.1f%%" % top_20_percent

  print "Next 50 misses:"
  next_50_percent = printDetails(misslist[20:70], total_queries)
  print "adding the next 50 would boost our HIT rate by %3.1f%%" % next_50_percent
  print


  # Calculate the fastest rising misses, and the fastest falling hits.

  if prevHits:
    print "Fastest falling hits:"
    prevHits = calculateDiffs(prevHits, hits)
    prevHits.reverse()
    printDetails(prevHits[:10], total_queries)
    print

  if prevMisses:
    print "Fastest rising misses:"
    prevMisses = calculateDiffs(prevMisses, misses)
    printDetails(prevMisses[:10], total_queries, "+")
    print

  print "# DNS Statistics lookups/cached (hit ratio)"
  dns_ratio = 100.0 * mx_cache_hit / (mx_queries + mx_cache_hit)
  print "%d/%d (%3.1f%%)" % (mx_queries, mx_cache_hit, dns_ratio)
 
  writeNext(options.next, hits, misses, mxs)
  return 0

if __name__ == "__main__":
    sys.exit(main())

