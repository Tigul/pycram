import pybullet as p
import itertools
import numpy as np
from .bullet_world import _world_and_id


def _get_seg_mask_for_target(cam_position, target_position):
    """
    Calculates the view and projection Matrix and returns the Segmentation mask
    The segmentation mask indicates for every pixel the visible Object.
    :param cam_position: The position of the Camera as a list of x,y,z
    :param target_position: The position to which the camera should point as a list of x,y,z
    :return: The Segmentation mask from the camera position
    """
    fov = 300
    aspect = 256 / 256
    near = 0.2
    far = 10

    view_matrix = p.computeViewMatrix(cam_position, target_position, [-1, 0, -1])
    projection_matrix = p.computeProjectionMatrixFOV(fov, aspect, near, far)
    return p.getCameraImage(256, 256, view_matrix, projection_matrix)[4]


def _get_joint_ranges(robot):
    """
    Calculates the lower and upper limits, the joint ranges and the joint damping. For a given multibody.
    The rest poses are the current poses of the joints.
    Fixed joints will be skipped because they don't have limits or ranges.
    :param robot: The robot for whom the values should be calculated
    :return: The lists for the upper and lower limits, joint ranges, rest poses and joint damping
    """
    ll, ul, jr, rp, jd = [], [], [], [], []

    for i in range(0, p.getNumJoints(robot.id)):
        info = p.getJointInfo(robot.id, i)
        if info[3] > -1:
            ll.append(info[8])
            ul.append(info[9])
            jr.append(info[9] - info[8])
            rp.append(p.getJointState(robot.id, i)[0])
            jd.append(info[6])

    return ll, ul, jr, rp, jd


def stable(object, world=None):
    """
    This predicate checks if an object is stable in the world. This will be done by simulating the world for 10 seconds
    and compare the previous coordinates with the coordinates after the simulation.
    :param object: The object which should be checked
    :param world: The BulletWorld if more than one BulletWorld is active
    :return: True if the given object is stable in the world False else
    """
    world, world_id = _world_and_id(world)
    coords_prev = p.getBasePositionAndOrientation(object.id, physicsClientId=world_id)[0]
    state = p.saveState(clientServerId=world_id)
    p.setGravity(0, 0, -9.8)

    # one Step is approximately 1/240 seconds
    for i in range(0, 10 * 240):
        p.stepSimulation(physicsClientId=world_id)
    coords_past = p.getBasePositionAndOrientation(object.id, physicsClientId=world_id)[0]

    p.restoreState(state, clientServerId=world_id)
    coords_prev = list(map(lambda n: round(n, 3), coords_prev))
    coords_past = list(map(lambda n: round(n, 3), coords_past))

    return coords_past == coords_prev


def contact(object1, object2, world=None):
    """
    This predicate checks if two objects are in contact or not.
    :param object1: The first object
    :param object2: The second object
    :param world: The BulletWorld if more than one BulletWorld is active
    :return: True if the two objects are in contact False else
    """
    world, world_id = _world_and_id(world)
    p.stepSimulation(world_id)
    con_points = p.getContactPoints(object1.id, object2.id, physicsClientId=world_id)

    return con_points is not ()


def visible(object, camera_position, world=None):
    """
    This predicate checks if an object is visible from a given position. This will be achieved by rendering the object
    alone and counting the visible pixel, then rendering the complete scene and compare the visible pixels with the
    absolut count of pixels.
    :param object: The object for which the visibility should be checked
    :param camera_position: The position of which the camera looks at the object
    :param world: The BulletWorld if more than one BulletWorld is active
    :return: True if the object is visible from the camera_position False if not
    """
    world, world_id = _world_and_id(world)
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


def occluding(object, camera_position, world=None):
    """
    This predicate lists the objects which are occluding a given object. This works similar to 'visible'.
    First the object alone will be rendered and the position of the pixels of the object in the picture will be saved.
    After that the complete scene will be rendered and the previous saved pixel positions will be compared to the
    actual pixels, if in one pixel an other object is visible ot will be saved as occluding.
    :param object: The object for which occluding should be checked
    :param camera_position: The position from which the camera looks at the object
    :param world: The BulletWorld if more than one BulletWorld is active
    :return: A list of occluding objects
    """
    world, world_id = _world_and_id(world)
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


def reachable(object, robot, gripper_name, world=None, threshold=0.01):
    """
    This predicate checks if an object is reachable for a given robot. For this purpose the inverse kinematics between
    the robot and the object will be calculated and applied. In the next step the distance between the given end_effector
    and the object will be calculated and it will be checked if it less than the threshold.
    :param object: The object for which reachability should be checked
    :param robot: The robot which should reach for the object
    :param gripper_name: The name of the end effector of the robot
    :param world: The BulletWorld if more than one BulletWorld is active
    :param threshold: The threshold between the end effector and the object. The default value is 0.01 m
    :return: True if after applying the inverse kinematics the distance between end effector and object is less than
                the threshold False if not.
    """
    world, world_id = _world_and_id(world)
    state = p.saveState()
    inv = p.calculateInverseKinematics(robot.id, robot.get_link_id(gripper_name), object.get_position(),
                                       maxNumIterations=100, physicsClientId=world_id)
    for i in range(p.getNumJoints(robot.id)):
        qIndex = p.getJointInfo(robot.id, i)[3]
        if qIndex > -1:
            p.resetJointState(robot.id, i, inv[qIndex-7])

    newp = p.getLinkState(robot.id, robot.get_link_id(gripper_name))[4]
    diff = [object.get_pose()[0] - newp[0], object.get_pose()[1] - newp[1], object.get_pose()[2] - newp[2]]
    p.restoreState(state)
    return np.sqrt(diff[0] ** 2 + diff[1] ** 2 + diff[2] ** 2) < threshold


def blocking(object, robot, gripper_name, world=None):
    """
    This predicate checks if any objects are blocking an other object when an robot tries to pick it. This works
    similar to the reachable predicate. First the inverse kinematics between the robot and the object will be calculated
    and applied. Then it will be checked if the robot is in contact with any object except the given one.
    :param object: The object for which blocking objects should be found
    :param robot: The robot who reaches for the object
    :param gripper_name: The name of the end effector of the robot
    :param world: The BulletWorld if more than one BulletWorld is active
    :return:
    """
    world, world_id = _world_and_id(world)
    state = p.saveState()
    inv = p.calculateInverseKinematics(robot.id, robot.get_link_id(gripper_name), object.get_pose(),
                                       maxNumIterations=100, physicsClientId=world_id)
    for i in range(0, p.getNumJoints(robot.id)):
        qIndex = p.getJointInfo(robot.id, i)[3]
        if qIndex > -1:
            p.resetJointState(robot.id, i, inv[qIndex-7])

    block = []
    for obj in world.objects:
        if obj == object:
            continue
        if contact(robot, obj, world):
            block.append(obj)
    p.restoreState(state)
    return block


def supporting(object1, object2, world=None):
    """
    This predicate checks if one object is supporting an other obkect. An object supports an other object if they are in
    contact and the second object is above the first one. (e.g. a Bottle will be supported by a table)
    :param object1: The first object
    :param object2: The second object
    :param world: The BulletWorld if more than one BulletWorld is active
    :return: True if the second object is in contact with the first one and the second one ist above the first False else
    """
    world, world_id = _world_and_id(world)
    return contact(object1, object2, world) and object2.getposition()[2] > object1.get_position()[2]

