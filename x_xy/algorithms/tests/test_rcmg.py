import jax
import jax.numpy as jnp
import numpy as np
import pytest

import x_xy
from x_xy.maths import unit_quats_like
from x_xy.maths import wrap_to_pi


@pytest.mark.parametrize("N,seed", [(1, 0), (1, 1), (5, 0), (5, 1)])
def test_batch_generator(N: int, seed: int):
    sys = x_xy.io.load_example("test_free")
    config1 = x_xy.RCMG_Config(ang0_min=0.0, ang0_max=0.0)
    config2 = x_xy.RCMG_Config()
    gen1 = x_xy.build_generator(sys, config1)
    gen2 = x_xy.build_generator(sys, config2)
    gen = x_xy.batch_generator([gen1, gen2, gen1], [N, N, N])
    q, _ = gen(jax.random.PRNGKey(seed))

    arr_eq = lambda a, b: np.testing.assert_allclose(
        q[a:b, 0, :4], unit_quats_like(q[a:b, 0, :4])
    )

    arr_eq(0, N)
    with pytest.raises(AssertionError):
        arr_eq(N, 2 * N)
    arr_eq(2 * N, 3 * N)


def test_initial_ang_pos_values():
    T = 1.0
    bs = 8
    # system consists only of prismatic, and then revolute joint
    sys = x_xy.io.load_example("test_ang0_pos0")

    def rcmg(ang0_min=0, ang0_max=0, pos0_min=0, pos0_max=0, bs=bs):
        q, _ = x_xy.batch_generator(
            x_xy.build_generator(
                sys,
                x_xy.RCMG_Config(
                    ang0_min=ang0_min,
                    ang0_max=ang0_max,
                    pos0_min=pos0_min,
                    pos0_max=pos0_max,
                    T=T,
                ),
            ),
            bs,
        )(jax.random.PRNGKey(1))
        return q

    for init_val in np.linspace(-5.0, 5.0, num=10):
        q = rcmg(init_val, init_val, init_val, init_val)
        np.testing.assert_allclose(q[:, 0, 0], init_val * jnp.ones((bs,)))
        np.testing.assert_allclose(q[:, 0, 1], wrap_to_pi(init_val * jnp.ones((bs,))))

    a, b = -0.1, 0.1
    c, d = -1.5, -0.5
    q = rcmg(a, b, c, d)[:, 0].T
    assert np.all((q[1] > a) & (q[1] < b))
    assert np.all((q[0] > c) & (q[0] < d))


def _dang_max(t: jax.Array) -> jax.Array:
    return jnp.where(t < 0.5, 1.0, 2.0)


@pytest.mark.long
def test_rcmg():
    for example in x_xy.io.list_examples():
        sys = x_xy.load_example(example)
        for cdf_bins_min, cdf_bins_max in zip([1, 1, 3], [1, 3, 3]):
            config = x_xy.RCMG_Config(
                T=1.0,
                cdf_bins_min=cdf_bins_min,
                cdf_bins_max=cdf_bins_max,
                randomized_interpolation_angle=True,
                # this tests `TimeDependentFloat`-logic
                dang_max=_dang_max,
            )
            generator = x_xy.build_generator(sys, config)
            bs = 8
            generator = x_xy.batch_generator(generator, bs)

            seed = jax.random.PRNGKey(
                1,
            )
            qs, xs = generator(seed)

            assert qs.shape == (bs, 100, sys.q_size())
