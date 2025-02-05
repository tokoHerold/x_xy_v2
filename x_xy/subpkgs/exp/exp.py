from pathlib import Path
from typing import Callable, Optional

import jax
import jax.numpy as jnp
import joblib
import tree_utils
import yaml

import x_xy
from x_xy.io import load_comments_from_xml
from x_xy.subpkgs import sys_composer

_id2xml = {"S_06": "setups/arm.xml"}


def _relative_to_this_file(path: str) -> Path:
    return Path(__file__).parent.joinpath(path)


def _read_yaml(path: str):
    with open(_relative_to_this_file(path)) as file:
        yaml_str = yaml.safe_load(file)
    return yaml_str


def _replace_rxyz_with(sys: x_xy.base.System, replace_with: str):
    return sys.replace(
        link_types=[
            replace_with if (typ in ["rx", "ry", "rz"]) else typ
            for typ in sys.link_types
        ]
    )


def _morph_new_parents_from_xml_file(file_path: str) -> dict[str, list]:
    comments = load_comments_from_xml(file_path)
    assert len(comments) == 9
    seg_new_parents_map = {}
    for comment in comments[5:]:
        segi, new_parents = comment.split(":")
        seg_new_parents_map[segi] = eval(new_parents)
    return seg_new_parents_map


def _marker_numbers_from_xml_file(file_path: str) -> dict[str, int]:
    comments = load_comments_from_xml(file_path)
    assert len(comments) == 9
    seg_marker_map = {}
    for comment in comments[:5]:
        segi, marker_eq_number = comment.split(",")
        seg_marker_map[segi] = int(marker_eq_number[-1])
        # marker numbers are 1,2,3, or 4
        assert 1 <= seg_marker_map[segi] <= 4
    return seg_marker_map


def load_sys(
    exp_id: str,
    preprocess_sys: Optional[Callable] = None,
    morph_yaml_key: Optional[str] = None,
    delete_after_morph: Optional[list[str]] = None,
    replace_rxyz: Optional[str] = None,
) -> x_xy.base.System:
    xml_path = _relative_to_this_file(_id2xml[exp_id])
    sys = x_xy.io.load_sys_from_xml(xml_path)

    if preprocess_sys is not None:
        sys = preprocess_sys(sys)

    if replace_rxyz is not None:
        sys = _replace_rxyz_with(sys, replace_rxyz)

    if morph_yaml_key is not None:
        new_parents = _morph_new_parents_from_xml_file(xml_path)[morph_yaml_key]
        sys = sys_composer.morph_system(sys, new_parents)

    if delete_after_morph is not None:
        sys = sys_composer.delete_subsystem(sys, delete_after_morph)

    return sys


def load_data(
    exp_id: str,
    motion_start: str,
    motion_stop: Optional[str] = None,
    left_padd: float = 0.0,
    right_padd: float = 0.0,
    start_for_start: bool = True,
    stop_for_stop: bool = True,
) -> dict:
    trial_data = joblib.load(_relative_to_this_file(f"joblib/{exp_id}.joblib"))

    timings = _read_yaml("timings.yaml")[exp_id]["timings"]

    if motion_stop is None:
        motion_stop = motion_start

    motions = list(timings.keys())
    assert motions.index(motion_start) <= motions.index(
        motion_stop
    ), f"starting point motion {motion_start} is after the stopping "
    "point motion {motion_stop}"

    if motion_start == motion_stop:
        assert start_for_start and stop_for_stop, "Empty sequence, stop <= start"

    t1 = timings[motion_start]["start" if start_for_start else "stop"] - left_padd
    # ensure that t1 >= 0
    t1 = max(t1, 0.0)
    t2 = timings[motion_stop]["stop" if stop_for_stop else "start"] + right_padd

    # TODO
    HZ = 100.0
    trial_data = _crop_sequence(trial_data, 1 / HZ, t1=t1, t2=t2)

    # xml_path = _relative_to_this_file(_id2xml[exp_id])
    # seg_to_marker_number = _marker_numbers_from_xml_file(xml_path)

    # TODO
    # for seg in trial_data:
    #    trial_data[seg]["pos"] = trial_data[seg][f"marker{seg_to_marker_number[seg]}"]

    return trial_data


def _crop_sequence(data: dict, dt: float, t1: float = 0.0, t2: Optional[float] = None):
    # crop time left and right
    if t2 is None:
        t2i = tree_utils.tree_shape(data)
    else:
        t2i = int(t2 / dt)
    t1i = int(t1 / dt)
    return jax.tree_map(lambda arr: jnp.array(arr)[t1i:t2i], data)
