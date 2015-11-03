.. This README is meant for consumption by humans and pypi. Pypi can render rst files so please do not use Sphinx features.
   If you want to learn more about writing documentation, please check out: http://docs.plone.org/about/documentation_styleguide_addons.html
   This text does not appear on pypi or github. It is a comment.

==============================================================================
collective.contentexport
==============================================================================


Features
--------

- Provides a form ``/@@export_view`` to configure the export.
- Exports dexterity content as xlsx, csv and json
- Exports blobs from image, file and relation-fields as zip-files


Installation
------------

Install collective.contentexport by adding it to your buildout::

    [buildout]

    ...

    eggs =
        collective.contentexport


and then running ``bin/buildout``


Contribute
----------

- Issue Tracker: https://github.com/starzel/collective.contentexport/issues
- Source Code: https://github.com/starzel/collective.contentexport


Support
-------

If you are having issues, please let us know at https://github.com/starzel/collective.contentexport/issues.


License
-------

The project is licensed under the GPLv2.
