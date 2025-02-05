from typing import Optional, Sequence

import mujoco

from .. import maths
from ..base import Box
from ..base import Capsule
from ..base import Cylinder
from ..base import Geometry
from ..base import Sphere
from ..base import Transform


def _build_model_of_geoms(
    geoms: list[Geometry],
    cameras: dict[int, Sequence[str]],
    lights: dict[int, Sequence[str]],
    debug: bool,
) -> mujoco.MjModel:
    # sort in ascending order, this shouldn't be required as it is already done by
    # parse_system; do it for good measure anyways
    geoms = geoms.copy()
    geoms.sort(key=lambda ele: ele.link_idx)

    # range of required link_indices to which geoms attach
    unique_parents = set([geom.link_idx for geom in geoms])

    # throw error if you attached a camera or light to a body that has no geoms
    inside_worldbody_cameras = ""
    for camera_parent in cameras:
        if -1 not in unique_parents:
            if camera_parent == -1:
                for camera_str in cameras[camera_parent]:
                    inside_worldbody_cameras += camera_str
                continue

        assert (
            camera_parent in unique_parents
        ), f"Camera parent {camera_parent} not in {unique_parents}"

    inside_worldbody_lights = ""
    for light_parent in lights:
        if -1 not in unique_parents:
            if light_parent == -1:
                for light_str in lights[light_parent]:
                    inside_worldbody_lights += light_str
                continue

        assert (
            light_parent in unique_parents
        ), f"Light parent {light_parent} not in {unique_parents}"

    # group together all geoms in each link
    grouped_geoms = dict(
        zip(unique_parents, [list() for _ in range(len(unique_parents))])
    )
    parent = -1
    for geom in geoms:
        while geom.link_idx != parent:
            parent += 1
        grouped_geoms[parent].append(geom)

    inside_worldbody = ""
    for parent, geoms in grouped_geoms.items():
        find = lambda dic: dic[parent] if parent in dic else []
        inside_worldbody += _xml_str_one_body(
            parent, geoms, find(cameras), find(lights)
        )

    parents_noworld = unique_parents - set([-1])
    targetbody = min(parents_noworld) if len(parents_noworld) > 0 else -1
    xml_str = f""" # noqa: E501
<mujoco>
  <asset>
    <texture name="texplane" type="2d" builtin="checker" rgb1=".25 .25 .25" rgb2=".3 .3 .3" width="512" height="512" mark="cross" markrgb=".8 .8 .8"/>
    <material name="matplane" reflectance="0.3" texture="texplane" texrepeat="1 1" texuniform="true"/>
    <texture name="skybox" type="skybox" builtin="gradient" rgb1=".4 .6 .8" rgb2="0 0 0" width="800" height="800" mark="random" markrgb="1 1 1"/>
    <texture name="grid" type="2d" builtin="checker" rgb1=".1 .2 .3" rgb2=".2 .3 .4" width="300" height="300" mark="edge" markrgb=".2 .3 .4"/>
    <material name="grid" texture="grid" texrepeat="1 1" texuniform="true" reflectance=".2"/>
  </asset>

  <visual>
    <headlight ambient=".4 .4 .4" diffuse=".8 .8 .8" specular="0.1 0.1 0.1"/>
    <map znear=".01"/>
    <quality shadowsize="2048"/>
    <global offwidth="1920" offheight="1080"/>
  </visual>

<worldbody>
<camera pos="0 -1 1" name="trackcom" mode="trackcom"/>
<camera pos="0 -1 1" name="target" mode="targetbodycom" target="{targetbody}"/>
<camera pos="0 -3 3" name="targetfar" mode="targetbodycom" target="{targetbody}"/>
<camera pos="0 -5 5" name="targetFar" mode="targetbodycom" target="{targetbody}"/>
<light pos="0 0 10" dir="0 0 -1"/>
<geom name="floor" pos="0 0 -0.5" size="0 0 1" type="plane" material="matplane" mass="0"/>
<geom name="earthframe_x" pos="0.2 0.05 0.05" size="0.2 0.05 0.05" type="box" rgba=".8 .2 .2 1" mass="0"/>
<geom name="earthframe_y" pos="0.05 0.2 0.05" size="0.05 0.2 0.05" type="box" rgba=".2 .8 .2 1" mass="0"/>
<geom name="earthframe_z" pos="0.05 0.05 0.2" size="0.05 0.05 .2" type="box" rgba=".2 .2 .8 1" mass="0"/>
{inside_worldbody_cameras}
{inside_worldbody_lights}
{inside_worldbody}
</worldbody>
</mujoco>
"""
    if debug:
        print("Mujoco xml string: ", xml_str)

    return mujoco.MjModel.from_xml_string(xml_str)


