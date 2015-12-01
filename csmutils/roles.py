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
Model role us-west-2-prod-signal-transmitter
'''
def compareModelRoles(ctx, targetRegion, targetEnv, targetRole, isAudit, no_diff, diff_type, context_lines):
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
                ctx.log('Model role %-34s' % role, nl=False, bold=True)
                if not aws_roles.isRoleInAWS(ctx,role):
                    ctx.log('NOT FOUND!', fg='red')
                    continue

                ctx.log('     FOUND', bold=True)

                policies = set(ctxRoles[region][env][role])
                if isAudit:
                    for policyName in policies:
                        csm_policies.comparePolicy(ctx, policyName, no_diff, diff_type, context_lines, '    ')

                attached = set(aws_roles.getAttachedPolicies(ctx, role))
                missing = policies.difference(attached)

                if len(missing) > 0:
                    ctx.log('    -- Model policies not attached:', fg='cyan')
                    for policyName in missing:
                        ctx.log('       %s' % policyName)

                extra = attached.difference(policies)
                if len(missing) > 0:
                    ctx.log('    -- Attached policies not in model:', fg='cyan')
                    for policyName in extra:
                        ctx.log('       %s' % policyName)


def compareAWSRoles(ctx, targetRegion, targetEnv, targetRole):
    extraRoles = []
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
            extraRoles.append(roleName)
    if len(extraRoles) > 0:
        ctx.log('AWS Roles NOT in Model:', fg='cyan')
        for roleName in extraRoles:
            ctx.log('    %s' % roleName)



def compareRoles(ctx, targetRegion, targetEnv, targetRole):
    isAudit=False
    no_diff=True
    diff_type = None
    context_lines = 0

    compareModelRoles(ctx, targetRegion, targetEnv, targetRole, isAudit, no_diff, diff_type, context_lines)
    compareAWSRoles(ctx, targetRegion, targetEnv, targetRole)

def auditRoles(ctx, targetRegion, targetEnv, targetRole, no_diff, diff_type, context_lines):
    isAudit = True
    compareModelRoles(ctx, targetRegion, targetEnv, targetRole, isAudit, no_diff, diff_type, context_lines)
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
                        aws_roles.attachPolicy(ctx, role, policyName)

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
    if constrainToModel:
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
            utils.showPolicyJson(ctx, policyName, ctx.dumps(policyDoc), 15, 120)
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
