import sys
import os.path
import json
import awsutils.roles as aws_roles
import awsutils.policies as aws_policies
import csmutils.policies as csm_policies
import utils.utils as utils

'''
The envs.json data contains the following:
[
    "<env>": {
        "<role_1>": [
            {
                "<service_1>": ["policy_1","policy_2"]
            }
        ]
    }
]

The dev, test, qa, and prod roles are defined in the file default_roles.json.
All other envs have their roles defined directly in the envs.json file.

'''
def getAWSRoles(ctx):
    aws_roles.getAllRoles(ctx)




def getModelRolePolicies(ctx, region, env, role, roleName):
    policies = []
    for service in ctx.model[region][env][role]:
        for policy in ctx.model[region][env][role][service]:
            policyName = utils.policyNameFromModel(ctx, region, env, role, service, policy)
            policies.append(policyName)
    return policies

'''
Look to see if all the roles in the model exist, and there are no
roles that exist outside the model
'''
def compareModelRoles(ctx, targetRegion, targetEnv, targetRole, targetRoleName, compareOnly, constrainToModel):

    for region in ctx.model:
        if targetRegion != None and region != targetRegion:
            continue
        for env in ctx.model[region]:
            defaults = None
            if targetEnv != None and env != targetEnv:
                continue
            for role in ctx.model[region][env]:
                if targetRole != None and role != targetRole:
                    continue
                if role == '*':
                    continue
                roleName,_ = utils.nameAndPath(region, env, role)
                if targetRoleName != None and roleName != targetRoleName:
                    continue
                if not aws_roles.roleExists(ctx,roleName):
                    if compareOnly:
                        ctx.log('Model role not found in AWS: ' + roleName)
                        continue
                    ctx.vlog('Adding missing role to AWS: %s' % roleName)
                    aws_roles.createRole(ctx, region, env, role)
                    if ctx.dry_run:
                        continue
                else:
                    ctx.log('Model role found in AWS: ' + roleName)

                policies = getModelRolePolicies(ctx, ctx.region, env, role, roleName)
                if '*' in ctx.model[region][env]:
                    defaults = getModelRolePolicies(ctx, ctx.region, env, '*', roleName)
                    policies.extend(defaults)
                ctx.vlog('--- model policies: %s' % policies)
                attached = aws_roles.getAttachedPolicies(ctx, roleName)
                ctx.vlog('--- attached policies: %s' % attached)
                missing = []
                policiesMatch = True
                for p in policies:
                    if p not in attached:
                        missing.append(p)
                        policiesMatch = False
                if len(missing) > 0:
                    if compareOnly:
                        ctx.log('-- Missiing attached policies: %s' % missing)
                    else:
                        for policyName in missing:
                            ctx.log('-- Attaching policy: %s' % policyName)
                            aws_roles.attachPolicy(ctx, roleName, policyName)

                missing = []
                for p in attached:
                    if p not in policies:
                        missing.append(p)
                        policiesMatch = False
                if len(missing) > 0:
                    if compareOnly:
                        ctx.log('-- Attached policies not in model: %s' % missing)
                    else:
                        if constrainToModel:
                            for policyName in missing:
                                ctx.log('-- Unattaching policy: %s' % policyName)
                                aws_roles.detachPolicy(ctx, roleName, policyName)

                if not policiesMatch and not compareOnly:
                    ctx.vlog('-- Attached policies do not match model')

def compareAWSRoles(ctx, targetRegion, targetEnv, targetRole, targetRoleName, compareOnly, constrainToModel):
    for role in ctx.currentRoles:
        roleName = role['RoleName']
        if targetRoleName != None and roleName != targetRoleName:
            continue
        region, env, role = utils.regionEnvAndRole(roleName)
        if targetRegion != None and region != targetRegion:
            continue
        if targetEnv != None and env != targetEnv:
            continue
        if targetRole != None and role != targetRole:
            continue
        if roleExists(ctx, roleName):
            ctx.log('AWS Role: %s is in model' % roleName)
        else:
            ctx.log('AWS Role: %s is NOT in model' % roleName)



def compareRoles(ctx, targetRegion, targetEnv, targetRole, targetRoleName, compareOnly, constrainToModel):
    compareModelRoles(ctx, targetRegion, targetEnv, targetRole, targetRoleName, compareOnly, constrainToModel)
    compareAWSRoles(ctx, targetRegion, targetEnv, targetRole, targetRoleName, compareOnly, constrainToModel)



def showAwsRoles(ctx, targetRegion, targetEnv, targetRole, targetRoleName):
    for role in ctx.currentRoles:
        roleName = role['RoleName']
        if targetRoleName != None and roleName != targetRoleName:
            continue
        region, env, role = utils.regionEnvAndRole(roleName)
        if targetRegion != None and region != targetRegion:
            continue
        if targetEnv != None and env != targetEnv:
            continue
        if targetRole != None and role != targetRole:
            continue
        attached = aws_roles.getAttachedPolicies(ctx, roleName)
        ctx.log('Role: %s: %d attached policies:' % (roleName, len(attached)))
        for policyName in attached:
            policyDoc = csm_policies.getAWSPolicyDocument(ctx,policyName)
            ctx.log('   %s:  %s'% (policyName, json.dumps(policyDoc)))


def roleExists(ctx, name):
    try:
        region, env, role = utils.regionEnvAndRole(name)
        if env not in ctx.model[region]:
            return False
        else:
            if role not in ctx.model[region][env]:
                return false
            else:
                return True
    except:
        return False
