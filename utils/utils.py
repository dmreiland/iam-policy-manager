import os
import json
import sys
from collections import OrderedDict
from jinja2 import Template
from jinja2 import FileSystemLoader
from jinja2.environment import Environment



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
    if templateName not in ctx.templates:
        ctx.log('renderPolicy: Error - %s is not in the set of available templates' % templateName)
        sys.exit(1)
    if templateName.startswith('default.'):
        templateName = 'default/%s' % templateName[len('default.'):]
    env = Environment()
    env.loader = FileSystemLoader(ctx.templateDir)
    jt = env.get_template(templateName)
    #jt = Template(templateName)
    #jt = Template(ctx.templates[templateName])
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
    props = {}
    props['ctx'] = ctx
    env = Environment()
    env.loader = FileSystemLoader(ctx.modelDir)
    jt = env.get_template(ctx.modelFile)
    doc = jt.render(props)
    model = json.loads(doc, object_pairs_hook=OrderedDict)
    return model


def loadModelPolicies(ctx):
    ctx.vlog('loadModelPolicies: Start')
    if ctx.templates == None:
        ctx.log("Cannot load model policies until templates are loaded")
        sys.exit(1)
    props = {}
    props['ctx'] = ctx

    modelPolicies = {}
    ctxPolicies = ctx.model['policies']
    for region in ctxPolicies:
        for env in ctxPolicies[region]:
            for service in ctxPolicies[region][env]:
                    for policyName in ctxPolicies[region][env][service]:
                        templateName =  ctxPolicies[region][env][service][policyName]
                        if policyName not in modelPolicies:
                            props['region'] = ctx.region
                            props['env'] = env
                            props['service'] = service
                            modelPolicy = renderPolicy(ctx, templateName, props)
                            modelPolicies[policyName]=modelPolicy
    ctx.vlog('loadModelPolicies: Done')
    return modelPolicies


def loadPolicyTemplates(ctx):
    if ctx.templateDir == None:
        print('loadPolicyTemplates: No templateDir')
        return None
    ctx.vlog('loadPolicyTemplates: Start')
    templates = {}
    path=ctx.templateDir
    for file in os.listdir(path):
        #if file == 'default':
        if file in ctx.templateExcludes:
            continue
        with open(path+'/'+file, "r") as fd:
            templates[file] = fd.read()
    path = ctx.templateDir+'/default'
    for file in os.listdir(path):
        with open(path+'/'+file, "r") as fd:
            templates['default.' + file] = fd.read()
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

def showPolicyJson(ctx, policyDoc, offset, width):
    lineLen = width - offset

    lines = policyDoc.splitlines()
    for line in lines:
        total = len(line)
        begin = 0
        end = lineLen
        while  begin < total:
            ctx.log('%*s%s'% (offset,' ', line[begin:end]))
            begin += lineLen
            end += lineLen
