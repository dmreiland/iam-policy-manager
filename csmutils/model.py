import sys
from collections import OrderedDict
import json
import utils.utils as utils
import click

def showModeJson(ctx):
    click.echo(json.dumps(ctx.model, indent=4))

def showModel(ctx, targetRegion, targetEnv, targetRole, targetService, targetPolicy):
    ctxRoles = ctx.model['roles']
    for region in ctxRoles:
        if targetRegion != None and region != targetRegion:
            continue
        for env in ctxRoles[region]:
            if targetEnv != None and env != targetEnv:
                continue
            for roleName in ctxRoles[region][env]:
                click.echo('Role: %s: ' % (roleName))
                for policyName in ctxRoles[region][env][roleName]:
                    if targetPolicy != None and policyName != targetPolicy:
                        continue
                    modelPolicy = json.dumps(ctx.modelPolicies[policyName])
                    utils.showPolicyJson(ctx, policyName, modelPolicy, 20, 120)


def printTemplates(ctx):
    print('\nList of Policy templates\n')
    for name, template in iter(ctx.templates.items()):
        print(name,': ', template)
