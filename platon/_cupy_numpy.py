FORCE_CPU = False  # force to use CPU if this is True

if FORCE_CPU:
    from numpy import *
    import scipy
    import scipy.special
    from scipy import interpolate, ndimage
else:
    try:
        from cupy import *
        from cupyx import scipy
        from cupyx.scipy import interpolate, ndimage
    except:
        from numpy import *
        import scipy
        import scipy.special
        from scipy import interpolate, ndimage

def cpu(arr):
    try:
        return arr.get()
    except:
        return arr
