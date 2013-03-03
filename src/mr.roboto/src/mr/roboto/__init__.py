from pyramid.config import Configurator

from security import RequestWithAttributes

from mr.roboto.db import PullsDB

from mr.roboto.plonegithub import PloneGithub
from jenkins import Jenkins


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings,
                          request_factory=RequestWithAttributes)

    # adds cornice
    config.include("cornice")
    config.registry.settings['roboto_url'] = settings['roboto_url']
    config.registry.settings['callback_url'] = settings['callback_url'] + '/callback/'
    config.registry.settings['api_key'] = settings['api_key']

    config.registry.settings['jenkins'] = Jenkins(settings['jenkins_url'], settings['jenkins_username'], settings['jenkins_password'])

    config.registry.settings['github'] = PloneGithub(settings['github_user'], settings['github_password'])

    config.registry.settings['pulls'] = PullsDB(settings['core_pulls_db'])

    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('home', '/')

    # adds cornice
    config.include("cornice")

    config.scan("mr.roboto.views")

    config.end()

    return config.make_wsgi_app()
