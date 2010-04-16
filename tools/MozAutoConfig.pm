package MozAutoConfig;

use strict;
use warnings;
use Apache2::RequestRec ();
use Apache2::RequestUtil ();
use Apache2::RequestIO ();
use APR::Table ();
use Apache2::Const -compile => qw(OK HTTP_NOT_FOUND);
use Net::DNS;
use IO::Select;
use Time::HiRes qw(time);
use File::Path qw(mkpath);
use File::Temp qw(mkstemps);
use LWP::UserAgent;
use HTTP::Request;

use constant DEBUG => 0;

# Domain matching RE (use our own, since _ is technically invalid, but seems to be used)
my $domain_re = qr/[a-z0-9_\-]+(\.[a-z0-9_\-]+)+/i;

# Some known primary MX exchange server -> domain mappings
my %known_domains_mx = (
  'ASPMX.L.GOOGLE.COM' => 'gmail.com',
  'IN1.SMTP.MESSAGINGENGINE.COM' => 'fastmail.fm',
);

sub handler {
  my $r = shift;

  # Don't need request body (we only handle GET requests)
  $r->discard_request_body();

  # Get config known dirs and cache dirs
  my $known_domains_path = $r->dir_config('known_domains_path')
    || die 'Must set config option "known_domains_path"';
  my $cache_domains_path = $r->dir_config('cache_domains_path')
    || warn 'No config option "cache_domains_path" specified, so no domains being cached. Are you sure you want that?';

  # Should we're only a single level directory, and the last part
  #  is always the domain
  my $uri = $r->uri;

  if ($r->prev) {
    my $prev = $r->prev;
    $uri = $prev->uri;
  }

  warn "handler called. uri=$uri" if DEBUG;

  my ($domain) = $uri =~ m#/([a-z0-9_\-\.]*)$#;
  warn "extract domain. domain=$domain" if DEBUG;

  # Create simple object for state storage
  my $self = bless {
    r => $r,
    errors => [],
    depth => 0,
    seen_domains => {},
    domain => $domain,
    known_domains_path => $known_domains_path,
    cache_domains_path => $cache_domains_path,
  }, 'MozAutoConfig';

  # If we're given a domain, lookup the data for it
  if ($domain) {

    # Run full lookup and return data for domain if found
    if ($self->return_domain_data($domain)) {
      return Apache2::Const::OK;
    }

  } else {
    $self->add_error("Need a valid domain in the path");
  }

  $self->add_error("Could not find domain autoconfig details");

  $self->print_errors();

  return Apache2::Const::OK;
}

sub return_domain_data {
  my ($self, $domain) = @_;

  # Avoid deep recursive lookups
  if ($self->{depth}++ > 10) {
    $self->add_error("Recursive lookup too deep");
    return undef;
  }
  # Avoid lookup loops
  if ($self->{seen_domains}->{$domain}++) {
    $self->add_error("Recursive domain loop");
    return undef;
  }

  # Check if it's from the pre-known list
  if ($self->return_known_domain($domain)) {
    # Found it and returned the data
    return 1;
  }

  # Or in our cache
  if ($self->return_cache_domain($domain)) {
    return 1;
  }

  # Resolve mx and txt records
  my $dns_results = $self->resolve_dns(
    [ "mx", $domain, "MX"],
    [ "txt", "mozautoconfig." . $domain, "TXT" ]
  );
  if (!$dns_results) {
    $self->add_error("Timeout on dns lookup");
    return undef;
  }

  # Check for valid TXT record
  my $dns_txt = $dns_results->{txt};
  if ($dns_txt && $self->return_domain_txt($domain, $dns_txt)) {
    return 1;
  }

  # Check for known primary MX records
  my $dns_mx = $dns_results->{mx};
  if ($dns_mx && $self->return_domain_mx($domain, $dns_mx)) {
    return 1;
  }

  return undef;
}

sub return_known_domain {
  my ($self, $domain) = @_;

  # Look for file in the known domains path
  my $known_domains_file = $self->known_domains_path($domain);
  warn "checking for known domain. path=$known_domains_file" if DEBUG;

  if (-f $known_domains_file) {
    warn "found known domain, returning data. path=$known_domains_file" if DEBUG;
    my $r = $self->{r};

    # TODO: Set Expires/Etag headers?

    $r->content_type('text/xml');
    $r->sendfile($known_domains_file);

    return 1;
  }

  return undef;
}

