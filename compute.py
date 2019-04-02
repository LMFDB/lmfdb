import yaml
import json
from bson import ObjectId
from bson.json_util import loads, dumps
from sage.interfaces.magma import Magma
from sets import Set
import sys
import os
import time

magma = Magma()

# get file name as command-line argument
if len(sys.argv) == 1:
    sys.exit('Please give an input file name as a command-line argument. ')
input_file_name = sys.argv[1]
output_file_name = input_file_name
if output_file_name.endswith('.json'):
    output_file_name = input_file_name[:-5]
output_file_name += '-output.yml'
input_file = open(input_file_name, 'r')
output_file = open(output_file_name, 'a')

# Flush changes in a file to disk
def flush(file):
    file.flush()
    os.fsync(file.fileno())

helper_code = '''
/* helper functions for orbits */
/* L is list of IDs */
PrtOrbit:=function(L);
   prtstring:="  - [";
   for i in [1..#L-1] do
      prtstring:=prtstring cat "'" cat L[i] cat "'";
      prtstring:=prtstring cat ",";
   end for;
   prtstring:=prtstring cat "'" cat  L[#L] cat "'" cat "]";
   return prtstring; 
end function;
Qi:=function(k,L);
   left_unchanged:=[L[i] : i in [1..k-1]];
   braid:=[L[k]*L[k+1]*L[k]^-1,L[k]];
   right_unchanged:=[L[i]: i in [k+2..#L] ];
   return left_unchanged cat braid cat right_unchanged;
end function;
BrdOrbit:=function(L,r);
   for ell in L do
      for i in [1..r-1] do
         brd:=Qi(i,ell);
         L join:={brd};
      end for;   
   end for;
   return L;
end function;
Strg:=function(L);
   sg:="[";
   for i in [1..#L-1] do
     sg:= sg cat IntegerToString(L[i]) cat ",";
   end for;
   sg:= sg cat IntegerToString(L[#L]) cat "]";
   return sg;
end function;
OuterAutOrbit:=function(L,G);
   for ell in L do
     for g in G do
        L join:={g(ell)};
     end for;
   end for;
   return L;
end function;
OrbitComputeBraid:=function(Vects,r);
   T:={};
   Orbs:=[];
   genvecs:=Vects;   
   while Vects ne {} do
      rand:=Random(Vects);
      T join:={rand};
      
      tempcount:=0;
      Orb:={rand};
      /* t1:=Cputime(); */
      while (tempcount eq 0) do
         sizeOrb:=#Orb;
         Orb:=BrdOrbit(Orb,r); 
         if #Orb eq sizeOrb  then
            tempcount:=1;  /* stops when outer aut doesn't add more */
            N:=genvecs meet Orb;
            Append(~Orbs,N);
         else
            Vects diff:=Orb;
            if #Vects eq 0 then
               N:=genvecs meet Orb;
               Append(~Orbs,N);
               tempcount:=1;/* stop if all in one orbit or got to last */
            end if;
         end if;    
      end while;   
   end while;  /* while Vects not empty */
   return T, Orbs;
end function;
OrbitComputeAut:=function(Vects,A,r);
   /* T will be list of final orbits, A is outer auts */
   T:={};
   Orbs:=[];
   genvecs:=Vects; 
   while Vects ne {} do
      rand:=Random(Vects);
      T join:={rand};
      tempcount:=0;
      Orb:={rand};
      /* t1:=Cputime(); */
      while (tempcount eq 0) do
         sizeOrb:=#Orb;
         Orb:=OuterAutOrbit(Orb,A);
         Orb:=BrdOrbit(Orb,r);
         if #Orb eq sizeOrb  then
            tempcount:=1;  /* stops when outer aut doesn't add more */
            N:=genvecs meet Orb;
            Append(~Orbs,N);
         else
            Vects diff:=Orb;
            if #Vects eq 0 then
                N:=genvecs meet Orb;
                Append(~Orbs,N);
               tempcount:=1;/* stop if all in one orbit or got to last */
            end if;
         end if;    
      end while;   
   end while;  /* while Vects not empty */
   return T, Orbs;
end function;
/*
AbelianOrbitComputeAut:=function(Vects,A,r);
   /* T will be list of final orbits, A is outer auts */
   T:={};
   Orbs:=[];
   genvecs:=Vects; 
   while Vects ne {} do
      rand:=Random(Vects);
      T join:={rand};
      tempcount:=0;
      Orb:={rand};
      /* t1:=Cputime(); */
      while (tempcount eq 0) do
         sizeOrb:=#Orb;
         Orb:=OuterAutOrbit(Orb,A);
         if #Orb eq sizeOrb  then
            tempcount:=1;  /* stops when outer aut doesn't add more */
            N:=genvecs meet Orb;
            Append(~Orbs,N);
         else
            Vects diff:=Orb;
            if #Vects eq 0 then
                N:=genvecs meet Orb;
                Append(~Orbs,N);
               tempcount:=1;/* stop if all in one orbit or got to last */
            end if;
         end if;    
      end while;   
   end while;  /* while Vects not empty */
   return T, Orbs;
end function;*/
''' 

top_matter = '''
// The results are stored in a list of records called 'data'
// The results for braid equivalence are stored in a list of records called 'braid_data'
RecFormat:=recformat<group, gp_id, signature, gen_vectors, genus, dimension, r, g0, vector_id>;
data:=[];
braid_data:=[];
// Create group as a permutation group, and generate data which is the same for all entries.
gp_id:={group};
H:=SmallGroup(gp_id[1],gp_id[2]);
n:=#H;
LP:=[];
LG:=[g : g in H];
for i in [1..n] do 
    x:=LG[i]; Tx:=[LG[j]*x : j in [1..n]]; permL:=[];
    for j in [1..n] do
        for k in [1..n] do
            if Tx[j] eq LG[k] then
                permL[j]:=k;
                break;
            end if;
        end for;
    end for;
    Append(~LP,permL);
end for;
G:=PermutationGroup<n|LP>;
signature:={signature};
genus:={genus};
r:=#signature-1;
g0:=signature[1];
dim:=r-3;
S:=Sym(gp_id[1]);
'''

