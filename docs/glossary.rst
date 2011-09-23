.. _Glossary:

Glossary
********

.. glossary::

   workitem
      A JSON hash that contains various bits and pieces of information

   actions
      A list of dicts that contains information about an OBS request from a
      user. For submit requests it will look like:
      [{
      "sourceproject":"foo",
      "sourcepackage":"bar",
      "targetproject":"FOO",
      "targetpackage":"BAR",
      "sourcerevision":1
      }]

