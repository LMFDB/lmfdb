# This data is loaded into the smf_families postgres table

families = [
{
    "name": "Gamma0_2",
    "degree": int(2),
    "dim_args_default": {"k": "4..24", "j": "2"},
    "latex_name": "M_{k,j}\\left(\\Gamma_0(2)\\right)", 
    "order": int(50)
},
{
    "name": "Gamma0_3", 
    "degree": int(2),
    "dim_args_default": { "k": "0..20" },
    "latex_name": "M_k\\left(\\Gamma_0(3)\\right)",
    "order": int(80)
},
{
    "name": "Gamma0_3_psi_3", 
    "degree": int(2),
    "dim_args_default": { "k": "0..20" },
    "latex_name": "M_k\\left(\\Gamma_0(3),\\psi_3\\right)",
    "order": int(90)
},
{
    "name": "Gamma0_4_half",
    "degree": int(2),
    "dim_args_default": { "k": "1..20" },
    "latex_name": "M_{k-1/2}\\left(\\Gamma_0(4)\\right)",
    "order": int(108)
},
{
    "name": "Gamma0_4",
    "degree": int(2),
    "dim_args_default": { "k": "0..20" },
    "latex_name": "M_k\\left(\\Gamma_0(4)\\right)", 
    "order": int(100)
},
{
    "name": "Gamma0_4_psi_4",
    "degree": int(2),
    "dim_args_default": { "k": "0..40" },
    "latex_name": "M_k\\left(\\Gamma_0(4),\\psi_4\\right)",
    "order": int(105)
},
{
    "name": "Gamma1_2",
    "degree": int(2),
    "dim_args_default": { "k": "4..10", "j": "2" },
    "latex_name": "M_{k,j}\\left(\\Gamma_1(2)\\right)", 
    "order": int(60)
},
{
    "name": "Gamma_2", 
    "degree": int(2),
    "dim_args_default": { "k": "4..10", "j": "2" },
    "latex_name": "M_{k,j}\\left(\\Gamma(2)\\right)", 
    "order": int(70)
},
{
    "name": "Kp", 
    "degree": int(2),
    "latex_name": "M_2\\left(K(p)\\right)", 
    "order": int(110)
},
{
    "name": "Sp4Z_2", 
    "degree": int(2),
    "dim_args_default": { "k": "4..24" },
    "latex_name": "M_{k,2}\\left(\\textrm{Sp}(4,\\mathbb{Z})\\right)", 
    "order": int(30)
},
{
    "name": "Sp4Z_j", 
    "degree": int(2),
    "dim_args_default": { "k": "4..24", "j": "4" },
    "latex_name": "M_{k,j}\\left(\\textrm{Sp}(4,\\mathbb{Z})\\right)", 
    "order": int(40)
},
{
    "name": "Sp4Z", 
    "degree": int(2),
    "dim_args_default": { "k": "0..20" },
    "latex_name": "M_k\\left({\\textrm{Sp}}(4,\\mathbb{Z})\\right)", 
    "order": int(10)
},
{
    "name": "Sp6Z",
    "degree": int(3),
    "dim_args_default": { "k": "0..20" },
    "latex_name": "M_{k}\\left(\\textrm{Sp}(6,\\mathbb{Z})\\right)", 
    "order": int(130)
},
{
    "name": "Sp8Z", 
    "degree": int(4),
    "dim_args_default": { "k": "0..16" },
    "latex_name": "M_k\\left(\\textrm{Sp}(8,\\mathbb{Z})\\right)", 
    "order": int(140)
},
]