sub return_cache_domain {
  my ($self, $domain) = @_;

  # Look for file in the known domains path
  my $cache_domains_file = $self->cache_domains_path($domain);
  warn "checking cache domain. path=$cache_domains_file" if DEBUG;

  if ($cache_domains_file && -f($cache_domains_file)) {
    warn "found cache domain, returning data. path=$cache_domains_file" if DEBUG;

    my $r = $self->{r};

    # TODO: Set Expires/Etag headers?

    $r->headers_out()->add("X-MozAutoConfig", "UsingCached");
    $r->content_type('text/xml');
    $r->sendfile($cache_domains_file);

    return 1;
  }

  return undef;
}

sub return_domain_mx {
  my ($self, $domain, $dns_mx) = @_;

  if ($dns_mx && @$dns_mx) {

    # Pull out on MX results and sort by priority
    my @mx_exchanges = grep { $_->type() eq 'MX' } @$dns_mx;
    @mx_exchanges = sort { $a->preference() <=> $b->preference() } @mx_exchanges;

    # Use the lowest priority
    my $primary_mx = @mx_exchanges ? uc($mx_exchanges[0]->exchange()) : '';

    warn "checking primary mx. mx=$primary_mx" if DEBUG;

    # Primary MX record -> domain mapping
    if (my $alt_domain = $known_domains_mx{$primary_mx}) {
      warn "found known mx. mx=$primary_mx" if DEBUG;

      return $self->return_domain_data($alt_domain);
    }
  }

  return undef;
}

sub return_domain_txt {
  my ($self, $domain, $dns_txt) = @_;

  if ($dns_txt && @$dns_txt) {
    for (@$dns_txt) {
      if ($_->type() eq 'TXT') {
        my $txt_data = $_->txtdata();

        warn "found txt record. txt=$txt_data" if DEBUG;

        # Use an SPF like syntax that starts with "v=mozautoconfig1 "
        #  and then has lookup data
        
        # For now we support two formats:
        #  domain:otherdomain.com - repeat lookup for otherdomain.com
        #  url:http... - retrieve data from given url

        if ($txt_data =~ s#^v=mozautoconfig1 ##) {
          if ($txt_data =~ m#^domain:(${domain_re})$#) {
            my $domain = $1;

            warn "found txt domain reference. domain=$domain" if DEBUG;

            # Try and find domain details
            if ($self->return_domain_data($domain)) {
              return 1;
            }

            $self->add_error("Could not find $domain details");
          
          } elsif ($txt_data =~ m#^url:(https?://${domain_re}[\x21-\x7f]*)$#i) {
            my $url = $1;

            warn "found txt url reference. url=$url" if DEBUG;

            if ($self->return_domain_httpfetch($domain, $url)) {
              return 1;
            }

            $self->add_error("Fetch from $url failed");
          }
        }
      }
    }
  }

  return undef;
}

sub return_domain_httpfetch {
  my ($self, $domain, $url) = @_;

  $url =~ m#^https?://${domain_re}#i || die "URL sanity failure";

  my $ua = LWP::UserAgent->new(
    max_size => 32768,
    timeout => 10,
    parse_head => 0,
    protocols_allowed => [ 'http', 'https' ],
  );

  # Replace %%domain%% in url with original domain
  $url =~ s#\%\%domain\%\%#$self->{domain}#ge;

  warn "fetching url data. url=$url" if DEBUG;

  my $request = HTTP::Request->new(GET => $url);

  # Force a true 10 second timeout (see LWP docs about timeout param)
  my $result;
  eval {
    local $SIG{ALRM} = sub { die "timeout"; };
    my $old_alarm = alarm(10);
    $result = $ua->request($request);
    alarm($old_alarm);
  };
  if ($@ =~ /timeout/) {
    $self->add_error("A timeout occured fetching $url");
    return 0;

  } elsif ($@) {
    $self->add_error("An unexpected error occured feteching $url");
    return 0;
  }

  # Sanity check result and basic content expectation

  my $code = $result->code();
  if ($code != 200) {
    $self->add_error("An error occured fetching $url, response code $code");
    return 0;
  }

  my $content_type = $result->header('content-type');
  if ($content_type !~ m#^text/xml(?:$|;)#i) {
    $self->add_error("Fetched $url, but not text/xml content type");
    return 0;
  }

  my $content = $result->content();
  if ($content !~ m#^\s*<\?xml#) {
    $self->add_error("Fetched $url, but doesn't seem to start with an <?xml> section");
    return 0;
  }
  if ($content !~ m#<clientConfig>.*?</clientConfig>#s) {
    $self->add_error("Fetched $url, but doesn't seem to have a <clientConfig> block");
    return 0;
  }
  if ($content =~ m#<(?:html|head|title|meta|body|div|p)\b#i) {
    $self->add_error("Fetched $url, but appears to contain html like content");
    return 0;
  }

  # TODO: actually listen to Expires header, rather than out own
  #  arbitrary caching

  # Ok, data looks sane, lets cache it (original domain requested) locally, then return it to the client
  $self->store_cache_domain($self->{domain}, $content);

  # TODO: Set Expires/Etag headers?

  warn "url fetch success, returning data. url=$url" if DEBUG;

  my $r = $self->{r};
  $r->content_type('text/xml');
  $r->print($content);

  return 1;
}

