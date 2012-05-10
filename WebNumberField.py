# -*- coding: utf-8 -*-
import base
from sage.all import *
import re
import pymongo
import bson
from utils import *
from transitive_group import group_display_short
#logger = make_logger("DC")

## Turn a list into a string (without brackets)
def list2string(li):
  li2 = [str(x) for x in li]
  return ','.join(li2)

def string2list(s):
  s = str(s)
  if s=='': return []
  return [int(a) for a in s.split(',')]

def decodedisc(ads, s):
  return ZZ(ads[3:])*s

class WebNumberField:
  """
   Class for retrieving number field information from the database
  """
  def __init__(self, label, data=None):
    self.label = label
    if data is None:
      self._data = self._get_dbdata()
    else:
      self._data = data

  @classmethod
  def from_coeffs(cls, coeffs):
    if isinstance(coeffs, list):
      coeffs = list2string(coeffs)
    if isinstance(coeffs, str):
      nfdb = base.getDBConnection().numberfields.fields
      f = nfdb.find_one({'coeffs': coeffs})
      if f is None:
        return cls('a')  # will initialize data to None
      return cls(f['label'], f)
    else:
      raise Exception('wrong type')

  def _get_dbdata(self):
    nfdb = base.getDBConnection().numberfields.fields
    return nfdb.find_one({'label': self.label})

  # Return discriminant as a sage int
  def disc(self):
    return decodedisc(self._data['disc_abs_key'], self._data['disc_sign'])

  # Return a nice string for the Galois group
  def galois_string(self):
    n = self._data['degree']
    t = self._data['galois']['t']
    C = base.getDBConnection()
    return group_display_short(n, t, C)

  def coeffs(self):
    return string2list(self._data['coeffs'])

  def signature(self):
    return string2list(self._data['sig'])

  def degree(self):
    return self._data['degree']

  def poly(self):
    return coeff_to_poly(string2list(self._data['coeffs']))

  def haskey(self, key):
    return key in self._data

  def regulator(self):
    if self.haskey('reg'): return self._data['reg']
    return None

  def fu(self): # fundamental units
    if self.haskey('units'): return self._data['units']
    return None

