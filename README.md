This repository is no longer active, current ISPDB is available at: https://github.com/thundernest/autoconfig

experimental django front-end to figure out workflow of ISP database info
for the Thunderbird autoconfig database

## Dependencies

  You can install all of the dependencies with:

  pip install -r requirements.txt

  Note: You may have to do an "easy_install pip" first. See requirements.txt for details on what we depend on.

## Getting Started
1. python ../manage.py syncdb
2. convert existing XML data to the DB:

  have http://svn.mozilla.org/mozillamessaging.com/sites/autoconfig.mozillamessaging.com/trunk checked out at ../autoconfig_data
 
  if autoconfig_data is somewhere else, you can set the env't var AUTOCONFIG_DATA to  point to it
  
  echo 'import ispdb.convert;ispdb.convert.main()' | python manage.py shell

3. python manage.py runserver
4. then hit http://localhost:8000
