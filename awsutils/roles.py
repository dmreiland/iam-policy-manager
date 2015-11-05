import sys
import os.path
import boto3
import json
import utils.utils as utils
import awsutils.policies as aws_policies


def getAllRoles(ctx):
    iam = ctx.iam
    if ctx.env == None:
        mps = iam.list_roles()
    else:
        mps = iam.list_roles(PathPrefix='/us-west-2/%s' % ctx.env)

    ctx.currentRoles.extend(mps['Roles'])
    while mps['IsTruncated']:
        mps = iam.list_roles( Marker=mps['Marker'])
        ctx.currentRoles.extend(mps['Roles'])

    for role in ctx.currentRoles:
        if role['Path'] == '/':
            try:
                region,env,roleName = utils.regionEnvAndRole(role['RoleName'])
                _,path = utils.nameAndPath(region, env, roleName)
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
        ctx.log('Attached policy %s to role %s' % (policyName, roleName))

def detachPolicy(ctx, roleName, policyName):
    iam = ctx.iam
    meta = aws_policies.getPolicyMeta(ctx, policyName)
    if meta == None:
        ctx.log('detachPolicy: Error- %s does not exist in cached AWS policies' % policyName)
        sys.exit(1)
    policyArn = meta['Arn']
    if ctx.dry_run:
        ctx.log('iam.detach_role_policy(RoleName=roleName, PolicyArn=policyArn)' % (roleName, policyArn))
    else:
        ctx.log('detachPolicy: calling detach_role_policy with %s, %s' % (roleName, policyName))
        msp = iam.detach_role_policy(RoleName=roleName, PolicyArn=policyArn)
        ctx.log('detachPolicy: detach_role_policy returned, %s' % (msp))
        ctx.audit('Detached policy %s from role %s' % (policyName, roleName) )


def detachAllPolicies(ctx, roleName):
    attached = getAttachedPolicies(ctx,roleName)
    if len(attached) > 0:
        for policyName in attached:
            detachPolicy(ctx, roleName, policyName)

def deleteRole(ctx, roleName):
    iam = ctx.iam
    try:
        iam.remove_role_from_instance_profile(InstanceProfileName=roleName, RoleName=roleName)
        ctx.audit('Removed role %s from instance: %s' % (roleName, roleName))
    except:
        pass
    try:
        iam.delete_instance_profile(InstanceProfileName=roleName)
        ctx.audit('Deleted instance profile: %s' % roleName)
    except:
        pass
    try:
        detachAllPolicies(ctx,roleName)
    except:
        pass
    try:
        iam.delete_role(RoleName=roleName)
        ctx.audit('Deleted role: %s' % roleName)
    except:
        pass

def createRole(ctx, region, env, role):
    iam = ctx.iam
    if ctx.currentRoles == None:
        ctx.vlog('createRole:  Roles must be fetched first')
        return

    roleName, path = utils.nameAndPath(region, env, role)
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

    ctx.log('Role created: %s' % msp['Role']['Arn'])
    ctx.currentRoles.append(msp['Role'])

def roleExists(ctx, roleName):
    if ctx.currentRoles == None:
        ctx.vlog('roleExists: Roles must be fetched first')
        return False
    for role in ctx.currentRoles:
        if role['RoleName'] == roleName:
            return True
    return False