action_code = '''
// Here we add an action to data.
gen_vectors:={gen_vectors};
gen_vectors_as_perm:=[S!perm : perm in gen_vectors];
Append(~data, rec<RecFormat | group:=G,
                              gp_id:=gp_id,
                              signature:=signature,
                              gen_vectors:=gen_vectors_as_perm,
                              genus:=genus,
                              dimension:=dim,
                              r:=r,
                              g0:=g0,
                              vector_id:="{_id}">);
'''

braid_action_code = '''
Append(~braid_data, rec<RecFormat | group:=G,
                                    gp_id:=gp_id,
                                    signature:=signature,
                                    gen_vectors:=gen_vectors_as_perm,
                                    genus:=genus,
                                    dimension:=dim,
                                    r:=r,
                                    g0:=g0,
                                    vector_id:="{_id}">);
'''

orbits_code = '''
prtfile:="orbits_magma2.yml";
/* This next command keeps Magma from printing line breaks */
SetColumns(0);
genvecs:=[[* data[i]`gen_vectors,data[i]`vector_id *] : i in [1..#data]];
braid_genvecs:=[[* braid_data[i]`gen_vectors,braid_data[i]`vector_id *] : i in [1..#braid_data]];
/* MAIN CODE */
if #genvecs gt 0 then
   if #genvecs eq 1 then
      PrintFile(prtfile, "topological:");
      PrintFile(prtfile, "-   "); 
     
   else
      B:=AutomorphismGroup(G);     
      f,A,k:=PermutationRepresentation(B);
      h:=Inverse(f); /* Map from A to B */
      aut:= [h(aL): aL in A | not IsInner(h(aL))];   /* Outer Automorphisms */
      Vects:={g[1] : g in genvecs};
      braid_Vects:={g[1] : g in braid_genvecs};
      BrdRep,BrdOrbs:=OrbitComputeBraid(braid_Vects,#signature-1);
      if #BrdRep eq 1 then
      	TopRep:=BrdRep;
        TopOrbs:=BrdOrbs;
      else
        TopRep,TopOrbs:=OrbitComputeAut(Vects,aut,#signature-1);    
      end if;
      TopOrbsID:=[];
      for j in [1..#TopOrbs] do
         orb:=TopOrbs[j];
         Append(~TopOrbsID,[* *]);
         for orbt in orb do
            for i in [1..#genvecs] do
               if genvecs[i,1] eq orbt then
                  Append(~TopOrbsID[j],genvecs[i,2]);
                  break i;
               end if;
            end for;  
         end for;
      end for;    
      
      BrdOrbsID:=[];
      for j in [1..#BrdOrbs] do
         orb:=BrdOrbs[j];
         Append(~BrdOrbsID,[*  *]);
         for orbt in orb do
            for i in [1..#braid_genvecs] do
               if braid_genvecs[i,1] eq orbt then
                  Append(~BrdOrbsID[j],braid_genvecs[i,2]);
                  break i;
               end if;
            end for;
         end for;
      end for;
      print "topological:";
      for j in [1..#TopOrbs]  do
         print PrtOrbit(TopOrbsID[j]);
      end for;
      print "braid:";
      for j in [1..#BrdOrbs] do
         print PrtOrbit(BrdOrbsID[j]);
      end for;
  end if; /* whether 1 generating vector or more */
end if;   /* whether any generating vectors */
'''

def find_representatives(orbits):
    reps = {}
    for orbit in orbits:
        rep = min(orbit)
        for object_id in orbit:
            reps[object_id] = rep
    return reps

def save_output(label, magma_output):
    output_file.write('# {}'.format(label))
    braid_reps = find_representatives(magma_output['braid'])
    top_reps = find_representatives(magma_output['topological'])
    for object_id in braid_reps:
        braid_rep = braid_reps[object_id]
        top_rep = top_reps[object_id]
        output_file.write('''
{0}:
  topological: {1}
  braid: {2}
'''.format(object_id, top_rep, braid_rep))
    flush(output_file)

def run_magma(family):
    label = family[0]['label']
    if len(family) == 1:
        vector_id = family[0]['id']
        save_output(label, {
            'braid': [[vector_id]],
            'topological': [[vector_id]]})
        return
    group = json.loads(family[0]['group'])
    is_abelian = magma.eval("IsAbelian(SmallGroup({},{}))".format(*group)) == 'true'
    compute_braid = any(vec['cc'][1] > 1 for vec in family)
    code = helper_code + top_matter.format(**family[0])
    for vector in family:
        code += action_code.format(**vector)
        if compute_braid:
            code += braid_action_code.format(**vector)
    code += orbits_code
    magma_output = magma.eval(code)
    if not compute_braid or is_abelian:
        for vector in family:
            magma_output += '\n  - [{}]'.format(vector['_id'])
    save_output(label, yaml.load(magma_output))

sum_time = 0.0        
for line in input_file:
    family = loads(line)
    print "Starting family {0}".format(family[0]['label'])
    sys.stdout.flush()
    start = time.time()
    run_magma(family)
    end = time.time()
    sum_time += end - start
    print end - start
    sys.stdout.flush()
print sum_time
print "Done" + input_file_name

input_file.close()
output_file.close()
