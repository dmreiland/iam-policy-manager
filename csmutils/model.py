import sys
from collections import OrderedDict
import json
import utils.utils as utils
import click

def showModeJson(ctx):
    click.echo(json.dumps(ctx.model, indent=4))

def showModel(ctx, targetRegion, targetEnv, targetRole, targetService, targetPolicy):
    for region in ctx.model:
        if targetRegion != None and region != targetRegion:
            continue
        for env in ctx.model[region]:
            if targetEnv != None and env != targetEnv:
                continue
            for role in ctx.model[region][env]:
                if targetRole != None and role != targetRole:
                    continue
                click.echo('Role: %s-%s-%s: ' % (region,env,role))
                for service in ctx.model[region][env][role]:
                    if targetService != None and service != targetService:
                        continue
                    click.echo('%10sService: %s:' % ('',service))
                    for policy in ctx.model[region][env][role][service]:
                        policyName = utils.policyNameFromModel(ctx, region, env, role, service, policy)
                        if targetPolicy != None and policyName != targetPolicy:
                            continue
                        templateName = utils.templateNameFromModel(ctx, service, policy)
                        modelPolicy = json.dumps(ctx.modelPolicies[policyName])
                        width = 120
                        total = len(modelPolicy)
                        lineLen = width - 30
                        begin = 0
                        end = lineLen
                        click.echo('%20sPolicy: %s: ' % ('',policyName))
                        while  begin < total:
                            click.echo('%30s%s'% (' ', modelPolicy[begin:end]))
                            begin += lineLen
                            end += lineLen




def printTemplates(ctx):
    print('\nList of Policy templates\n')
    for name, template in iter(ctx.templates.items()):
        print(name,': ', template)
