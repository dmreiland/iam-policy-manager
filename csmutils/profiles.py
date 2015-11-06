import sys
import os.path
from collections import OrderedDict
import json
import awsutils.policies as aws_policies
import awsutils.profiles as aws_profiles
import awsutils.instances as aws_instances
import utils.utils as utils
import click
import difflib
from utils.utils import Reorder



def showInstanceProfiles(ctx, targetRegion, targetEnv, targetRole, targetProfileName, targetId, show_instances):
    instanceProfiles,instanceProfileByProfileId = aws_profiles.getAllInstanceProfiles(ctx)

    if show_instances:
        instances, instancesByProfileId = aws_instances.getInstances(ctx, targetRegion, targetEnv )

    for profile in instanceProfiles:
        profileName = profile['InstanceProfileName']
        profileId = profile['InstanceProfileId']

        if targetProfileName != None and profileName != targetProfileName:
            continue
        if targetId != None and profileId != targetId:
            continue

        region, env, role = utils.regionEnvAndRole(profileName)

        if targetRegion != None and region != targetRegion:
            continue
        if targetEnv != None and env != targetEnv:
            continue
        if targetRole != None and role != targetRole:
            continue

        ctx.log('Profile Name: %s   Profile ID: %s' % (profileName, profileId))
        ctx.log('  Attached Roles:')
        for role in profile['Roles']:
            ctx.log('    %s' % (role['RoleName']))
        if not show_instances:
            continue
        if profileId in instancesByProfileId:
            ctx.log('  Attached Instances:')
            for instance in instancesByProfileId[profileId]:
                fullName = aws_instances.getTag(ctx,instance['Tags'], 'FullName')
                ctx.log('    %s' % (fullName))
        else:
            ctx.log('  No Attached Instances:')
        ctx.log('\n')

    if not show_instances:
        return
    if 'NO_INSTANCE_PROFILE' in instancesByProfileId:
        ctx.log('The following instances have no profile id')
        for instance in instancesByProfileId['NO_INSTANCE_PROFILE']:
            fullName = aws_instances.getTag(ctx,instance['Tags'], 'FullName')
            state = instance['State']['Name']
            ctx.log('    %-30s  State: %s' % (fullName, state))
    else:
        ctx.log('All instances have a profile id')

    badIds = []
    for instance in instances:
        if 'IamInstanceProfile' not in instance:
            continue
        profileId = instance['IamInstanceProfile']['Id']
        if profileId not in instanceProfileByProfileId:
            fullName = aws_instances.getTag(ctx,instance['Tags'], 'FullName')
            state = instance['State']['Name']
            badIds.append({'fullName':fullName,'state':state, 'profileId':profileId})

    if len(badIds) > 0:
        ctx.log('\nThe following instances have a bad profile id')
        for entry in badIds:
            ctx.log('    Instance: %-25s  State: %-10s  Profile ID: %s' % (entry['fullName'], entry['state'], entry['profileId']))
    else:
        ctx.log('\nAll instances have a valid profile id')
