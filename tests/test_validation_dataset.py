import numpy as np
from markov.validation import dataset


def test_forward_returns_horizons_and_tail_nan():
    close = np.array([100.0, 110, 121, 133.1])
    out = dataset.forward_returns(close, horizons=(1, 2))
    assert np.isclose(out[1][0], 0.10)
    assert np.isnan(out[1][-1])
    assert np.isclose(out[2][0], 0.21)
    assert np.isnan(out[2][-1]) and np.isnan(out[2][-2])
