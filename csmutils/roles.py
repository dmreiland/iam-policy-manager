import sys
import os.path
import json
import click
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


def deleteRole(ctx, role):
    aws_roles.deleteRole(ctx, role)


'''
Look to see if all the roles in the model exist, and there are no
roles that exist outside the model
'''
def compareModelRoles(ctx, targetRegion, targetEnv, targetRole):
    ctxRoles = ctx.model['roles']
    for region in ctxRoles:
        if targetRegion != None and region != targetRegion:
            continue
        for env in ctxRoles[region]:
            #defaults = None
            if targetEnv != None and env != targetEnv:
                continue
            for role in ctxRoles[region][env]:
                if targetRole != None and role != targetRole:
                    continue
                if not aws_roles.isRoleInAWS(ctx,role):
                    ctx.log(click.style('Model role not found in AWS: ' + role, fg='cyan'))
                    continue

                ctx.log('Model role found in AWS: ' + role)

                policies = set(ctxRoles[region][env][role])
                attached = set(aws_roles.getAttachedPolicies(ctx, role))

                missing = policies.difference(attached)
                policiesMatch = True
                if len(missing) > 0:
                    policiesMatch = False
                    ctx.log(click.style('-- Missiing attached policies: %s' % missing, fg='cyan'))

                extra = attached.difference(policies)
                if len(missing) > 0:
                    policiesMatch = False
                    ctx.log(click.style('-- Attached policies not in model: %s' % missing, fg='cyan'))

                if policiesMatch:
                    ctx.log('-- Attached policies conform to model')

def compareAWSRoles(ctx, targetRegion, targetEnv, targetRole):
    for role in ctx.currentRoles:
        roleName = role['RoleName']
        if targetRole != None and roleName != targetRole:
            continue
        region, env, _ = utils.regionEnvAndRole(roleName)
        if targetRegion != None and region != targetRegion:
            continue
        if targetEnv != None and env != targetEnv:
            continue
        if isRoleInModel(ctx, roleName):
            ctx.log('AWS Role: %s is in model' % roleName)
        else:
            ctx.log(click.style('AWS Role: %s is NOT in model' % roleName, fg='cyan'))



def compareRoles(ctx, targetRegion, targetEnv, targetRole):
    compareModelRoles(ctx, targetRegion, targetEnv, targetRole)
    compareAWSRoles(ctx, targetRegion, targetEnv, targetRole)


def updateModelRoles(ctx, targetRegion, targetEnv, targetRole, constrainToModel):
    ctxRoles = ctx.model['roles']
    for region in ctxRoles:
        if targetRegion != None and region != targetRegion:
            continue
        for env in ctxRoles[region]:
            #defaults = None
            if targetEnv != None and env != targetEnv:
                continue
            for role in ctxRoles[region][env]:
                if targetRole != None and role != targetRole:
                    continue
                if not aws_roles.isRoleInAWS(ctx, role):
                    ctx.vlog('Adding missing role to AWS: %s' % role)
                    aws_roles.createRole(ctx, role)
                    if ctx.dry_run:
                        # Since we are not actually creating the role in
                        # dry_run mode, we can't try to attach policies.
                        continue
                else:
                    ctx.log('Model role found in AWS: ' + role)

                policies = set(ctxRoles[region][env][role])
                attached = set(aws_roles.getAttachedPolicies(ctx, role))

                missing = policies.difference(attached)
                if len(missing) > 0:
                    for policyName in missing:
                        ctx.log('-- Attaching policy: %s' % policyName)
                        aws_roles.attachPolicy(ctx, roleName, policyName)

                if not constrainToModel:
                    continue

                # Remove attached policies that are not in the model
                extra = attached.difference(policies)
                if len(extra) > 0:
                    for policyName in extra:
                        ctx.log('-- Unattaching policy: %s' % policyName)
                        aws_roles.detachPolicy(ctx, role, policyName)

def updateAWSRoles(ctx, targetRegion, targetEnv, targetRole):
    for role in ctx.currentRoles:
        roleName = role['RoleName']
        if targetRole != None and roleName != targetRole:
            continue
        region, env, _ = utils.regionEnvAndRole(roleName)
        if targetRegion != None and region != targetRegion:
            continue
        if targetEnv != None and env != targetEnv:
            continue
        if not isRoleInModel(ctx, roleName):
            aws_roles.deleteRole(ctx,roleName)



def updateRoles(ctx, targetRegion, targetEnv, targetRole, constrainToModel):
    updateModelRoles(ctx, targetRegion, targetEnv, targetRole, constrainToModel)
    if constrainTomodel:
        updateAWSRoles(ctx, targetRegion, targetEnv, targetRole)


def showRoles(ctx, targetRegion, targetEnv, targetRole):
    for role in ctx.currentRoles:
        roleName = role['RoleName']
        if targetRole != None and roleName != targetRole:
            continue
        region, env, _ = utils.regionEnvAndRole(roleName)
        if targetRegion != None and region != targetRegion:
            continue
        if targetEnv != None and env != targetEnv:
            continue
        attached = aws_roles.getAttachedPolicies(ctx, roleName)
        ctx.log('Role: %s: %d attached policies:' % (roleName, len(attached)))
        for policyName in attached:
            policyDoc = csm_policies.getAWSPolicyDocument(ctx,policyName)
            utils.showPolicyJson(ctx, policyName, json.dumps(policyDoc), 15, 120)
        ctx.log('')

def isRoleInModel(ctx, roleName):
    try:
        region, env, _ = utils.regionEnvAndRole(roleName)
        if env not in ctx.model['roles'][region]:
            return False
        else:
            if roleName not in ctx.model['roles'][region][env]:
                return False
            else:
                return True
    except:
        return False
