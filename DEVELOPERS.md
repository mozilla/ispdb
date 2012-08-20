# ISPDB

ISPDB is a Django front-end to figure out workflow of ISP database info for the
Thunderbird autoconfig database. 

This file contains useful informations to help developers.

## Documentation 

### Models

ISPDB has the following models: Domain, DomainRequest, Config, Issue, DocURL,
DocURLDesc, EnableURL, EnableURLInst. 

Both Domain and DomainRequest represent a mail domain. The difference is that
DomainRequest is not approved yet. It means that users can vote on it and their
name attribute is not unique (we can have more than one DomainRequest with the
same name). A Config holds the domain configuration. It can be related to more
than one domain. It has zero or more documentation pages (DocURL) and zero or
more enable pages (EnableURL). A DocURL has one or more descriptions
(DocURLDesc) and a EnableURL has one or more instructions (EnableURLInst).
Because those 4 classes are very similar, we have created common model and form
classes.

The Issue model represents a reported issue. It is related to the configuration
and optionally to an user suggested configuration.

### Forms

The complexity of the forms is in the form's classes. For example, ConfigForm
class has domain_formset, docurl_formset and enableurl_formset attributes. So we
can do things like the save_all method which save all of the forms (Domain,
Config, DocURL, EnableURL), simplifying the views.

Also there are two nested forms (for DocURL and EnableURL models). So each
DocURLForm has a DocURLDesc formset and each EnableURLForm has a EnableURLInst
formset. 

It is possible to add new forms dynamically in all of the formsets. There are
two form classes to help with this task: DynamicModelForm and
DynamicBaseModelFormSet. Basically they add a DELETE hidden boolean field and a
overriden empty_form attribute (see below).  

#### Dynamic Forms

enter_config.html template has hidden textarea elements which contains empty
forms. These empty forms have on their attributes JQuery Validation tags, in our
case "{1}-{0}" string, which are replaced with a form prefix and a index.
