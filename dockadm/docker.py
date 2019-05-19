#!/usr/bin/env python3

import sys, yaml, datetime
import pexpect
from fabric.api import run, env
from django.conf import settings

env.port = settings.DEFAULT_ENV_PORT

ngxdest = "/etc/nginx/conf.d/"
composedir = "/root/docker/"
composefile = "/root/docker/docker-compose.yml"
backuspdir = "/root/docker/backups"
phpdockerfile = "config/dockerfiles/php7.1.conf"
gitlab_runners_confdir = "/opt/gitlab-runners"
gitlab_example_config = "/opt/gitlab-runners/example/config.toml"
nginx_cont_name = "nginx"
gitlab_token = "xxxxxxxxxxxxxxxxx"
server_ip = "144.76.xxx.xxx"
server_if = "enp2s0"

env.user = 'root'
none_to_str = lambda x: x or ''


class DockerConfigurator(object):
    def __init__(self, dockerfile, backuspdir):

        self.now = datetime.datetime.now()
        self.nowstr = "{0}.{1}.{2}.{3}:{4}".format(self.now.year,
                                                   self.now.month,
                                                   self.now.day,
                                                   self.now.hour,
                                                   self.now.minute)
        self.backuspdir = backuspdir
        self.dockerfile = dockerfile
        self.projects = 'PROJECTS_PLACEHOLDER'
        self.ngxcfg = {}
        self.project = ""
        self.container = ""

        self.__yml = self.parse()

    def create_container(self, project, container, ip):
        self.project = project
        self.container = container

        free_ext_port = self.free_external_port()

        self.add_nginx_volume(self.project)
        self.create_container_config(vol=self.project, contname=self.container, ip=ip, localport=free_ext_port)
        self.create_nginx_config(project=self.project, upstream=self.container)

        # contport = self.add_iptables_ssh(ip)

        self.writefiles()

        run("cd " + composedir + " && docker-compose up --build -d " + container)
        run("cd " + composedir + " && docker-compose up --build -d " + nginx_cont_name)

        run("cp /opt/gitlab-runners/example/config.toml /opt/gitlab-runners/"+container+"/config.toml ")

        self.register_runner(free_ext_port)

        ret = "{project} ssh: {server}:{port}".format(project=self.project, server=server_ip, port=free_ext_port)

        return ret

    def add_project(self, container_name, project):
        target = self.__yml["services"][container_name]
        old_volumes = self.__yml["services"][container_name]["volumes"]
        old_volumes += ['/var/www/'+project+':/var/www/'+project]
        target["volumes"] = old_volumes

        self.add_nginx_volume(project)
        self.create_nginx_config(project=project, upstream=container_name)
        self.writefiles()

        run("cd " + composedir + " && docker-compose up --build -d " + nginx_cont_name)
        run("cd " + composedir + " && docker-compose up --build -d " + container_name)


    def parse(self):
        return yaml.load(run("cat " + self.dockerfile))

    def writeyaml(self, content, dest):
        run("echo \"" + yaml.dump(content) + "\" > " + dest)

    def writefile(self, content, dest):
        run("echo '"+content+"' > " + dest)

    def writefiles(self):
        # for nginx
        for project, cfg in self.ngxcfg.items():
            self.writefile(cfg, ngxdest + project + ".conf")

        # for docker-compose.yml
        run("ls " + self.backuspdir + " || mkdir -p " + self.backuspdir)
        run("cp " + self.dockerfile + " " + self.backuspdir + "/" + self.dockerfile.split('/')[-1] +
            "." + self.nowstr+'.yml')

        # writing new file
        self.writeyaml(self.__yml, self.dockerfile)

    # def __pprint(self, obj):
    #     pp = pprint.PrettyPrinter(indent=0)
    #     pp.pprint(obj)

    def add_nginx_volume(self, vol):
        # print(self.__yml)
        ngxvol = self.__yml["services"][nginx_cont_name]["volumes"]
        ngxvol += ["/var/www/" + str(vol) + ":/var/www/" + str(vol) + ":ro"]
        self.__yml["services"]["nginx"]["volumes"] = ngxvol

    def create_container_config(self, vol, contname, ip, localport):
        services = self.__yml["services"]

        services.update({contname: {'build': {'context': '.',
                                             'dockerfile': phpdockerfile},
                                   'container_name': contname,
                                   'depends_on': ['db'],
                                   'expose': ['9000'],
                                   'networks': {'static-network': {'ipv4_address': ip}},
                                   'ports': ["'"+server_ip+':'+localport+':22'],
                                   'restart': 'always',
                                   'volumes': ['/var/www/' + vol + ':/var/www/' + vol,
                                               gitlab_runners_confdir+"/"+contname+"/" + ":/etc/gitlab-runner"]}})

        self.__yml["services"] = services

    def create_nginx_config(self, project, upstream):
        ngxcfg = """server {{
  listen 80;
  server_name {project} www.{project};

    root /var/www/{project};
    error_log /var/log/nginx/{project}.err;

    location / {{
        try_files $uri /index.php$is_args$args;
    }}

    location ~ \.php$ {{
        fastcgi_pass {upstream}:9000;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }}

}}""".format(project=project, upstream=upstream)

        self.ngxcfg.update({project: ngxcfg})

    def get_occ_ipv4(self):
        ret = []
        for cont in self.__yml["services"]:
            ret.append(self.__yml["services"][cont]['networks']['static-network']["ipv4_address"])

        return str(sorted(ret, key=lambda x: tuple(map(int, x.split('.')))))

    def free_external_port(self):
        return run("expr $(iptables-save | grep DOCKER | grep xxx\.xxx\.xxx\.xxx | awk 'match($0, /dport [0-9]+/) { print substr($0, RSTART+6, RLENGTH-6) }' | sort -n | tail -1) + 1")

    def register_runner(self, contport):
        # run("docker restart " + self.container)

        env.port = contport
        run("ip a")
        run("gitlab-runner  -v")
        run("echo \"" + """

try:
    child = pexpect.spawn('/usr/bin/gitlab-runner register')
    child.expect('Running in system-mode.*')
    child.sendline('https://git.xxxxxxxxxx.com/')
    child.expect('Please enter the gitlab-ci token for this runner:')
    child.sendline('{gitlab_token}')
    child.expect('Please enter the gitlab-ci description for this runner:')
    child.sendline('{project}')
    child.expect('.*')
    child.sendline('{project},')
    child.expect('Whether to run untagged builds.*')
    child.sendline('true')
    child.expect('Whether to lock Runner to current project.*')
    child.sendline('false')
    child.expect('Registering runner... succeeded.*')
    child.sendline('shell')
    child.expect('Runner registered successfully.*')
except:
    print('except')
    print(str(child))""".format(gitlab_token=gitlab_token, project=self.project) + "\" > /tmp/reg.py")



        run("python /tmp/reg.py")

        env.port = settings.DEFAULT_ENV_PORT
        run("ip a")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: " + sys.argv[0] + " <file.yml> project.xxx.cc project2.xxx.cc ... projectN.xxx.cc")
        exit(0)

    dockerfile = sys.argv[1]
    project = sys.argv[2:] if sys.argv[2:] else None

    dc = DockerConfigurator(dockerfile)
    dc.create_container(project=project)
