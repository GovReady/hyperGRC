# Build on Docker's official CentOS 7 image.
FROM centos:7

# Expose the port that hyperGRC listens on by default.
EXPOSE 8000

# Put the Python source code here.
WORKDIR /usr/src/app

# Set up the locale. Lots of things depend on this.
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV LANGUAGE en_US:en

# Install required system packages. Python 3.6 is available in IUS.
RUN  \
   yum -y install https://centos7.iuscommunity.org/ius-release.rpm \
&& yum -y update \
&& yum -y install \
	python36u python36u-pip \
	&& yum clean all && rm -rf /var/cache/yum

# Copy in the Python module requirements and install them.
COPY requirements.txt ./
RUN pip3.6 install --no-cache-dir -r requirements.txt

# Copy in remaining source code. (We put this last because these
# change most frequently, so there is less to rebuild if we put
# infrequently changed steps above.)
COPY VERSION VERSION
COPY example example
COPY hypergrc hypergrc
COPY static static

# Create an empty repos.conf file so the program doesn't die
# when run without command-line arguments.
RUN cat > repos.conf

# Create a non-root user and group for the application to run as to guard against
# run-time modification of the system and application.
RUN groupadd application && \
    useradd -g application -d /home/application -s /sbin/nologin -c "application process" application && \
    chown -R application:application /home/application
USER application

# Add the source files to the PYTHONPATH.
ENV PYTHONPATH="/usr/src/app:${PYTHONPATH}"

# Set the startup command to launch hyperGRC and bind on all network interfaces
# so that the host can connect. Since the end-user will not visit it at 0.0.0.0,
# override the address that hyperGRC will recommend that the user visit so there
# is no confusion.
ENTRYPOINT [ "/usr/bin/python3.6", \
             "-m", "hypergrc", \
             "--bind", "0.0.0.0:8000", \
             "--showaddress", "http://localhost:8000" ]

# Additionally set the default command-line argument. The CMD value below is
# simply appended to the ENTRYPOINT command-line to form the start command.
# We'll set it to "/opencontrol" so that hyperGRC looks there for an OpenControl
# repository, and then it is up to the host `docker container run` command to
# mount a volume at that location.
#
# The advantage of using CMD separately from ENTRYPOINT is that ENTRYPOINT cannot
# be changed by the `docker run` command, but CMD can be overridden simply by
# adding more arguments to the run command after the image name. So e.g.
# `docker container run hypergrc:latest /path1 /path2` would replace the default
# `/opencontrol` argument with two other container paths, if you want hyperGRC
# to read other directories.
CMD ["/opencontrol"]

