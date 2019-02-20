# -*- coding: utf-8 -*-

from base import LmfdbTest

class LfunctionTest(LmfdbTest):

    def check(self, homepage, path, text):
        assert path in homepage, "path not in homepage."
        assert text in self.tc.get(path).data, "text %s not in pathpage %s."%(text, path)
    
    # Testing all links in the home page

    def test_table(self):
        r"""
        Check that the links in the /L/degree2/ table work.
        """
        homepage = self.tc.get("/L/degree2/").data
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000032",
                   'Maass')
        self.check(homepage,
                   "/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000032",
                   'Maass')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/Maass/4f55570e88aece241f00000c",
                   'Maass')
        self.check(homepage,
                   "/ModularForm/GL2/Q/Maass/4f55570e88aece241f00000c",
                   'Maass')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/Maass/4f55571b88aece241f000013",
                   'Maass')
        self.check(homepage,
                   "/ModularForm/GL2/Q/Maass/4f55571b88aece241f000013",
                   'Maass')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/holomorphic/1/12/a/a/",
                   'Modular')
        self.check(homepage,
                   "/ModularForm/GL2/Q/holomorphic/1/12/a/a/",
                   'Modular')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/holomorphic/7/3/b/a/",
                   'Modular')
        self.check(homepage,
                   "/ModularForm/GL2/Q/holomorphic/7/3/b/a/",
                   'Modular')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/holomorphic/5/6/4/a/1/",
                   'Modular')
        self.check(homepage,
                   "/ModularForm/GL2/Q/holomorphic/5/6/b/a/",
                   'Modular')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/holomorphic/3/9/2/a/1/",
                   'Modular')
        self.check(homepage,
                   "/ModularForm/GL2/Q/holomorphic/3/9/b/a/",
                   'Modular')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/Maass/4f4bf1c388aece438d000002/",
                   'Modular')
        self.check(homepage,
                   "/ModularForm/GL2/Q/Maass/4f4bf1c388aece438d000002",
                   'Modular')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/holomorphic/6/4/a/a/",
                   'Modular')
        self.check(homepage,
                   "/ModularForm/GL2/Q/holomorphic/6/4/a/a/",
                   'Modular')
        self.check(homepage,
                   "/L/EllipticCurve/Q/11/a",
                   'Elliptic')
        self.check(homepage,
                   "/EllipticCurve/Q/11/a",
                   'Elliptic')
        self.check(homepage,
                   "/ModularForm/GL2/Q/holomorphic/11/2/a/a/",
                   'Modular')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000033",
                   'Modular')
        self.check(homepage,
                   "/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000033",
                   'Modular')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/holomorphic/5/6/4/a/2/",
                   'Modular')
        self.check(homepage,
                   "/ModularForm/GL2/Q/holomorphic/5/6/b/a/",
                   'Modular')
        self.check(homepage,
                   "/L/EllipticCurve/Q/36/a/",
                   'Elliptic')
        self.check(homepage,
                   "/EllipticCurve/Q/36/a",
                   'Elliptic')
        self.check(homepage,
                   "ModularForm/GL2/Q/holomorphic/36/2/a/a/",
                   'Modular')
        self.check(homepage,
                   "/L/ArtinRepresentation/2.2e2_37.3t2.1c1",
                   'Artin')
        self.check(homepage,
                   "/ArtinRepresentation/2.2e2_37.3t2.1c1",
                   'Artin')
        self.check(homepage,
                   "/L/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000000",
                   'Modular')
        self.check(homepage,
                   "/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000000",
                   'Modular')
        self.check(homepage,
                   "/L/ArtinRepresentation/2.163.8t12.1c2",
                   'Artin')
        self.check(homepage,
                   "/ArtinRepresentation/2.163.8t12.1c2",
                   'Artin')
        self.check(homepage,
                   "/L/ArtinRepresentation/2.2e2_17.4t3.2c1",
                   'Artin')
        self.check(homepage,
                   "/ArtinRepresentation/2.2e2_17.4t3.2c1",
                   'Artin')
        self.check(homepage,
                   "/L/ArtinRepresentation/2.2e3_17.4t3.4c1",
                   'Artin')
        self.check(homepage,
                   "/ArtinRepresentation/2.2e3_17.4t3.4c1",
                   'Artin')
        self.check(homepage,
                   "/L/EllipticCurve/Q/234446/a",
                   'Elliptic')
        self.check(homepage,
                   "/EllipticCurve/Q/234446/a",
                   'Elliptic')

        

