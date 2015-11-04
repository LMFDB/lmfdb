# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2


class HomePageTest(LmfdbTest):

    def check(self,homepage,path,text):
        assert path in homepage
        assert text in self.tc.get(path).data

    def check_external(self, homepage, path, text):
        import urllib2
        assert path in homepage
        assert text in urllib2.urlopen(path).read()

    # All tests should pass
    #
    # The acknowledgments page
    def test_acknowledgements(self):
        homepage = self.tc.get("/acknowledgment").data
        assert 'American Institute of Mathematics' in homepage

    #
    # Link to workshops page
    def test_workshops(self):
        homepage = self.tc.get("/workshops").data
        assert 'Computational Aspects of the Langlands Program' in homepage

    #
    # Link to Computational Aspects of the Langlands Program
    def test_(self):
        homepage = self.tc.get("https://icerm.brown.edu/sp-f15/").data
        assert 'computational infrastructure underpinning the Langlands program' in homepage   
      
        
    #
    # Link to Computational Representation Theory in Number Theory
    def test_(self):
        homepage = self.tc.get("http://people.oregonstate.edu/~swisherh/CRTNTconference/index.html").data
        assert 'Galois representations' in homepage
        
    #
    # Link to Advanced School and Workshop on L-functions and Modular Forms 
    def test_(self):
        homepage = self.tc.get("http://indico.ictp.it/event/a13219/material/1/0.pdf").data
        assert 'aspects of computational algebra' in homepage        
        
    #
    # Link to LMFDB Workshop
    def test_(self):
        homepage = self.tc.get("http://www2.warwick.ac.uk/fac/sci/maths/research/events/2013-2014/nonsymp/lmfdb/").data
        assert 'elliptic curves over number fields' in homepage
        
        
    #
    # Link to Curves and Automorphic Forms
    def test_(self):
        homepage = self.tc.get("http://hobbes.la.asu.edu/lmfdb-14/").data
        assert 'Arizona State University' in homepage                 


    #
    # Link to Bristol LMFDB Workshop III
    def test_(self):
        homepage = self.tc.get("http://www.maths.bris.ac.uk/~maarb/public/lmfdb2013.html").data
        assert 'Development of algorithms' in homepage        

    #
    # Link to Online databases: from L-functions to combinatorics
    def test_(self):
        homepage = self.tc.get("http://icms.org.uk/workshops/onlinedatabases").data
        assert 'development of new software tools' in homepage
        
    #
    # Link to Arithmetic Statistics
    def test_(self):
        homepage = self.tc.get("https://www.msri.org/programs/262").data
        assert 'algebraic number fields' in homepage
        
        
    #
    # Link to L-functions and Modular Forms I
    def test_(self):
        homepage = self.tc.get("http://aimath.org/pastworkshops/lfunctionsandmf.html").data
        assert 'L-functions and modular forms' in homepage
        
        
