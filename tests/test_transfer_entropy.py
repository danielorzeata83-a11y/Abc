"""Transfer entropy: directionalitate (cine conduce), independenta, non-negativitate."""

import numpy as np

from markov.validation.transfer_entropy import (transfer_entropy,
                                                net_transfer_entropy)


def test_te_nonnegative_and_independent_near_zero():
    rng = np.random.default_rng(0)
    x = rng.normal(size=3000)
    y = rng.normal(size=3000)                 # independent de x
    te = transfer_entropy(x, y, bins=4, lag=1)
    assert te >= 0.0
    assert te < 0.03                          # fara flux real -> ~0


def test_te_detects_driver_direction():
    """y_t+1 := x_t (+ zgomot mic): X conduce Y. TE(X->Y) >> TE(Y->X)."""
    rng = np.random.default_rng(1)
    n = 4000
    x = rng.normal(size=n)
    y = np.empty(n)
    y[0] = rng.normal()
    y[1:] = x[:-1] + 0.1 * rng.normal(size=n - 1)   # Y copiaza trecutul lui X
    fwd = transfer_entropy(x, y, bins=4, lag=1)      # X -> Y
    bwd = transfer_entropy(y, x, bins=4, lag=1)      # Y -> X
    assert fwd > bwd
    assert net_transfer_entropy(x, y, bins=4, lag=1) > 0   # x conduce


def test_te_too_short_returns_nan():
    assert np.isnan(transfer_entropy(np.arange(5.0), np.arange(5.0)))


def test_net_te_antisymmetric_sign():
    rng = np.random.default_rng(2)
    n = 4000
    a = rng.normal(size=n)
    b = np.empty(n); b[0] = 0.0
    b[1:] = a[:-1] + 0.1 * rng.normal(size=n - 1)     # a conduce b
    assert net_transfer_entropy(a, b) > 0
    assert net_transfer_entropy(b, a) < 0             # semn opus la inversare
