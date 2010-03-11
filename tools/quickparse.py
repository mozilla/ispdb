#!/usr/bin/env python

import sys, re, os
domains = []
domain2count = {}
regex = re.compile(r"live.mozillamessaging.com/autoconfig/(\S*) HTTP/1.\d\" (\d*)")
for line in open(sys.argv[1]).readlines():
  if not line: continue
  found = regex.search(line)
  if not found: continue
  domain, code = found.groups()
  if not domain: continue
  if domain in domain2count:
    domain2count[domain] += 1
  else:
    domains.append(dict(domain=domain, code=code))
    domain2count[domain] = 1

for domain in domains:
  domain['count'] = domain2count[domain['domain']]

misses = []
miss_total = 0
hits = []
hit_total = 0
total_queries = 0;

misses = [d for d in domains if d['code'] == '404']
hits = [d for d in domains if d['code'] == '200']
miss_total = sum([d['count'] for d in misses])
hit_total = sum([d['count'] for d in hits])
total_queries = miss_total + hit_total
assert total_queries == sum([d['count'] for d in domains])

print "HITS: %d domains, accounting for %d successes, or %3.1f%% success rate" % (len(hits), hit_total, 100.*hit_total/total_queries)
print "MISSES: %d domains, accounting for %d failures, or %3.1f%% fail rate" % (len(misses), miss_total, 100.*miss_total/total_queries)

def rank_by_count(a,b):
  return -(a['count'] - b['count'])
misses.sort(rank_by_count)

print "Top 20 misses:"
top_20_percent = 0
for d in misses[:20]:
  percent = 100.0*d['count']/len(domains)
  top_20_percent += percent
  print "  %s (%d hits, aka %3.1f%%)" % (d['domain'], d['count'], percent)

print "adding all 20 would boost our HIT rate by %3.1f%%" % top_20_percent
