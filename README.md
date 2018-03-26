A python client implementation of the [dflat] and [redd] specifications
for versioning of simple filesystem based digital objects.

Installation:

  easy_install dflat

Usage:

  cd /my/object/directory/
  dflat init
  dflat checkout 
  # ... make some changes to v002
  dflat status
  dflat commit
  dflat export v001  

[dflat]: http://www.cdlib.org/inside/diglib/dflat/dflatspec.pdf
[redd]: http://www.cdlib.org/inside/diglib/redd/reddspec.html
