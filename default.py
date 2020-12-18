# -*- coding: utf-8 -*-

###############################################################################
from __future__ import absolute_import, division, unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import object
import logging
from sys import argv
from urllib.parse import parse_qsl

import xbmc
import xbmcgui
import xbmcplugin

from resources.lib import entrypoint, utils, transfer, variables as v, loghandler
from resources.lib.tools import unicode_paths

###############################################################################

loghandler.config()
LOG = logging.getLogger('PLEX.default')

###############################################################################

HANDLE = int(argv[1])


class Main(object):
    # MAIN ENTRY POINT
    # @utils.profiling()
    def __init__(self):
        LOG.debug('Full sys.argv received: %s', argv)
        # Parse parameters
        params = dict(parse_qsl(argv[2][1:]))
        arguments = unicode_paths.decode(argv[2])
        path = unicode_paths.decode(argv[0])
        # Ensure unicode
        for key, value in params.items():
            params[key.decode('utf-8')] = params.pop(key)
            params[key] = value.decode('utf-8')
        mode = params.get('mode', '')
        itemid = params.get('id', '')

        if mode == 'play':
            self.play()

        elif mode == 'plex_node':
            self.play()

        elif mode == 'browseplex':
            entrypoint.browse_plex(key=params.get('key'),
                                   plex_type=params.get('plex_type'),
                                   section_id=params.get('section_id'),
                                   synched=params.get('synched') != 'false',
                                   prompt=params.get('prompt'),
                                   query=params.get('query'))

        elif mode == 'show_section':
            entrypoint.show_section(params.get('section_index'))

        elif mode == 'watchlater':
            entrypoint.watchlater()

        elif mode == 'channels':
            entrypoint.browse_plex(key='/channels/all')

        elif mode == 'search':
            # "Search"
            entrypoint.browse_plex(key='/hubs/search',
                                   args={'includeCollections': 1,
                                         'includeExternalMedia': 1},
                                   prompt=utils.lang(137),
                                   query=params.get('query'))

        elif mode == 'route_to_extras':
            # Hack so we can store this path in the Kodi DB
            handle = ('plugin://%s?mode=extras&plex_id=%s'
                      % (v.ADDON_ID, params.get('plex_id')))
            if xbmcgui.getCurrentWindowId() == 10025:
                # Video Window
                xbmc.executebuiltin('Container.Update(\"%s\")' % handle)
            else:
                xbmc.executebuiltin('ActivateWindow(videos, \"%s\")' % handle)

        elif mode == 'extras':
            entrypoint.extras(plex_id=params.get('plex_id'))

        elif mode == 'settings':
            xbmc.executebuiltin('Addon.OpenSettings(%s)' % v.ADDON_ID)

        elif mode == 'enterPMS':
            LOG.info('Request to manually enter new PMS address')
            transfer.plex_command('enter_new_pms_address')

        elif mode == 'reset':
            transfer.plex_command('RESET-PKC')

        elif mode == 'togglePlexTV':
            LOG.info('Toggle of Plex.tv sign-in requested')
            transfer.plex_command('toggle_plex_tv_sign_in')

        elif mode == 'passwords':
            from resources.lib.windows import direct_path_sources
            direct_path_sources.start()

        elif mode == 'switchuser':
            LOG.info('Plex home user switch requested')
            transfer.plex_command('switch_plex_user')

        elif mode in ('manualsync', 'repair'):
            if mode == 'repair':
                LOG.info('Requesting repair lib sync')
                transfer.plex_command('repair-scan')
            elif mode == 'manualsync':
                LOG.info('Requesting full library scan')
                transfer.plex_command('full-scan')

        elif mode == 'texturecache':
            LOG.info('Requesting texture caching of all textures')
            transfer.plex_command('textures-scan')

        elif mode == 'chooseServer':
            LOG.info("Choosing PMS server requested, starting")
            transfer.plex_command('choose_pms_server')

        elif mode == 'deviceid':
            self.deviceid()

        elif mode == 'fanart':
            LOG.info('User requested fanarttv refresh')
            transfer.plex_command('fanart-scan')

        elif '/extrafanart' in path:
            plexpath = arguments[1:]
            plexid = itemid
            entrypoint.extra_fanart(plexid, plexpath)
            entrypoint.get_video_files(plexid, plexpath)

        # Called by e.g. 3rd party plugin video extras
        elif ('/Extras' in path or '/VideoFiles' in path or
                '/Extras' in arguments):
            plexId = itemid or None
            entrypoint.get_video_files(plexId, params)

        elif mode == 'playlists':
            entrypoint.playlists(params.get('content_type'))

        elif mode == 'hub':
            entrypoint.hub(params.get('content_type'))

        elif mode == 'select-libraries':
            LOG.info('User requested to select Plex libraries')
            transfer.plex_command('select-libraries')

        elif mode == 'refreshplaylist':
            LOG.info('User requested to refresh Kodi playlists and nodes')
            transfer.plex_command('refreshplaylist')

        else:
            entrypoint.show_main_menu(content_type=params.get('content_type'))

    @staticmethod
    def play():
        """
        Start up playback_starter in main Python thread
        """
        request = '%s&handle=%s' % (argv[2], HANDLE)
        # Put the request into the 'queue'
        transfer.plex_command('PLAY-%s' % request)
        if HANDLE == -1:
            # Handle -1 received, not waiting for main thread
            return
        # Wait for the result from the main PKC thread
        result = transfer.wait_for_transfer(source='main')
        if result is True:
            xbmcplugin.setResolvedUrl(HANDLE, False, xbmcgui.ListItem())
            # Tell main thread that we're done
            transfer.send(True, target='main')
        else:
            # Received a xbmcgui.ListItem()
            xbmcplugin.setResolvedUrl(HANDLE, True, result)

    @staticmethod
    def deviceid():
        window = xbmcgui.Window(10000)
        deviceId_old = window.getProperty('plex_client_Id')
        from resources.lib import clientinfo
        try:
            deviceId = clientinfo.getDeviceId(reset=True)
        except Exception as e:
            LOG.error('Failed to generate a new device Id: %s' % e)
            utils.messageDialog(utils.lang(29999), utils.lang(33032))
        else:
            LOG.info('Successfully removed old device ID: %s New deviceId:'
                     '%s' % (deviceId_old, deviceId))
            # 'Kodi will now restart to apply the changes'
            utils.messageDialog(utils.lang(29999), utils.lang(33033))
            xbmc.executebuiltin('RestartApp')


if __name__ == '__main__':
    LOG.info('%s started' % v.ADDON_ID)
    try:
        v.database_paths()
    except RuntimeError as err:
        # Database does not exists
        LOG.error('The current Kodi version is incompatible')
        LOG.error('Error: %s', err)
    else:
        Main()
    LOG.info('%s stopped' % v.ADDON_ID)
