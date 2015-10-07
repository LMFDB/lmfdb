import mdb
import mdb.schema
import mdb.schema_sage
from mdb.schema_sage import ModularSymbols_ambient,ModularSymbols_newspace_factor,ModularSymbols_oldspace_factor,Coefficient,NumberField,ModularSymbols_base_field, CoefficientField,AlgebraicNumber

from lmfdb.modular_forms.elliptic_modular_forms import EMF, emf_logger, emf

met = ['GET', 'POST']

@emf.route("/new/", methods=met)
@emf.route("/new/<int:level>/", methods=met)
@emf.route("/new/<int:level>/<int:weight>/", methods=met)
@emf.route("/new/<int:level>/<int:weight>/<int:character>/", methods=met)
@emf.route("/new/<int:level>/<int:weight>/<int:character>/<label>", methods=met)
@emf.route("/new/<int:level>/<int:weight>/<int:character>/<label>/", methods=met)
def render_new_elliptic_modular_forms(level=0,weight=0,character=0,label='',**kwds):
    if level>0 and weight>0 and character>0:
        f = find_modular_form(level,weight,character,label)
    
    return     