def _xml_str_one_body(
    body_number: int, geoms: list[Geometry], cameras: list[str], lights: list[str]
) -> str:
    inside_body_geoms = ""
    for geom in geoms:
        inside_body_geoms += _xml_str_one_geom(geom)

    inside_body_cameras = ""
    for camera in cameras:
        inside_body_cameras += camera  # + "\n"

    inside_body_lights = ""
    for light in lights:
        inside_body_lights += light  # + "\n"

    return f"""
<body name="{body_number}" mocap="true">
{inside_body_cameras}
{inside_body_lights}
{inside_body_geoms}
</body>
"""


def _xml_str_one_geom(geom: Geometry) -> str:
    rgba = f'rgba="{_array_to_str(geom.color)}"'

    if isinstance(geom, Box):
        type_size = f'type="box" size="{_array_to_str([geom.dim_x / 2, geom.dim_y / 2, geom.dim_z / 2])}"'  # noqa: E501
    elif isinstance(geom, Sphere):
        type_size = f'type="sphere" size="{_array_to_str([geom.radius])}"'
    elif isinstance(geom, Capsule):
        type_size = (
            f'type="capsule" size="{_array_to_str([geom.radius, geom.length / 2])}"'
        )
    elif isinstance(geom, Cylinder):
        type_size = (
            f'type="cylinder" size="{_array_to_str([geom.radius, geom.length / 2])}"'
        )
    else:
        raise NotImplementedError

    rot, pos = maths.quat_inv(geom.transform.rot), geom.transform.pos
    rot, pos = f'pos="{_array_to_str(pos)}"', f'quat="{_array_to_str(rot)}"'
    return f"<geom {type_size} {rgba} {rot} {pos}/>"


def _array_to_str(arr: Sequence[float]) -> str:
    # TODO; remove round & truncation
    return "".join(["{:.4f} ".format(round(value, 4)) for value in arr])[:-1]


class MujocoScene:
    def __init__(
        self,
        height: int = 240,
        width: int = 320,
        add_cameras: dict[int, str | Sequence[str]] = {},
        add_lights: dict[int, str | Sequence[str]] = {},
        debug: bool = False,
    ) -> None:
        self.debug = debug
        self.height, self.width = height, width

        def to_list(dic: dict):
            for k, v in dic.items():
                if isinstance(v, str):
                    dic[k] = [v]
            return dic

        self.add_cameras, self.add_lights = to_list(add_cameras), to_list(add_lights)

    def init(self, geoms: list[Geometry]):
        self._parent_ids = list(set([geom.link_idx for geom in geoms]))
        self._model = _build_model_of_geoms(
            geoms, self.add_cameras, self.add_lights, debug=self.debug
        )
        self._data = mujoco.MjData(self._model)
        self._renderer = mujoco.Renderer(self._model, self.height, self.width)

    def update(self, x: Transform):
        rot, pos = maths.quat_inv(x.rot), x.pos
        for parent_id in self._parent_ids:
            if parent_id == -1:
                continue

            # body name is just the str(parent_id)
            mocap_id = int(self._model.body(str(parent_id)).mocapid)

            if self.debug:
                print(f"link_idx: {parent_id}, mocap_id: {mocap_id}")

            mocap_pos = pos[parent_id]
            mocap_quat = rot[parent_id]
            self._data.mocap_pos[mocap_id] = mocap_pos
            self._data.mocap_quat[mocap_id] = mocap_quat

        if self.debug:
            print("mocap_pos: ", self._data.mocap_pos)
            print("mocap_quat: ", self._data.mocap_quat)

        mujoco.mj_forward(self._model, self._data)

    def render(self, camera: Optional[str] = None):
        self._renderer.update_scene(self._data, camera=-1 if camera is None else camera)
        return self._renderer.render()
