#cython: embedsignature=True
#cython: language_level=3

import numpy
cimport numpy as np
import cython

cdef extern from "numpy/npy_math.h":
    bint npy_isnan(double x)

@cython.wraparound(False)
def contingency_floatarray(np.ndarray[np.float64_t, ndim=1] col_data, np.ndarray[np.float64_t, ndim=1] classes, np.intp_t n_rows, np.ndarray[np.float64_t, ndim=1] W = None):
    """
    Given column values and class values, return
    - an array with the sorted list of values,
    - a 2D array with counts for the value (indexed by columns)
      and class value (indexed by rows),
    - array with the number of missing values for each class.
    - array with the number of missing class values for each column value.
    - and the number of missing in class and column values at same time.
    """
    cdef np.ndarray[np.intp_t, ndim=1] ranks = col_data.argsort()
    cdef int N = 0
    cdef np.float64_t v
    cdef np.float64_t last = float("NaN")
    cdef Py_ssize_t i,j
    cdef int weights = not W is None
    for i in range(ranks.shape[0]):
        i = ranks[i]
        v = col_data[i]
        if v != last and not npy_isnan(v):
            N += 1
            last = v
    cdef np.ndarray[np.float64_t, ndim=1] V = numpy.zeros(N, dtype=numpy.float64)
    cdef np.ndarray[np.float64_t, ndim=2] C = numpy.zeros((n_rows, N), dtype=numpy.float64)
    last = float("NaN")
    j = -1
    cdef np.float64_t tc
    cdef np.ndarray[np.float64_t, ndim=1] col_unknowns = numpy.zeros(n_rows, dtype=numpy.float64)
    cdef np.ndarray[np.float64_t, ndim=1] row_unknowns = numpy.zeros(N, dtype=numpy.float64)
    cdef np.float64_t unknowns = 0
    for i in range(ranks.shape[0]):
        i = ranks[i]
        v = col_data[i]
        tc = classes[i]
        if v != last and not npy_isnan(v):
            j += 1
            V[j] = v
            last = v
        if npy_isnan(v) and npy_isnan(tc):
            unknowns += W[i] if weights else 1.
        elif npy_isnan(tc):
            row_unknowns[j] += W[i] if weights else 1.
        elif npy_isnan(v):
            col_unknowns[int(tc)] += W[i] if weights else 1.
        else:
            C[int(tc),j] += W[i] if weights else 1.

    assert j == N-1

    return (V,C),col_unknowns,row_unknowns,unknowns
