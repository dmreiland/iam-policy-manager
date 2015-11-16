import sys
import os.path
import boto3
import json
import utils.utils as utils
import awsutils.policies as aws_policies
import awsutils.instances as aws_instances
import awsutils.profiles as aws_profiles


def getAllRoles(ctx):
    iam = ctx.iam
    if ctx.env == None:
        mps = iam.list_roles()
    else:
        mps = iam.list_roles(PathPrefix='/%s/%s' % (ctx.region, ctx.env))

    ctx.currentRoles.extend(mps['Roles'])
    while mps['IsTruncated']:
        mps = iam.list_roles( Marker=mps['Marker'])
        ctx.currentRoles.extend(mps['Roles'])

    for role in ctx.currentRoles:
        if role['Path'] == '/':
            try:
                region,env,rolePart = utils.regionEnvAndRole(role['RoleName'])
                _,path = utils.nameAndPath(region, env, rolePart)
                role['Path'] = path
            except:
                pass

def getAttachedPolicies(ctx, roleName):
    iam = ctx.iam
    attached = []
    policies = iam.list_attached_role_policies(RoleName=roleName)['AttachedPolicies']
    if len(policies) != 0:
        for policy in policies:
            attached.append(policy['PolicyName'])
    return attached

def attachPolicy(ctx, roleName, policyName):
    iam = ctx.iam
    meta = aws_policies.getPolicyMeta(ctx, policyName)
    if meta == None:
        ctx.log('attachPolicy: Error- %s does not exist in cached AWS policies' % policyName)
        sys.exit(1)
    policyArn = meta['Arn']
    if ctx.dry_run:
        ctx.log('iam.attach_role_policy(RoleName=%s, PolicyArn=%s)' % (
            roleName, policyArn))
    else:
        msp = iam.attach_role_policy(RoleName=roleName, PolicyArn=policyArn)
        ctx.audit('Attached policy %s to role %s' % (policyName, roleName))

def detachPolicy(ctx, roleName, policyName):
    iam = ctx.iam
    meta = aws_policies.getPolicyMeta(ctx, policyName)
    if meta == None:
        ctx.log('detachPolicy: Error- %s does not exist in cached AWS policies' % policyName)
        sys.exit(1)
    policyArn = meta['Arn']
    if ctx.dry_run:
        ctx.log('iam.detach_role_policy(RoleName=%s, PolicyArn=%s)' % (roleName, policyArn))
    else:
        msp = iam.detach_role_policy(RoleName=roleName, PolicyArn=policyArn)
        ctx.audit('Detached policy %s from role %s' % (policyName, roleName) )


def detachAllPolicies(ctx, roleName):
    attached = getAttachedPolicies(ctx,roleName)
    if len(attached) > 0:
        for policyName in attached:
            detachPolicy(ctx, roleName, policyName)

def deleteRole(ctx, roleName):
    iam = ctx.iam
    # First, find out if there are any active instances using the role.  If so,
    # then deleting it will likely break the running instance.
    instanceProfiles,_ = aws_profiles.getInstanceProfilesForRoleName(ctx, roleName)
    inUses = []
    for instanceProfile in instanceProfiles:
        instanceProfileId = instanceProfile['InstanceProfileId']
        instances, instancesByProfileId = aws_instances.getInstancesByIAMInstanceProfileId(ctx, instanceProfile['Arn'])
        for instance in instances:

                        fullName = aws_instances.getTag(ctx, instance['Tags'], 'FullName')
                        state = instance['State']['Name']
                        if state != 'terminated':
                            inUses.append({'fullName':fullName,'state':state, 'profileId':instanceProfileId})
    if len(inUses) > 0:
        ctx.log('Error:  Cannot delete role %s.  The following active instances are attached: ' % (roleName))
        for entry in inUses:
            ctx.log('    Instance: %-25s  State: %-10s  Profile ID: %s' % (entry['fullName'], entry['state'], entry['profileId']))
        ctx.log('These instance must be terminated before the role can be deleted')
        return

    for instanceProfile in instanceProfiles:
        instanceProfileName = instanceProfile['InstanceProfileName']
        aws_profiles.removeRoleFromProfile(ctx, roleName, instanceProfileName)
        aws_profiles.deleteInstanceProfile(ctx, instanceProfileName)

    detachAllPolicies(ctx,roleName)
    if ctx.dry_run:
        ctx.log('iam.delete_role(RoleName=roleName)' % (roleName))
    else:
        iam.delete_role(RoleName=roleName)
        ctx.audit('Deleted role: %s' % roleName)

def createRole(ctx, roleName):
    iam = ctx.iam
    if ctx.currentRoles == None:
        ctx.vlog('createRole:  Roles must be fetched first')
        return

    assumeRolePolicyDocument = '{"Statement": [{"Action": "sts:AssumeRole", "Principal": {"Service": "ec2.amazonaws.com"}, "Sid": "", "Effect": "Allow"}], "Version": "2012-10-17"}'
    if ctx.dry_run:
        ctx.log('create_role(Path=%s, RoleName=%s,AssumeRolePolicyDocument=%s)' % (path, roleName, assumeRolePolicyDocument))
        return
    # Create roles

    # Attach role to instance profile
    msp = iam.create_role(Path=path, RoleName=roleName, AssumeRolePolicyDocument=assumeRolePolicyDocument)
    if msp['ResponseMetadata']['HTTPStatusCode'] != 200:
        ctx.log('createRole Error: create_role returned %d' % msp['ResponseMetadata']['HTTPStatusCode'])
        return
    ctx.audit('Created role: %s' % roleName)

    msp2 = iam.create_instance_profile(InstanceProfileName=roleName)
    if msp2['ResponseMetadata']['HTTPStatusCode'] != 200:
        ctx.log('createRole Error: create_role returned %d' % msp2['ResponseMetadata']['HTTPStatusCode'])
        return
    ctx.audit('Created instance profile: %s' % roleName)

    msp3 = iam.add_role_to_instance_profile(InstanceProfileName=roleName, RoleName=roleName)
    if msp3['ResponseMetadata']['HTTPStatusCode'] != 200:
        ctx.log('createRole Error: create_role returned %d' % msp3['ResponseMetadata']['HTTPStatusCode'])
        return
    ctx.audit('Attached role %s to instance profile: %s' % (roleName, roleName))

    ctx.vlog('Role created: %s' % msp['Role']['Arn'])
    ctx.currentRoles.append(msp['Role'])

def isRoleInAWS(ctx, roleName):
    if ctx.currentRoles == None:
        ctx.log('isRoleInAWS: Roles must be fetched first')
        return False
    for role in ctx.currentRoles:
        if role['RoleName'] == roleName:
            return True
    return False
