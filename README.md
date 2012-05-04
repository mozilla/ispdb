
experimental django front-end to figure out workflow of ISP database info
for the Thunderbird autoconfig database

## Step 0: Dependencies
   *  django-1.1
   *  django-openid-auth
   *  python-openid
   *  django-nose 
   *  lxml

    You can install all of the above with:
    pip install django python-openid django-openid-auth django-nose lxml
    Note: You may have to do an "easy_install pip" first

## Getting Started
1. python manage.py syncdb
2. convert existing XML data to the DB:
   # have http://svn.mozilla.org/mozillamessaging.com/sites/autoconfig.mozillamessaging.com/trunk checked out at ../autoconfig_data
   # if autoconfig_data is somewhere else, you can set the env't var AUTOCONFIG_DATA to  point to it
   echo 'import convert;convert.main()' | python manage.py shell --settings=local_settings
3. python manage.py runserver
4. then hit http://localhost:8000
