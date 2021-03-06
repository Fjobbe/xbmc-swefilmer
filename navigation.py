# -*- coding: utf-8 -*-
from mocks import Xbmc, Xbmcplugin, Xbmcgui, Xbmcaddon
import swefilmer
import sys
import urllib

ACTION_NEW = 'new'
ACTION_TOP = 'top'
ACTION_FAVORITES = 'favorites'
ACTION_CATEGORIES = 'categories'
ACTION_CATEGORY = 'category'
ACTION_SEARCH = 'search'
ACTION_VIDEO = 'video'
ACTION_NEXT_PAGE = 'next'

class Navigation(object):

    def __init__(self, xbmc, xbmcplugin, xbmcgui, xbmcaddon, swefilmer,
                 plugin_url, handle, params):
        self.xbmc = xbmc
        self.xbmcplugin = xbmcplugin
        self.xbmcgui = xbmcgui
        self.xbmcaddon = xbmcaddon
        self.swefilmer = swefilmer
        self.plugin_url = plugin_url
        self.handle = int(handle)
        self.params = self.swefilmer.parameters_string_to_dict(params)
        self.settings = xbmcaddon.Addon(id='plugin.video.swefilmer')
        self.localize = self.settings.getLocalizedString

    def get_credentials(self):
        username = self.settings.getSetting('username')
        password = self.settings.getSetting('password')
        return (username, password)

    def unikeyboard(self, default, message):
        keyboard = self.xbmc.Keyboard(default, message)
        keyboard.doModal()
        if (keyboard.isConfirmed()):
            return keyboard.getText()
        else:
            return None

    def quality_select_dialog(self, stream_urls):
        qualities = [s[0] for s in stream_urls]
        dialog = self.xbmcgui.Dialog()
        answer = 0
        if len(qualities) > 1:
            answer = dialog.select(self.localize(30201), qualities)
            if answer == -1:
                return None
        url = stream_urls[answer][1]
        return url

    def add_menu_item(self, caption, action, total_items, logged_in, url=None):
        li = self.xbmcgui.ListItem(caption)
        infoLabels = {'Title': caption}
        li.setInfo(type='Video', infoLabels=infoLabels)
        params = {'action': action, 'logged_in': logged_in}
        if url:
            params['url'] = url
        item_url = self.plugin_url + '?' + urllib.urlencode(params)
        self.xbmcplugin.addDirectoryItem(handle=self.handle, url=item_url,
                                         listitem=li, isFolder=True,
                                         totalItems=total_items)

    def add_video_item(self, caption, url, image, action, total_items, logged_in):
        li = self.xbmcgui.ListItem(caption)
        li.setProperty('IsPlayable', 'true')
        if image:
            li.setThumbnailImage(image)
        infoLabels = {'Title': caption}
        li.setInfo(type='Video', infoLabels=infoLabels)
        params = {'action': action, 'url': url, 'logged_in': logged_in}
        item_url = self.plugin_url + '?' + urllib.urlencode(params)
        self.xbmcplugin.addDirectoryItem(handle=self.handle, url=item_url,
                                         listitem=li, isFolder=False,
                                         totalItems=total_items)

    def start_menu(self):
        logged_in = False
        (username, password) = self.get_credentials()
        if username and len(username) > 0:
            logged_in = self.swefilmer.login(username, password)
            if not logged_in:
                self.xbmcgui.Dialog().ok(self.localize(30501),
                                         self.localize(30502))
        total_items = 5 if logged_in else 4
        self.add_menu_item(self.localize(30101), ACTION_NEW, total_items,
                           logged_in)
        self.add_menu_item(self.localize(30102), ACTION_TOP, total_items,
                           logged_in)
        if logged_in:
            self.add_menu_item(self.localize(30103), ACTION_FAVORITES,
                               total_items, logged_in)
        self.add_menu_item(self.localize(30104), ACTION_CATEGORIES,
                           total_items, logged_in)
        self.add_menu_item(self.localize(30105), ACTION_SEARCH, total_items,
                           logged_in)
        return True

    def new_menu(self):
        html = self.swefilmer.new_menu_html()
        return self.scrape_list(html)

    def top_menu(self):
        html = self.swefilmer.top_menu_html()
        return self.scrape_list(html)

    def favorites_menu(self):
        html = self.swefilmer.favorites_menu_html()
        return self.scrape_list(html)

    def categories_menu(self):
        html = self.swefilmer.categories_menu_html()
        ret, pagination = self.swefilmer.scrape_categories(html)
        total_items = len(ret)
        for (url, name), img in ret:
            self.add_menu_item(name, ACTION_CATEGORY, total_items, 
                               self.params['logged_in'], url)
        return True

    def category_menu(self):
        if not 'browse-serier' in self.params['url']:
            return self.next_page()
        html = self.swefilmer.menu_html(self.params['url'])
        ret, pagination = self.swefilmer.scrape_series(html)
        total_items = len(ret) + len(pagination)
        for (url, name), img in ret:
            self.add_menu_item(name, ACTION_CATEGORY, total_items,
                               self.params['logged_in'], url)
        if pagination:
            self.add_menu_item(self.localize(30301), ACTION_NEXT_PAGE,
                               total_items,
                               self.params['logged_in'], pagination[0])
        return True

    def search_menu(self):
        try:
            latest_search = self.settings.getSetting("latestSearch")
        except KeyError:
            latest_search = ""
        search_string = self.unikeyboard(latest_search, "")
        if search_string == "": return
        self.settings.setSetting("latestSearch", search_string)
        html = self.swefilmer.search_menu_html(search_string)
        return self.scrape_list(html)

    def next_page(self):
        url = self.params['url']
        html = self.swefilmer.menu_html(url)
        return self.scrape_list(html)

    def scrape_list(self, html):
        ret, pagination = self.swefilmer.scrape_list(html)
        total_items = len(ret) + len(pagination)
        for (url, name), img in ret:
            self.add_video_item(name, url, img, ACTION_VIDEO, total_items,
                                self.params['logged_in'])
        if pagination:
            self.add_menu_item(self.localize(30301), ACTION_NEXT_PAGE,
                               total_items, self.params['logged_in'],
                               pagination[0])
        return True

    def video(self):
        url = self.params['url']
        html = self.swefilmer.video_html(url)
        result = self.swefilmer.scrape_video(html)
        if not result:
            if not self.params['logged_in']:
                self.xbmcgui.Dialog().ok(self.localize(30401),
                                         self.localize(30402),
                                         self.localize(30403))
            else:
                self.xbmcgui.Dialog().ok(self.localize(30601),
                                         self.localize(30602))
            self.xbmcplugin.setResolvedUrl(
                self.handle, succeeded=False,
                listitem=self.xbmcgui.ListItem(''))
            return False
        name, description, img, streams = result
        self.xbmc.log('video: name=' + str(name))
        self.xbmc.log('video: description=' + str(description))
        self.xbmc.log('video: img=' + str(img))
        self.xbmc.log('video: streams=' + str(streams))
        if len(url) > 1:
            url = self.quality_select_dialog(streams)
            if not url:
                self.xbmcplugin.setResolvedUrl(
                    self.handle, succeeded=False,
                    listitem=self.xbmcgui.ListItem(''))
                return False
        else:
            url = url[0][1]
        list_item = self.xbmcgui.ListItem(name)
        if img:
            list_item.setThumbnailImage(img[0])
        infoLabels = {'Title': name}
        if description:
            infoLabels['Plot'] = description[0]
        list_item.setInfo(type="Video", infoLabels=infoLabels)
        list_item.setPath(url)
        self.xbmcplugin.setResolvedUrl(self.handle, True, list_item)
        return True

    def dispatch(self):
        ret = False
        if not 'action' in self.params:
            ret = self.start_menu()
        else:
            action = self.params['action']
            if action == ACTION_NEW:
                ret = self.new_menu()
            elif action == ACTION_TOP:
                ret = self.top_menu()
            elif action == ACTION_FAVORITES:
                ret = self.favorites_menu()
            elif action == ACTION_CATEGORIES:
                ret = self.categories_menu()
            elif action == ACTION_CATEGORY:
                ret = self.category_menu()
            elif action == ACTION_SEARCH:
                ret = self.search_menu()
            elif action == ACTION_VIDEO:
                ret = self.video()
            elif action == ACTION_NEXT_PAGE:
                ret = self.next_page()
        return self.xbmcplugin.endOfDirectory(self.handle, succeeded=ret,
                                              cacheToDisc=True)

# Use of standalone Navigation for testing:
# python navigation.py <params>
if __name__ == '__main__':
    xbmc = Xbmc(level=Xbmc.LOGNOTICE)
    xbmcplugin = Xbmcplugin(xbmc)
    xbmcgui = Xbmcgui()
    xbmcaddon = Xbmcaddon()
    swe = swefilmer.Swefilmer(xbmc, xbmcplugin, xbmcgui, xbmcaddon)
    navigation = Navigation(xbmc, xbmcplugin, xbmcgui, xbmcaddon, swe,
                            'plugin', '10', '?' + sys.argv[1])
    navigation.dispatch()
