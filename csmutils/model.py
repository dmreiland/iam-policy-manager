import sys
from collections import OrderedDict
import json
import utils.utils as utils
import click

def showModeJson(ctx):
    click.echo(ctx.dumps(ctx.model, indent=4))

def showModel(ctx, targetRegion, targetEnv, targetRole, targetService, targetPolicy):
    ctxRoles = ctx.model['roles']
    offset = 0
    width = 120
    for region in ctxRoles:
        if targetRegion != None and region != targetRegion:
            continue
        for env in ctxRoles[region]:
            if targetEnv != None and env != targetEnv:
                continue
            for roleName in ctxRoles[region][env]:
                if (targetPolicy == None and targetService == None) and targetRole == None:
                    ctx.log(click.style('Role: %s: ' % (roleName), fg='cyan'))
                    offset = 10
                else:
                    offset = 0
                for policyName in ctxRoles[region][env][roleName]:
                    if targetPolicy != None and policyName != targetPolicy:
                        continue
                    modelPolicy = ctx.dumps(ctx.modelPolicies[policyName])
                    if modelPolicy != None:
                        if targetPolicy == None:
                            # Don't display the policy name if only 1 policy is
                            # being shown.
                            ctx.log(click.style('%*sPolicy: %s: ' % (offset,'',policyName), fg='cyan'))
                        utils.showPolicyJson(ctx, modelPolicy, offset, width)
                        #ctx.log(click.wrap_text(modelPolicy, width, '%*s'%(offset,''),'%*s'%(offset,''), True))


def printTemplates(ctx):
    print('\nList of Policy templates\n')
    for name, template in iter(ctx.templates.items()):
        print(name,': ', template)
