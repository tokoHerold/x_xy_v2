import jax
import jax.numpy as jnp

import x_xy
from x_xy import maths
from x_xy.algorithms.jcalc import _draw_rxyz


def register_rr_joint():
    x_xy.update_n_joint_params(3)

    def _rr_transform(q, params):
        def _rxyz_transform(q, _, axis):
            q = jnp.squeeze(q)
            rot = maths.quat_rot_axis(axis, q)
            return x_xy.Transform.create(rot=rot)

        return _rxyz_transform(q, None, params)

    rr_joint = x_xy.JointModel(_rr_transform, rcmg_draw_fn=_draw_rxyz)
    try:
        x_xy.register_new_joint_type("rr", rr_joint, 1, 0)
    except AssertionError:
        pass


def setup_fn_randomize_joint_axes(key, sys: x_xy.System) -> x_xy.System:
    joint_axes = _draw_random_joint_axis(jax.random.split(key, sys.num_links()))
    return sys.replace(links=sys.links.replace(joint_params=joint_axes))


@jax.vmap
def _draw_random_joint_axis(key):
    return maths.rotate(jnp.array([1.0, 0, 0]), maths.quat_random(key))
