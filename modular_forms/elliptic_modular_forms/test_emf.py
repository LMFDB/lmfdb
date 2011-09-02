
from base import LmfdbTest
from flask import request

from elliptic_modular_forms.views.emf_main import *

class CmfTest(LmfdbTest):
  def test_get_args(self):
    with self.app.test_client() as c:
      c.get("/ModularForm/GL2/Q/holomorphic/1/2/3?label=l")
      got = get_args()
      assert request.args['label'] == "l"
      assert got['level'] == "1"
      assert got['weight'] == 2
      assert got['character'] == 3
      assert got['label'] == "l"



