import  pybullet as p
import itertools
from pycram.helper import _client_id

def _get_seg_mask_for_target(cam_position, target_position):
    fov = 300
    aspect = 256 / 256
    near = 0.2
    far = 10

    view_matrix = p.computeViewMatrix(cam_position, target_position, [-1, 0, -1])
    projection_matrix = p.computeProjectionMatrixFOV(fov, aspect, near, far)
    return p.getCameraImage(256, 256, view_matrix, projection_matrix)[4]


def stable(object, world):
    world_id = _client_id(world)
    object = object.id
    coords_prev = p.getBasePositionAndOrientation(object, physicsClientId=world_id)[0]
    state = p.saveState(clientServerId=world_id)
    p.setGravity(0, 0, -9.8)

    # one Step is approximately 1/240 seconds
    for i in range(0, 10 * 240):
        p.stepSimulation(physicsClientId=world_id)
    coords_past = p.getBasePositionAndOrientation(object, physicsClientId=world_id)[0]

    p.restoreState(state, clientServerId=world_id)
    coords_prev = list(map(lambda n: round(n, 3), coords_prev))
    coords_past = list(map(lambda n: round(n, 3), coords_past))
    return coords_past == coords_prev


def contact(object1, object2, world):
    world_id = _client_id(world)
    con_points = p.getContactPoints(object1.id, object2.id, physicsClientId=world_id)
    return con_points is not ()


def visible(object, camera_position,  world):
    world_id = _client_id(world)
    state = p.saveState()
    for obj in world.objects:
        if obj.id is not object.id:
            # p.removeBody(object.id, physicsClientId=world_id)
            # Hot fix until I come up with something better
            p.resetBasePositionAndOrientation(obj.id, [100, 100, 100], [0, 0, 0, 1], world_id)

    seg_mask = _get_seg_mask_for_target(camera_position, object.get_position())
    flat_list = list(itertools.chain.from_iterable(seg_mask))
    max_pixel = sum(list(map(lambda x: 1 if x == object.id else 0, flat_list)))
    p.restoreState(state)

    seg_mask = _get_seg_mask_for_target(camera_position, object.get_position())
    flat_list = list(itertools.chain.from_iterable(seg_mask))
    real_pixel = sum(list(map(lambda x: 1 if x == object.id else 0, flat_list)))

    return real_pixel >= max_pixel > 0


def occluding(object, camera_position, world):
    world_id = _client_id(world)
    state = p.saveState()
    for obj in world.objects:
        if obj.id is not object.id:
            # p.removeBody(object.id, physicsClientId=world_id)
            # Hot fix until I come up with something better
            p.resetBasePositionAndOrientation(obj.id, [100, 100, 100], [0, 0, 0, 1], world_id)

    seg_mask = _get_seg_mask_for_target(camera_position, object.get_position())
    pixels = []
    for i in range(0, 256):
        for j in range(0, 256):
            if seg_mask[i][j] == object.id:
                pixels.append((i, j))
    p.restoreState(state)

    occluding = []
    seg_mask = _get_seg_mask_for_target(camera_position, object.get_position())
    for c in pixels:
        if not seg_mask[c[0]][c[1]] == object.id:
            occluding.append(seg_mask[c[0]][c[1]])

    return list(set(map(lambda x: world.get_object_by_id(x), occluding)))


def reachable(object, robot, gripper_name, world):
    world_id = _client_id(world)
    inv = p.calculateInverseKinematics(robot.id, robot.get_link_id(gripper_name), object.get_position(), physicsClientId=world_id)
    return inv is not ()


def blocking(object, robot, gripper_name, world):
    world_id = _client_id(world)

    return None


def supporting(object1, object2, world):
    return contact(object1, object2, world) and object2.getposition()[2] > object1.get_position()[2]
