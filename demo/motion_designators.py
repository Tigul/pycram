from pycram.designator import MotionDesignator
from pycram.bullet_world import BulletWorld


def pr2_motion_designators(desig):
    solutions = []
    if desig.check_constraints([('type', 'moving'), 'target']):
        solutions.append(desig.make_dictionary([('cmd', 'navigate'), 'target']))

    if desig.check_constraints([('type', 'pick-up'), 'object', 'target']):
        if desig.check_constraints([('arm', 'right')]):
            solutions.append(desig.make_dictionary([('cmd', 'pick'), 'object', 'target', ('gripper', 'r_gripper_tool_frame')]))
        solutions.append(desig.make_dictionary([('cmd', 'pick'), 'object', 'target', ('gripper', 'l_gripper_tool_frame')]))

    if desig.check_constraints([('type', 'place'), 'target']):
        if desig.check_constraints(['object']):
            if desig.check_constraints([('arm', 'right')]):
                solutions.append(desig.make_dictionary([('cmd', 'place'), 'target', 'object', ('gripper', 'r_gripper_tool_frame')]))
            solutions.append(desig.make_dictionary([('cmd', 'place'), 'target', 'object', ('gripper', 'l_gripper_tool_frame')]))

        if desig.check_constraints([('arm', 'right')]):
            solutions.append(desig.make_dictionary([('cmd', 'place'), 'target',
                                                   ('object', list(BulletWorld.robot.attachments.keys())[0]), ('gripper', 'r_gripper_tool_frame')]))
        solutions.append(desig.make_dictionary([('cmd', 'place'), 'target',
                                               ('object', list(BulletWorld.robot.attachments.keys())[0]), ('gripper', 'l_gripper_tool_frame')]))

    if desig.check_constraints([('type', 'accessing'), 'drawer']):
        if desig.check_constraints(['distance']):
            if desig.check_constraints([('part-of', 'kitchen')]):
                solutions.append(desig.make_dictionary(('cmd', 'access'), 'drawer', 'part-of', 'distance'))
            solutions.append(desig.make_dictionary([('cmd', 'access'), 'drawer', 'distance',
                                                    ('part-of', BulletWorld.current_bullet_world.get_object_by_name("kitchen"))]))

        if desig.check_constraints([('part-of', 'kitchen')]):
            solutions.append(desig.make_dictionary([('cmd', 'access'), 'drawer', 'part-of', ('distance', 0.3)]))
        solutions.append(desig.make_dictionary([('cmd', 'access'), 'drawer', ('distance', 0.3),
                                                ('part-of', BulletWorld.current_bullet_world.get_object_by_name("kitchen"))]))

    if desig.check_constraints([('type', 'park-arms')]):
        solutions.append(desig.make_dictionary([('cmd', 'park')]))

    if desig.check_constraints([('type', 'looking')]):
        if desig.check_constraints(['target']):
            solutions.append(desig.make_dictionary([('cmd', 'looking'), 'target']))
        if desig.check_constraints(['object']):
            solutions.append(desig.make_dictionary([('cmd', 'looking'), ('target', BulletWorld.current_bullet_world.
                                                                         get_objects_by_name(desig.prop_value('object')).get_pose())]))
    #if desig.check_constraints([('type', 'move-gripper')]):
    #    solutions.append(desig.make_dictionary([('cmd', 'move-gripper'), 'right_gripper', 'left_gripper']))

    if desig.check_constraints([('type', 'opening-gripper'), 'gripper']):
        solutions.append([('cmd', 'move-gripper'), ('motion', 'open'), 'gripper'])

    if desig.check_constraints([('type', 'closing-gripper'), 'gripper']):
        solutions.append([('cmd', 'move-gripper'), ('motion', 'close'), 'gripper'])

    if desig.check_constraints([('type', 'detecting'), 'object']):
        solutions.append(desig.make_dictionary([('cmd', 'detecting'), 'object']))

    if desig.check_constraints([('type', 'move-tcp'), 'arm', 'target']):
        solutions.append(desig.make_dictionary([('cmd', 'move-tcp'), 'arm', 'target']))

    if desig.check_constraints([('type', 'move-arm-joints')]):
        if desig.check_constraints(['left-arm']):
            solutions.append(desig.make_dictionary([('cmd', 'move-joints'), ('left-poses', desig.prop_value('left-arm'))]))
        if desig.check_constraints(['right-arm']):
            solutions.append(desig.make_dictionary([('cmd', 'move-joints'), ('right-poses', desig.prop_value('right-arm'))]))



    return solutions


MotionDesignator.resolvers.append(pr2_motion_designators)
