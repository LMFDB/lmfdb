
# This implements new type generation facilities
# For instance, we can do Array(Int, Int, Int), immediately creating a type that consists of length 3 lists of Int
# This can then inherit additional functionalities:

# class WithFunctionalities(Array(Int,Int,Int)):
#   def extra_func(self,...):
#       pass

# In addition, it automatically acquires a __init__ function, that ensures type conversions.

# In fact, we can also do Array(f1,f2,f3), which gives a class as well, but that is callable
# Array(f1,f2,f3)([arg1,arg2,arg3]) gives [f1(arg1),f2(arg2),f3(arg3)]
# This is useful for type conversions on whole json records

# Similar functionalities exist for Dict, and can be combined recursively.

# author: Paul-Olivier Dehaye


def wrapper(f):
    def g(*args, **kwargs):
        #print f.__name__, " called with"
        #print "     *args: ", args
        #print "     **kwargs", kwargs
        tmp = f(*args, **kwargs)
        #print f.__name__, "      is returning      ", tmp
        return tmp
    return g


def ImmutableExtensionFactory(t, t_name):
    # I will need to add other methods to int, str and float, so I need to have a way to subclass them.
    # Have already used that for testing.
    class ImmutableExtensionClass(t):
        @staticmethod
        def __new__(cls, x):
            return super(ImmutableExtensionClass, cls).__new__(cls, x)

    return ImmutableExtensionClass

Int = ImmutableExtensionFactory(int, "Int")
Str = String = ImmutableExtensionFactory(str, "Str")
Float = ImmutableExtensionFactory(float, "Float")

Anything = lambda x: x

id = lambda x: x


def Array(*f, **kwargs):
    # Cases:
        # Array(f, n=3)
        # Array(f)
        # Array(id, n=3)

        # Use initOneFunction
    # Cases:
        # Array(f1,f2,f3)
        # Redundant: Array(f1,f2,f3,n=3)
        # Bad: Array(f1,f2,f3, n = 4)

        # Use initMultipleFunctions
    class SmartArray(list):
        pass

    def initOneFunction(self, x, n=kwargs.get("n")):
        tmp = (map(f[0], x[:n]))
        list.__init__(self, tmp)

    def initMultipleFunctions(self, x):
        tmp = map(lambda ff, xx: ff(xx), f, x)
        list.__init__(self, tmp)

    if len(f) == 1:
        # setattr(SmartArray, "__init__", wrapper(initOneFunction))
        setattr(SmartArray, "__init__", (initOneFunction))
    else:
        try:
            n = kwargs.get("n")
            assert len(f) == n or n is None
            # setattr(SmartArray, "__init__", wrapper(initMultipleFunctions))
            setattr(SmartArray, "__init__", (initMultipleFunctions))

        except AssertionError:
            raise Exception("Bad definition of a fixed length array")
    return SmartArray


def Dict(*f, **kwargs):
    # Cases:
        # Dict(f) Not allowed (or syntax would be confusing)
        # Use instead Dict(Str, g)
        # Not valid JSON, but should be handled: Dict(f,g)

        # Use ConstantValueTypes

    # Cases:
        # Dict({key1 : f1, key2 : f2, ...})

        # Use VariableValueTypes

    class SmartDict(dict):
        pass

    def initConstantValueTypes(self, x):
        tmp = dict([((f[0])(k), (f[1])(v)) for (k, v) in x.items()])
        # tmp = dict([(wrapper(f[0])(k), wrapper(f[1])(v)) for (k,v) in x.items()])
        dict.__init__(self, tmp)

    def initVariableValueTypes(self, x):
        # tmp = dict([(k,wrapper(f[0][k])(v)) for (k,v) in x.items()])
        tmp = dict([(k, (f[0][k])(v)) for (k, v) in x.items()])
        dict.__init__(self, tmp)

    if len(f) == 2:
        setattr(SmartDict, "__init__", initConstantValueTypes)
    elif len(f) == 1:
        assert isinstance(f[0], dict)
        setattr(SmartDict, "__init__", initVariableValueTypes)
    else:
        raise Exception("Bad definition of a SmartDict")
    return SmartDict


def ExecDict(d):
    return d.__get_item_
