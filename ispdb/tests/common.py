# -*- coding: utf-8 -*-

import httplib

# Redirect to /add/ on success
success_code = httplib.FOUND
# Return with form errors if form is invalid
fail_code = httplib.OK


def asking_domain_form():
    return {
            "asking_or_adding": "asking",
            "domain-TOTAL_FORMS": "1",
            "domain-INITIAL_FORMS": "0",
            "domain-0-id": "",
            "domain-0-name": "test.com",
            "domain-0-DELETE": "False",
            "docurl-INITIAL_FORMS": "0",
            "docurl-TOTAL_FORMS": "1",
            "docurl-MAX_NUM_FORMS": "",
            "docurl-0-id": "",
            "docurl-0-DELETE": "False",
            "docurl-0-url": "http://test.com/",
            "desc_0-INITIAL_FORMS": "0",
            "desc_0-TOTAL_FORMS": "1",
            "desc_0-MAX_NUM_FORMS": "",
            "desc_0-0-id": "",
            "desc_0-0-DELETE": "False",
            "desc_0-0-language": "en",
            "desc_0-0-description": "test",
            "enableurl-INITIAL_FORMS": "0",
            "enableurl-TOTAL_FORMS": "1",
            "enableurl-MAX_NUM_FORMS": "",
            "enableurl-0-id": "",
            "enableurl-0-DELETE": "False",
            "enableurl-0-url": "http://test.com/",
            "inst_0-INITIAL_FORMS": "0",
            "inst_0-TOTAL_FORMS": "1",
            "inst_0-MAX_NUM_FORMS": "",
            "inst_0-0-id": "",
            "inst_0-0-DELETE": "False",
            "inst_0-0-language": "en",
            "inst_0-0-description": "test"
           }


def adding_domain_form():
    return {
            "asking_or_adding": "adding",
            "domain-TOTAL_FORMS": "1",
            "domain-INITIAL_FORMS": "0",
            "domain-MAX_NUM_FORMS": "10",
            "domain-0-id": "",
            "domain-0-name": "test.com",
            "domain-0-DELETE": "False",
            "display_name": "test",
            "display_short_name": "test",
            "incoming_type": "imap",
            "incoming_hostname": "foo",
            "incoming_port": "333",
            "incoming_socket_type": "plain",
            "incoming_authentication": "password-cleartext",
            "incoming_username_form": "%25EMAILLOCALPART%25",
            "outgoing_hostname": "bar",
            "outgoing_port": "334",
            "outgoing_socket_type": "STARTTLS",
            "outgoing_username_form": "%25EMAILLOCALPART%25",
            "outgoing_authentication": "password-cleartext",
            "docurl-INITIAL_FORMS": "0",
            "docurl-TOTAL_FORMS": "1",
            "docurl-MAX_NUM_FORMS": "",
            "docurl-0-id": "",
            "docurl-0-DELETE": "False",
            "docurl-0-url": "http://test.com/",
            "desc_0-INITIAL_FORMS": "0",
            "desc_0-TOTAL_FORMS": "1",
            "desc_0-MAX_NUM_FORMS": "",
            "desc_0-0-id": "",
            "desc_0-0-DELETE": "False",
            "desc_0-0-language": "en",
            "desc_0-0-description": "test",
            "enableurl-INITIAL_FORMS": "0",
            "enableurl-TOTAL_FORMS": "1",
            "enableurl-MAX_NUM_FORMS": "",
            "enableurl-0-id": "",
            "enableurl-0-DELETE": "False",
            "enableurl-0-url": "http://test.com/",
            "inst_0-INITIAL_FORMS": "0",
            "inst_0-TOTAL_FORMS": "1",
            "inst_0-MAX_NUM_FORMS": "",
            "inst_0-0-id": "",
            "inst_0-0-DELETE": "False",
            "inst_0-0-language": "en",
            "inst_0-0-description": "test"
           }