sub store_cache_domain {
  my ($self, $domain, $content) = @_;

  my $cache_domains_file = $self->cache_domains_path($domain);

  warn "storing cache file. domain=$domain, path=$cache_domains_file" if DEBUG;

  # Use standard unix create tmp, rename into place for atomicity

  my ($tmp_fh, $tmp_file) = mkstemps($cache_domains_file . ".XXXXXX", "tmp");

  # Create to tmp file, and rename into place atomically
  if (!$tmp_fh || !$tmp_file) {
    warn "Open of tmp file failed, can't cache $domain data: $!";
    return 0;
  }

  print $tmp_fh $content;
  close $tmp_fh;

  if (!rename($tmp_file, $cache_domains_file)) {
    warn "Rename of tmp file $tmp_file to $cache_domains_file failed, can't cache $domain data: $!";
    unlink($tmp_file);
    return 0;
  }

  return 1;
}

sub resolve_dns {
  my ($self, @to_resolve) = @_;

  # Resolve records at the same time, so
  #  use Net::Resolve background query mode

  my $timeout    = 10;
  my $resolver   = Net::DNS::Resolver->new;

  my (%sockets, %reverse_sockets);

  # Save key => socket lookup, and reverse socket => key (stringify socket ref)
  for (@to_resolve) {
    my ($key, $domain, $type) = @$_;

    my $socket = $resolver->bgsend($domain, $type);
    $sockets{$key} = $socket;
    $reverse_sockets{"$socket"} = $key;
  }

  my $select = IO::Select->new(values %sockets);

  # Keep going until we have everything or we timeout
  my %results;
  while (keys %sockets && $timeout > 0.1) {

    # Find sockets with data, track timeout remaining
    my $start = time;
    my @ready = $select->can_read($timeout);
    $timeout -= time - $start;

    foreach my $socket (@ready) {
      my $packet = $resolver->bgread($socket);
      my $key = $reverse_sockets{"$socket"};

      $results{$key} = [ $packet->answer() ];

      # Cleanup all socket references so it auto-closes
      $select->remove($socket);
      delete $sockets{delete $reverse_sockets{"$socket"}};
    }
  }

  unless ($timeout > 0.1) {
    return undef;
  }

  return \%results;
}

sub known_domains_path {
  my ($self, $domain) = @_;

  # Sanity check domain in a few ways (should never be a problem, but be proactive)
  $domain !~ m#/# || die "Domain contains /";
  $domain !~ m#\.\.# || die "Domain contains ..";
  $domain =~ m#^${domain_re}$# || die "Unexpected invalid domain '$domain'";

  return $self->{known_domains_path} . "/" . $domain;
}

sub cache_domains_path {
  my ($self, $domain) = @_;
  
  # Sanity check domain in a few ways (should never be a problem, but be proactive)
  $domain !~ m#/# || die "Domain contains /";
  $domain !~ m#\.\.# || die "Domain contains ..";
  $domain =~ m#^${domain_re}$# || die "Unexpected invalid domain";

  my $cache_domains_path = $self->{cache_domains_path}
    || return undef;

  # Use 2 level deep dir on domain name
  $cache_domains_path .= "/" . substr($domain, 0, 1) . "/" . substr($domain, 1, 1);

  -d($cache_domains_path) || mkpath($cache_domains_path);

  return $cache_domains_path . "/" . $domain;
}

sub add_error {
  my $self = shift;

  push @{$self->{errors}}, @_;
  warn "adding errors. errors=@_" if DEBUG;
}

sub print_errors {
  my $self = shift;

  my ($r, $errors) = @$self{qw(r errors)};
  $r->status(Apache2::Const::HTTP_NOT_FOUND);
  $r->content_type('text/plain');
  print map { $_ . "\n" } @$errors;
}


1;

