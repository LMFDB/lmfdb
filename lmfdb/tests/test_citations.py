# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest


class CitationTest(LmfdbTest):
    '''
    Test that the citations page exists and the associated bib page exists
    '''

    def test_citation_root(self):
        '''
        Checking /citation page
        '''
        r = self.tc.get('/citation')
        assert "A list of articles which cite the LMFDB" in r.data

    def test_how_to_cite(self):
        '''
        Checking "How to Cite" /citation/citing
        '''
        r = self.tc.get('/citation/citing')
        assert "The BibTeX entry is" in r.data
        assert "To cite a specific page in the LMFDB" in r.data

    def test_citation_specific(self):
        '''
        Checking that a known citation appears in /citation/citations list
        '''
        r = self.tc.get('/citation/citations')
        assert "Thomas&nbsp;A Hulse" in r.data
        assert "Counting square discriminants" in r.data

    def test_cite_bib(self):
        '''
        Checking that a known bib is in /citation/citations_bib bibliography
        '''
        r = self.tc.get('/citation/citations_bib')
        assert "Hulse, Thomas A" in r.data
        assert "Counting square discriminants" in r.data
