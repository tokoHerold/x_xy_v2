import jax
import jax.numpy as jnp

from x_xy.base import _Base
from x_xy.base import Geometry


def tree_equal(a, b):
    "Copied from Marcel / Thomas"
    if type(a) is not type(b):
        return False
    if isinstance(a, _Base):
        return tree_equal(a.__dict__, b.__dict__)
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return False
        return all(tree_equal(a[k], b[k]) for k in a.keys())
    if isinstance(a, (tuple, list)):
        if len(a) != len(b):
            return False
        return all(tree_equal(a[i], b[i]) for i in range(len(a)))
    if isinstance(a, jax.Array):
        return jnp.allclose(a, b)
    return a == b


def _sys_compare_unsafe(sys1, sys2, verbose: bool, prefix: str) -> bool:
    d1 = sys1.__dict__
    d2 = sys2.__dict__
    for key in d1:
        if isinstance(d1[key], _Base):
            if not _sys_compare_unsafe(d1[key], d2[key], verbose, prefix + "." + key):
                return False
        elif isinstance(d1[key], list) and isinstance(d1[key][0], Geometry):
            for ele1, ele2 in zip(d1[key], d2[key]):
                if not _sys_compare_unsafe(ele1, ele2, verbose, prefix + "." + key):
                    return False
        else:
            if not tree_equal(d1[key], d2[key]):
                if verbose:
                    print(f"Systems different in attribute `sys{prefix}.{key}`")
                    print(f"{repr(d1[key])} NOT EQUAL {repr(d2[key])}")
                return False
    return True


def sys_compare(sys1, sys2, verbose: bool = True):
    equalA = _sys_compare_unsafe(sys1, sys2, verbose, "")
    equalB = tree_equal(sys1, sys2)
    assert equalA == equalB
    return equalA


def to_list(obj: object) -> list:
    "obj -> [obj], if it isn't already a list."
    if not isinstance(obj, list):
        return [obj]
    return obj


def dict_union(
    d1: dict[str, dict[str, jax.Array]],
    d2: dict[str, dict[str, jax.Array]],
    overwrite: bool = False,
) -> dict:
    "Builds the union between two nested dictonaries."
    # safety copying; otherwise this function would mutate out of scope
    d1 = {key: d1[key].copy() for key in d1}

    for key2 in d2:
        if key2 not in d1:
            d1[key2] = d2[key2].copy()
        else:
            for key_nested in d2[key2]:
                if not overwrite:
                    assert (
                        key_nested not in d1[key2]
                    ), f"d1.keys()={d1[key2].keys()}; d2.keys()={d2[key2].keys()}"

            d1[key2].update(d2[key2].copy())
    return d1


def dict_to_nested(
    d: dict[str, jax.Array], add_key: str
) -> dict[str, dict[str, jax.Array]]:
    "Nests a dictonary by inserting a single key dictonary."
    return {key: {add_key: d[key]} for key in d.keys()}
