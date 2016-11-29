# Copyright (c) 2016, Vladimir Feinberg
# Licensed under the BSD 3-clause license (see LICENSE)

import sys
import math

import contexttimer
import numpy as np
import scipy.linalg
import scipy.sparse.linalg

from runlmc.linalg.toeplitz import Toeplitz
from runlmc.linalg.kronecker import Kronecker

def random_toep(n):
    top = np.abs(np.random.rand(n))
    top[::-1].sort()
    top[0] += 1
    return top

def poor_cond_toep(n):
    up = np.arange(n // 8) + 1
    down = np.copy(up[::-1])
    up = up / 2
    top = np.zeros(n)
    updown = np.add.accumulate(np.hstack([up, down]))[::-1]
    top[:len(updown)] = updown
    return top

def rand_psd(n):
    A = np.random.rand(n, n)
    A = (A + A.T).astype(np.float64) / 2
    A += np.diag(np.fabs(A).sum(axis=1) + 1)
    return A

def stress_kronecker_solve(top, d):
    n = len(top)
    b = np.random.rand(n * d)
    toep = scipy.linalg.toeplitz(top)
    dense = rand_psd(d)

    assert np.linalg.matrix_rank(dense) == d
    assert np.linalg.matrix_rank(toep) == n

    A = Kronecker(dense, Toeplitz(top)).as_linear_operator()
    M = np.kron(dense, toep)
    assert np.linalg.matrix_rank(M) == n * d

    tol = 1e-6
    cond = np.linalg.cond(M)
    print('    size {}x{} tol {:g} cond {}'
          .format(n, d, tol, cond))

    def time_method(f):
        with contexttimer.Timer() as solve_time:
            solve, name = f()
        print('    {} sec {:8.4f} resid {:8.4e}'.format(
            name.rjust(20),
            solve_time.elapsed,
            np.linalg.norm(A.matvec(solve) - b)))
    time_method(lambda: (np.linalg.solve(M, b), 'linear solve'))

    def sparse():
        out, succ = scipy.sparse.linalg.cg(A, b, tol=tol, maxiter=(n*d))
        return out, '{} sparse CG'.format('' if not succ else '*')
    time_method(sparse)


    def minres():
        out, succ = scipy.sparse.linalg.minres(A, b, tol=tol, maxiter=(n*d))
        return out, '{} sparse MINRES'.format('' if not succ else '*')
    time_method(minres)

if __name__ == "__main__":
    if len(sys.argv) not in [3, 4]:
        print('Usage: python kronecker_cg.py n d [seed]')
        print()
        print('n > 8 is the size of the Toeplitz submatrix')
        print('d > 0 is the size of the dense submatrix')
        print('default seed is 1234')
        print('this solves the kronecker product system size n * d')
        print('choose d == 1 and n large to test Toeplitz CG mainly')
        sys.exit(1)

    n = int(sys.argv[1])
    d = int(sys.argv[2])
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1234

    assert n > 8
    assert d > 0

    np.random.seed(seed)

    print('* = no convergence')

    print('random (well-cond) ')
    stress_kronecker_solve(random_toep(n), d)

    # Poorly-conditioned
    print('linear decrease (poor-cond)')
    stress_kronecker_solve(poor_cond_toep(n), d)

    print('exponentially decreasing (realistic)')
    stress_kronecker_solve(np.exp(-np.arange(n)), d)
