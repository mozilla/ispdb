#!/usr/bin/env python

from optparse import OptionParser
import os
import pickle
import re
import sys


# Constants.

ASSIGNED_DOMAINS = {
  "mail.ru": 493758,
  "yandex.ru": 493758,
  "rambler.ru": 493758,
}


# Utility functions.

def readPrevious(pickleName):
  """Read the previous data from the specified pickle."""
  prevHits = None
  prevMisses = None
  if os.path.exists(pickleName):
    data = open(pickleName)
    prevHits = pickle.load(data)
    prevMisses = pickle.load(data)
  return prevHits, prevMisses

def writeNext(pickleName, hits, misses):
  """Write the current data to the specified pickle."""
  out = open(pickleName, "w")
  pickle.dump(hits, out, -1)
  pickle.dump(misses, out, -1)
  out.close()

def gatherData(files):
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
      if (domain,code) in domain2count:
        domain2count[(domain,code)] += 1
      else:
        domains.append(dict(domain=domain, code=code))
        domain2count[(domain,code)] = 1
    for domain in domains:
      domain["count"] = domain2count[(domain["domain"],domain["code"])]
  ip_histogram = {}

  for ip, count in countsperIP.items():
    ip_histogram[count] = ip_histogram.setdefault(count, 0) + 1

  counts = ip_histogram.keys()
  counts.sort()
  return domains, counts, ip_histogram

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


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


# Main method.

def main(argv=None):
  if argv is None:
    argv = sys.argv

  parser = OptionParser()
  parser.add_option("-p", "--previous", dest="previous",
                    default="./quickparse.pickle",
                    help="Where to get the previous data.  "
                         "%default by default.")
  parser.add_option("-n", "--next", dest="next",
                    default=None,
                    help="Where to write the new data.  "
                         "<filename>.pickle by default.")
  (options, args) = parser.parse_args()
  if not options.next:
    options.next = os.path.splitext(args[0])[0]+".pickle"

  prevHits, prevMisses = readPrevious(options.previous)

  domains, counts, ip_histogram = gatherData(args)

  for c in counts[:9]:
    print c, ip_histogram[c]
  if len(counts) > 9:
    print counts[9], "and more:", sum([ip_histogram[i] for i in counts[9:]])

  hits = dictify(d for d in domains if d["code"] in ("200","304"))
  misses = dictify(d for d in domains if d["code"] == "404"
                                      and d["domain"] not in ASSIGNED_DOMAINS)
  pending = dictify(d for d in domains if d["code"] == "404"
                                       and d["domain"] in ASSIGNED_DOMAINS)
  weirdos = sorted(d for d in domains if d["code"] not in ("200","304","404"))

  miss_total = sum(misses.values())
  pending_total = sum(pending.values())
  weirdo_total = sum(x["count"] for x in weirdos)
  hit_total = sum(hits.values())
  total_queries = miss_total + hit_total + pending_total + weirdo_total
  if total_queries != sum([d["count"] for d in domains]):
    print "Error: total_queries (%d) != sum of domain counts (%d)." % (
      total_queries, sum([d["count"] for d in domains]))


  print "HITS: %d domains, accounting for %d successes, or %3.1f%% success rate" % (len(hits), hit_total, 100.*hit_total/total_queries)
  print "MISSES: %d domains, accounting for %d failures, or %3.1f%% fail rate" % (len(misses), miss_total, 100.*miss_total/total_queries)
  print "PENDING: %d domains, accounting for %d failures, or %3.1f%% fail rate" % (len(pending), pending_total, 100.*pending_total/total_queries)
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

  writeNext(options.next, hits, misses)
  return 0

if __name__ == "__main__":
    sys.exit(main())

