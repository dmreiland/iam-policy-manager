import os
import json
import sys
from collections import OrderedDict
from jinja2 import Template

def nameAndPath(region, env, roleName):
    name = '%s-%s-%s' % (region, env, roleName)
    path = '/%s/%s/%s/' % (region, env, roleName)
    return name, path

def regionEnvAndRole(name):
    parts = name.split('-')
    # 0 - 'us', 1 -' west', 2 - '2', 3 - '<env>', 4 - '<role>'
    if len(parts) < 3:
        return None, None, name
    region = '%s-%s-%s'%(parts[0],parts[1],parts[2])
    env = parts[3]
    if len(parts) > 5:
        role = parts[4]
        i = 5
        while i < len(parts):
            role += '-' + parts[i]
            i += 1
    else:
        role = parts[4]
    return region, env, role

def policyNameFromArn(ctx, policyArn):
    #arn:aws:iam::716927822216:policy/us-west-2-dev-default
    parts = policyArn.split('/')
    if len(parts) == 1:
        return policyArn
    else:
        ctx.vlog('policyNameFromArn: %s -> %s' % (policyArn, parts[-1]))
        return parts[-1]

def renderPolicy(ctx, templateName, options):
    jt = Template(ctx.templates[templateName])
    doc = jt.render(options)
    return json.loads(doc, object_pairs_hook=OrderedDict)

def policyNameFromModel(ctx, region, env, role, service, policy):
    if policy == 'service' or policy == service:
        policyName='%s-%s-%s' % (region, env, service)
    else:
        policyName='%s-%s-%s-%s' % (region, env, service, policy)
    return policyName

def templateNameFromModel(ctx, service, policy):
    if service == 'default':
        templateName= "%s.%s" % (service, policy)
    else:
        templateName= "%s" % (policy)
    return templateName


def loadModel(ctx):
    ctx.vlog('loadModel: Start')
    with open('json/'+ctx.defaultRolesFile) as data_file:
        defaultRoles = json.load(data_file)
    with open('json/'+ctx.modelFile) as data_file:
        model = json.load(data_file)
    for region in model:
        model[region]['dev'] = defaultRoles
        model[region]['test'] = defaultRoles
        model[region]['qa'] = defaultRoles
        model[region]['prod'] = defaultRoles
    ctx.vlog('loadModel: Done')
    return model


def loadModelPolicies(ctx):
    ctx.vlog('loadModelPolicies: Start')
    if ctx.templates == None:
        ctx.log("Cannot load model policies until templates are loaded")
        sys.exit(1)
    modelPolicies = {}
    for region in ctx.model:
        for env in ctx.model[region]:
            for role in ctx.model[region][env]:
                for service in ctx.model[region][env][role]:
                    for policy in ctx.model[region][env][role][service]:
                        policyName = policyNameFromModel(ctx, region, env, role, service, policy)
                        templateName = templateNameFromModel(ctx, service, policy)
                        '''
                        if policy == 'service' or policy == service:
                            policyName='%s-%s-%s' % (region, env, service)
                        else:
                            policyName='%s-%s-%s-%s' % (region, env, service, policy)
                        if service == 'default':
                            templateName= "%s.%s" % (service, policy)
                        else:
                            templateName= "%s" % (policy)
                        '''
                        if policyName not in modelPolicies:
                            options = {'region':ctx.region, 'env':env, 'role':role, 'service':service}
                            modelPolicy = renderPolicy(ctx, templateName, options)
                            modelPolicies[policyName]=modelPolicy
    ctx.vlog('loadModelPolicies: Done')
    '''
    # Fix up the default policies
    for region in modelPolicies:
        for env in modelPolicies[region]:
            if '*' in modelPolicies[region][env]:
                for role in modelPolicies[region][env]:
                    if role != '*':
                        modelPolicies[region][env][role].extend(modelPolicies[region][env]['*'])
                del modelPolicies[region][env]['*']
    '''
    return modelPolicies


def loadPolicyTemplates(ctx):
    if ctx.templateDir == None:
        print('loadPolicyTemplates: No templateDir')
        return None
    ctx.vlog('loadPolicyTemplates: Start')
    templates = {}
    path=ctx.templateDir
    for file in os.listdir(path):
        if file == 'default':
            continue
        with open(path+'/'+file, "r") as fd:
            templates[file.split('.')[0]] = fd.read()
    path = ctx.templateDir+'/default'
    for file in os.listdir(path):
        with open(path+'/'+file, "r") as fd:
            templates['default.' + file.split('.')[0]] = fd.read()
    ctx.vlog('loadPolicyTemplates: Done')
    return templates

'''
This method ensures that OrderdDict is used and puts the dict in proper order.
obj is the dict to be OrderedDict
ary is an array of ordered elements. This is mainly used to order the
policy statements returned from AWS, so they can be compared to model statemnts.
'''
class Reorder(object):
    def ___init___(self):
        self.model = None

    def do(self, obj):
        return OrderedDict((k, obj[k]) for k in self.model)

    def dolist(self, lorig):
        lnew = []
        for obj in lorig:
            lnew.append(OrderedDict((k, obj[k]) for k in self.model))
        return lnew
