FROM python:2.7
MAINTAINER ITOH Akihiko

ADD ./git_deploy.conf.json.dist /root/git_deploy.conf.json
ADD ./git_deploy.py /root/git_deploy.py

EXPOSE 8001

WORKDIR /root
ENTRYPOINT ["python"]
CMD ["git_deploy.py --daemon-mode"]

