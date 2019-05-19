from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponse
from fabric.context_managers import settings, hide
from fabric.api import run, env, prompt
from distutils.util import strtobool
from dockadm.docker import env, DockerConfigurator
from gixy.parser.nginx_parser import NginxParser

# for basic auth
import base64
from django.http import HttpResponse
from django.contrib.auth import authenticate
from django.conf import settings

env.user = 'root'
env.host = 'xxxx-host.xxxxx.cc'
env.host_string = 'xxxxx-host.xxxx.cc'
env.port = settings.DEFAULT_ENV_PORT
env.key_filename = '~/.ssh/id_rsa'
nginxconfdir = '/etc/nginx/conf.d/'

def view_or_basicauth(view, request, *args, **kwargs):
    # Check for valid basic auth header
    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2:
            # print(base64.b64decode(auth[1]).decode('UTF-8').split(':'))
            if auth[0].lower() == "basic":
                uname, passwd = base64.b64decode(auth[1]).decode('UTF-8').split(':')
                user = authenticate(username=uname, password=passwd)
                if user is not None and user.is_active:
                    request.user = user
                    return view(request, *args, **kwargs)

    response = HttpResponse()
    response.status_code = 401
    response['WWW-Authenticate'] = 'Basic realm="%s"' % settings.BASIC_AUTH_REALM
    return response


def basicauth(view_func):
    def wrapper(request, *args, **kwargs):
        return view_or_basicauth(view_func, request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@basicauth
def index(request):
    return render(request, 'index.html')


@basicauth
def create_container(request):
    if request.method == 'POST':
        rp = request.POST
        print(rp)
        # print(rp['default_zone'][1:])

        dc = DockerConfigurator(dockerfile='/root/docker/docker-compose.yml',
                                backuspdir="/root/docker/backups")

        messages.info(request, "project created: " +
                      dc.create_container(project=rp['proj_name'], container=rp["container"], ip=rp['ip']))

        return render(request, 'create_container.html')

    else:
        dc = DockerConfigurator(dockerfile='/root/docker/docker-compose.yml',
                                backuspdir="/root/docker/backups")

        messages.info(request, "addr in use: \r\n" + dc.get_occ_ipv4())
        return render(request, 'create_container.html')


@basicauth
def projectadd(request):
    if request.method == 'GET':
        containers = run("docker ps --format '{{.Names}}'")
        messages.info(request, "containers: \r\n"+containers)

        return render(request, 'add_project.html')

    if request.method == 'POST':
        dc = DockerConfigurator(dockerfile='/root/docker/docker-compose.yml',
                                backuspdir="/root/docker/backups")
        rp = request.POST
        container_name = rp['container']
        project_name = rp['proj_name']
        dc.add_project(container_name, project_name)

        messages.info(request, "project added")
        return render(request, 'add_project.html')


@basicauth
def domainadd(request):
    if request.method == 'GET':
        conf_files = run(
                'for i in $(ls '+nginxconfdir+'*.conf) ; do basename "$i" ; done')

        ret=""
        for conf in conf_files.split():
            ret += conf+"\r\n"

        messages.info(request, "conf files: \r\n"+ret)
        return render(request, 'domainadd.html')

    if request.method == 'POST':
        rp = request.POST

        config = rp['config_name']
        # env.host_string = rp['hostname']
        domain = rp['domain']
        temp = []

        with settings(hide('warnings', 'running', 'stdout', 'stderr'), warn_only=True):
            conf_file = run(
                'ls ' + nginxconfdir + config + '.conf'
            )

            nginx_config = run('cat ' + conf_file)
            print(nginx_config)

        if nginx_config:
            temp = temp + getnames(nginx_config)
            temp.append(domain)
            domain_names = ' '.join(temp)
            run("sed -i -r 's/server_name.*;/server_name " + domain_names + ";/g' " + conf_file)
            run("docker exec -it nginx nginx -s reload")

            # now check
            nginx_config = run('cat ' + conf_file)
            ret = str(getnames(nginx_config))
        else:
            ret = "config file not found, %s" % nginx_config

    return HttpResponse(ret)


def _get_parsed(config):
    root = NginxParser(cwd='', allow_includes=False).parse(config)
    return root.children[0]


def getnames(config):
    # ./tests/directives/test_block.py
    directive = _get_parsed(config)
    return ([x.args for x in directive.get_names()][0])
