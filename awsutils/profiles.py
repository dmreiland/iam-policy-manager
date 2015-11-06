import sys
import os.path
import boto3
from botocore.exceptions import ClientError
import json
import click
from jinja2 import Template
import utils.utils as utils
from awsutils import roles as aws_roles

def getInstanceProfilesForRoleName(ctx, roleName):
    iam = ctx.iam
    instanceProfiles = []
    instanceProfileByProfileId = {}
    mps = iam.list_instance_profiles_for_role(RoleName=roleName)
    for profile in mps['InstanceProfiles']:
        instanceProfiles.append(profile)
        instanceProfileByProfileId[profile['InstanceProfileId']] = profile
    while mps['IsTruncated'] == True:
        mps = iam.list_instance_profiles_for_role(RoleName=roleName, Marker=mps['Marker'])
        for profile in mps['InstanceProfiles']:
            instanceProfiles.append(profile)
            instanceProfileByProfileId[profile['InstanceProfileId']] = profile
    return instanceProfiles, instanceProfileByProfileId

def getAllInstanceProfiles(ctx):
    iam = ctx.iam
    instanceProfiles = []
    instanceProfileByProfileId = {}
    mps = iam.list_instance_profiles()
    for profile in mps['InstanceProfiles']:
        instanceProfiles.append(profile)
        instanceProfileByProfileId[profile['InstanceProfileId']] = profile
    while mps['IsTruncated']:
        iam.list_instance_profiles( Marker=mps['Marker'])
        for profile in mps['InstanceProfiles']:
            instanceProfiles.append(profile)
            instanceProfileByProfileId[profile['InstanceProfileId']] = profile
    return instanceProfiles, instanceProfileByProfileId


def deleteInstanceProfile(ctx, profileName):
    iam = ctx.iam
    iam.delete_instance_profile(InstanceProfileName=profileName)
    ctx.audit('Deleted instance profile: %s' % profileName)


'''
Make sure you do not have any Amazon EC2 instances running with
the role you are about to remove from the instance profile.
Removing a role from an instance profile that is associated with
a running instance will break any applications running on the instance.
'''
def removeRoleFromProfile(ctx, roleName, profileName):
    iam = ctx.iam
    iam.remove_role_from_instance_profile(InstanceProfileName=profileName, RoleName=roleName)
    ctx.audit('Removed role %s from instance: %s' % (roleName, profileName))
