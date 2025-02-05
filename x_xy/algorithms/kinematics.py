from typing import Callable, Optional, Tuple

import jax
import jax.numpy as jnp
import jaxopt
from jaxopt._src.base import Solver

from x_xy import algebra

from .. import base
from .. import maths
from .. import scan
from ..scan import scan_sys
from .jcalc import jcalc_transform


def forward_kinematics_transforms(
    sys: base.System, q: jax.Array
) -> Tuple[base.Transform, base.System]:
    """Perform forward kinematics in system.

    Returns:
        - Transforms from base to links. Transforms first axis is (n_links,).
        - Updated system object with updated `transform2` and `transform` fields.
    """

    eps_to_l = {-1: base.Transform.zero()}

    def update_eps_to_l(_, __, q, link, link_idx, parent_idx, joint_type: str):
        transform2 = jcalc_transform(joint_type, q, link.joint_params)
        transform = algebra.transform_mul(transform2, link.transform1)
        link = link.replace(transform=transform, transform2=transform2)
        eps_to_l[link_idx] = algebra.transform_mul(transform, eps_to_l[parent_idx])
        return eps_to_l[link_idx], link

    eps_to_l_trafos, updated_links = scan_sys(
        sys,
        update_eps_to_l,
        "qllll",
        q,
        sys.links,
        list(range(sys.num_links())),
        sys.link_parents,
        sys.link_types,
    )
    sys = sys.replace(links=updated_links)
    return (eps_to_l_trafos, sys)


def forward_kinematics(
    sys: base.System, state: base.State
) -> Tuple[base.System, base.State]:
    """Perform forward kinematics in system.
    - Updates `transform` and `transform2` in `sys`
    - Updates `x` in `state`
    """
    x, sys = forward_kinematics_transforms(sys, state.q)
    state = state.replace(x=x)
    return sys, state


def inverse_kinematics_endeffector(
    sys: base.System,
    endeffector_link_name: str,
    endeffector_x: base.Transform,
    error_weight_rot: float = 1.0,
    error_weight_pos: float = 1.0,
    q0: Optional[jax.Array] = None,
    random_q0_starts: Optional[int] = None,
    key: Optional[jax.Array] = None,
    custom_joints: dict[str, Callable[[jax.Array], jax.Array]] = {},
    jaxopt_solver: Solver = jaxopt.LBFGS,
    **jaxopt_solver_kwargs,
) -> tuple[jax.Array, jaxopt.OptStep]:
    assert endeffector_x.ndim() == 1, "Use `vmap` for batching"

    if random_q0_starts is not None:
        assert q0 is None, "Either provide `q0` or `random_q0_starts`."
        assert key is not None, "`random_q0_starts` requires `key`"

    if q0 is None:
        if random_q0_starts is None:
            q0 = base.State.create(sys).q
        else:
            q0s = jax.random.normal(key, shape=(random_q0_starts, sys.q_size()))
            qs, results = jax.vmap(
                lambda q0: inverse_kinematics_endeffector(
                    sys,
                    endeffector_link_name,
                    endeffector_x,
                    error_weight_rot,
                    error_weight_pos,
                    q0,
                    None,
                    None,
                    jaxopt_solver,
                    **jaxopt_solver_kwargs,
                )
            )(q0s)
            # find best result
            best_q_index = jnp.argmin(results.state.value)
            best_q, best_result = jax.tree_map(
                lambda arr: jax.lax.dynamic_index_in_dim(
                    arr, best_q_index, keepdims=False
                ),
                (qs, results),
            )
            return best_q, best_result
    else:
        assert len(q0) == sys.q_size()

    def preprocess_q(q: jax.Array) -> jax.Array:
        # preprocess q
        # - normalize quaternions
        # - hinge joints in [-pi, pi]
        q_preproc = []

        def preprocess(_, __, link_type, q):
            if link_type in ["free", "cor", "spherical"]:
                new_q = q.at[:4].set(maths.safe_normalize(q[:4]))
            elif link_type in ["rx", "ry", "rz", "saddle"]:
                new_q = maths.wrap_to_pi(q)
            elif link_type in ["frozen", "p3d", "px", "py", "pz"]:
                new_q = q
            elif link_type in custom_joints:
                new_q = custom_joints[link_type](q)
            else:
                raise NotImplementedError
            q_preproc.append(new_q)

        scan.scan_sys(sys, preprocess, "lq", sys.link_types, q)
        return jnp.concatenate(q_preproc)

    def objective(q: jax.Array) -> jax.Array:
        q = preprocess_q(q)
        xhat = forward_kinematics_transforms(sys, q)[0][
            sys.name_to_idx(endeffector_link_name)
        ]
        error_rot = maths.angle_error(endeffector_x.rot, xhat.rot)
        error_pos = jnp.sqrt(jnp.sum((endeffector_x.pos - xhat.pos) ** 2))
        return error_weight_rot * error_rot + error_weight_pos * error_pos

    solver = jaxopt_solver(objective, **jaxopt_solver_kwargs)
    results = solver.run(q0)
    return preprocess_q(results.params), results
