#!/usr/bin/env python

import sys, re, os

ASSIGNED_DOMAINS = {
  'mail.ru': 493758,
  'yandex.ru': 493758,
  'rambler.ru': 493758,
}

domains = []
domain2count = {}
countsperIP = {}
regex = re.compile(r"(\d+.\d+\d.\d+).*?live.mozillamessaging.com/autoconfig/(\S*) HTTP/1.\d\" (\d*)")
for line in open(sys.argv[1]).readlines():
  if not line: continue
  found = regex.search(line)
  if not found: continue
  ip, domain, code = found.groups()
  if ip not in countsperIP:
    countsperIP[ip] = 1
  else:
    countsperIP[ip] += 1
  if not domain: continue
  if domain in domain2count:
    domain2count[(domain,code)] += 1
  else:
    domains.append(dict(domain=domain, code=code))
    domain2count[(domain,code)] = 1

ip_histogram = {}
for ip, count in countsperIP.items():
  ip_histogram[count] = ip_histogram.setdefault(count, 0) + 1

counts = ip_histogram.keys()
counts.sort()
for c in counts[:9]:
  print c, ip_histogram[c]
if len(counts) > 9:
  print counts[9], "and more:", sum([ip_histogram[i] for i in counts[9:]])
for domain in domains:
  domain['count'] = domain2count[(domain['domain'],domain['code'])]

misses = []
miss_total = 0
hits = []
hit_total = 0
total_queries = 0;

misses = [d for d in domains if d['code'] == '404' and d['domain'] not in ASSIGNED_DOMAINS]
pending = [d for d in domains if d['code'] == '404' and d['domain'] in ASSIGNED_DOMAINS]
hits = [d for d in domains if d['code'] in ('200','304')]
weirdos = [d for d in domains if d['code'] not in ('200','304','404')]
miss_total = sum([d['count'] for d in misses])
pending_total = sum([d['count'] for d in pending])
weirdo_total = sum([d['count'] for d in weirdos])
hit_total = sum([d['count'] for d in hits])
total_queries = miss_total + hit_total + pending_total + weirdo_total
if total_queries != sum([d['count'] for d in domains]):
  print "Error: total_queries (%d) != sum of domain counts (%d)." % (
    total_queries, sum([d['count'] for d in domains]))


print "HITS: %d domains, accounting for %d successes, or %3.1f%% success rate" % (len(hits), hit_total, 100.*hit_total/total_queries)
print "MISSES: %d domains, accounting for %d failures, or %3.1f%% fail rate" % (len(misses), miss_total, 100.*miss_total/total_queries)
print "PENDING: %d domains, accounting for %d failures, or %3.1f%% fail rate" % (len(pending), pending_total, 100.*pending_total/total_queries)
print "WEIRDOS: %d domains, accounting for %d oddities, or %3.1f%% strangeness rate" % (len(weirdos), weirdo_total, 100.*weirdo_total/total_queries)
print "\n".join("  %(domain)s (%(count)s hits, returned %(code)s)" % x for x in weirdos)

def rank_by_count(a,b):
  return -(a['count'] - b['count'])
misses.sort(rank_by_count)

print "Top 20 misses:"
top_20_percent = 0
for d in misses[:20]:
  percent = 100.0*d['count']/total_queries
  top_20_percent += percent
  print "  %s (%d hits, aka %3.1f%%)" % (d['domain'], d['count'], percent)

print "adding all 20 would boost our HIT rate by %3.1f%%" % top_20_percent

print "Next 50 misses:"
next_50_percent = 0
for d in misses[20:70]:
  percent = 100.0*d['count']/total_queries
  next_50_percent += percent
  print "  %s (%d hits, aka %3.1f%%)" % (d['domain'], d['count'], percent)

print "adding the next 50 would boost our HIT rate by %3.1f%%" % next_50_percent
