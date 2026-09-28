# Vendored runtime files

These files are copied verbatim from their upstream projects.

- CSInterface.js — Adobe CEP Resources, CEP 11.x API bridge.
- json2.js — Douglas Crockford JSON-js, public domain ES3 JSON implementation.

They are vendored so a clean FSTR Line test never depends on another installed extension, an internet connection, or leaked host globals.
