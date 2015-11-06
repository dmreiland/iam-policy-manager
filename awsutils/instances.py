import sys
import os.path
import boto3
from botocore.exceptions import ClientError
import json
import click
from jinja2 import Template
import utils.utils as utils
from awsutils import roles as aws_roles

def getTag(ctx, tags, tagName):
    for tag in tags:
        if tag['Key'] == tagName:
            return tag['Value']
    return None


def getFilteredInstances(ctx, filters):
    ec2 = ctx.ec2
    instances = []
    instancesByProfileId = {}
    irs = ec2.describe_instances(Filters=filters)
    for reservation in  irs['Reservations']:
        for instance in reservation['Instances']:
            #ctx.vlog('%s' % instance)
            instances.append(instance)
            id = 'NO_INSTANCE_PROFILE'
            if 'IamInstanceProfile' in instance:
                id = instance['IamInstanceProfile']['Id']
            if id in instancesByProfileId:
                instancesByProfileId[id].append(instance)
            else:
                instancesByProfileId[id] = []
                instancesByProfileId[id].append(instance)
    while 'NextToken' in irs:
        irs = ec2.describe_instances(Filters=filters)
        for reservation in  irs['Reservations']:
            for instance in reservation['Instances']:
                instances.append(instance)
                id = 'NO_INSTANCE_PROFILE'
                if 'IamInstanceProfile' in instance:
                    id = instance['IamInstanceProfile']['Id']
                if id in instancesByProfileId:
                    instancesByProfileId[id].append(instance)
                else:
                    instancesByProfileId[id] = []
                    instancesByProfileId[id].append(instance)
    return instances, instancesByProfileId



def getInstances(ctx, region, env):
    filters = []
    if region != None:
        filters.append({'Name':'tag:Region', 'Values':['%s'%region]})
    if env != None:
        filters.append({'Name':'tag:Environment', 'Values':['%s'%env]})
    ctx.nvlog('Getting ec2 instances...')
    instances, instancesByProfileId = getFilteredInstances(ctx, filters)
    ctx.vlog(' done')
    return instances, instancesByProfileId


def getInstancesByIAMInstanceProfileId(ctx, instanceProfileArn):
    ec2 = ctx.ec2
    instances = []
    filters = [{'Name':'iam-instance-profile.arn', 'Values':['%s'%instanceProfileArn]}]
    instances, instancesByProfileId = getFilteredInstances(ctx, filters)
    return instances, instancesByProfileId
