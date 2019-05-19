FROM khanhicetea/php7-fpm-docker

RUN apt update
RUN apt install -y php7.1-xdebug curl bash vim tar python-pip iputils-ping
RUN pip install pexpect

RUN sed -i "s/upload_max_filesize =.*/upload_max_filesize = 100M/" /etc/php/7.1/fpm/php.ini
RUN sed -i "s/post_max_size =.*/post_max_size = 100M/" /etc/php/7.1/fpm/php.ini
RUN sed -i "s/error_reporting =.*/error_reporting = E_ALL \& \~E_DEPRECATED \& \~E_STRICT \& \~E_NOTICE/" /etc/php/7.1/fpm/php.ini

#ssh
RUN apt install -y openssh-server
RUN echo "root:broooooooooooot" | chpasswd
RUN sed -i 's/prohibit-password/yes/' /etc/ssh/sshd_config
RUN useradd -ms /bin/bash user
RUN echo "user:wooooooooot" | chpasswd

#gitlab
RUN curl -s https://packages.gitlab.com/install/repositories/runner/gitlab-ci-multi-runner/script.deb.sh | bash
RUN apt update
RUN apt install -y gitlab-ci-multi-runner
RUN sed -i -r  's/"--user" "gitlab-runner"/"--user" "root"/g' /etc/init.d/gitlab-runner

RUN mkdir /root/.ssh
RUN echo "ssh-rsa kindashortforpubkeyyep? testkey" > /root/.ssh/authorized_keys

CMD service gitlab-runner start && /etc/init.d/ssh start && php-fpm7.1
