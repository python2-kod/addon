# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# Canale per serietvonline
# ----------------------------------------------------------
import re

from core import httptools, scrapertoolsV2, servertools, tmdb
from core.item import Item
from lib import unshortenit
from platformcode import logger, config
from channels import autoplay
from channels.support import menu
from channelselector import thumb

host = "https://serietvonline.co"
headers = [['Referer', host]]

IDIOMAS = {'Italiano': 'IT'}
list_language = IDIOMAS.values()
list_servers = ['wstream', 'backin', 'akvideo', 'vidto', 'nowvideo']
list_quality = ['default']

PERPAGE = 30

def mainlist(item):
    logger.info(item.channel + 'mainlist')

    itemlist = web_menu()
    menu(itemlist, "Cerca Film... color blue", 'search', '', 'movie')
    menu(itemlist, "Cerca Serie... color blue", 'search', '', 'episode')

    autoplay.init(item.channel, list_servers, list_quality)
    autoplay.show_option(item.channel, itemlist)
                
    return itemlist


def web_menu():
    itemlist=[]

    data = httptools.downloadpage(host, headers=headers).data
    matches = scrapertoolsV2.find_multiple_matches(data, r'<li class="page_item.*?><a href="([^"]+)">(.*?)<\/a>')
    blacklist = ['DMCA','Contatti','Attenzione NON FARTI OSCURARE']

    for url, title in matches:
        if not title in blacklist:
            title = title.replace('Lista ','') + ' bold'
            if 'film' in title.lower():
                contentType = 'movie'
            else:
                contentType = 'episode'
            menu(itemlist, title, 'peliculas', url,contentType=contentType)            

    return itemlist



def search(item, texto):
    logger.info(item.channel + 'search' + texto)

    item.url = host + "/?s= " + texto
    
    return search_peliculas(item)

def search_peliculas(item):
    logger.info(item.channel + 'search_peliculas')

    logger.info('TYPE= ' + item.contentType)

    if item.contentType == 'movie':
        action = 'findvideos'
    else:
        action = 'episodios'

    itemlist = []
    data = httptools.downloadpage(item.url, headers=headers).data
    logger.info('DATA SEARCH= ' + data)

    patron = r'<a href="([^"]+)"><span[^>]+><[^>]+><\/a>[^h]+h2>(.*?)<'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for url, title in matches:
       
        title = scrapertoolsV2.decodeHtmlentities(title)
        itemlist.append(
            Item(channel=item.channel,
                 action=action,
                 contentType=item.contentType,
                 fulltitle=title,
                 show=title,
                 title=title,
                 url=url))
   
    next_page = scrapertoolsV2.find_single_match(data, "<a rel='nofollow' class=previouspostslink href='([^']+)'")
    
    if next_page != "":
        itemlist.append(
            Item(channel=item.channel,
                 action="search_peliculas",
                 contentType=item.contentType,
                 title="[COLOR blue]" + config.get_localized_string(30992) + " >[/COLOR]",
                 url=next_page))

    tmdb.set_infoLabels_itemlist(itemlist, seekTmdb=True)
    return itemlist


def peliculas(item):
    logger.info(item.channel + 'peliculas')
    itemlist = []

    if item.contentType == 'movie':
        action = 'findvideos'
    else:
        action = 'episodios'

    page = 1
    if '{}' in item.url:
        item.url, page = item.url.split('{}')
        page = int(page)

    data = httptools.downloadpage(item.url, headers=headers).data
    block = scrapertoolsV2.find_single_match(data, r'id="lcp_instance_0">(.*?)<\/ul>')
    matches = re.compile(r'<a\s*href="([^"]+)" title="([^<]+)">[^<]+</a>', re.DOTALL).findall(block)

    for i, (url, title) in enumerate(matches):
        if (page - 1) * PERPAGE > i: continue
        if i >= page * PERPAGE: break
        title = scrapertoolsV2.decodeHtmlentities(title)
        itemlist.append(
            Item(channel=item.channel,
                 action=action,
                 title=title,
                 fulltitle=title,
                 url=url,
                 contentType=item.contentType,
                 show=title))

    if len(matches) >= page * PERPAGE:
        url = item.url + '{}' + str(page + 1)
        itemlist.append(
            Item(channel=item.channel,
                 extra=item.extra,
                 action="peliculas",
                 title="[COLOR blue]" + config.get_localized_string(30992) + " >[/COLOR]",
                 url=url,
                 thumbnail=thumb(),
                 contentType=item.contentType))

    tmdb.set_infoLabels_itemlist(itemlist, seekTmdb=True)
    return itemlist


def episodios(item):
    logger.info(item.channel + 'episodios')
    itemlist = []

    data = httptools.downloadpage(item.url, headers=headers).data
    block= scrapertoolsV2.find_single_match(data, r'<table>(.*?)<\/table>')

    matches = re.compile(r'<tr><td>(.*?)</td><tr>', re.DOTALL).findall(block)

    for episode in matches:
        episode = "<td class=\"title\">" + episode
        logger.info('EPISODE= ' + episode)
        title = scrapertoolsV2.find_single_match(episode, '<td class="title">(.*?)</td>')
        title = title.replace(item.title, "")
        if scrapertoolsV2.find_single_match(title, '([0-9]+x[0-9]+)'):            
            title = scrapertoolsV2.find_single_match(title, '([0-9]+x[0-9]+)') + ' - ' + re.sub('([0-9]+x[0-9]+)',' -',title)
        elif scrapertoolsV2.find_single_match(title, ' ([0-9][0-9])') and not scrapertoolsV2.find_single_match(title, ' ([0-9][0-9][0-9])'):  
            title = '1x' + scrapertoolsV2.find_single_match(title, ' ([0-9]+)') + ' - ' + re.sub(' ([0-9]+)',' -',title)
        itemlist.append(
            Item(channel=item.channel,
                 action="findvideos",
                 fulltitle=title,
                 show=title,
                 title=title,
                 url=episode,
                 folder=True))

    if config.get_videolibrary_support() and len(itemlist) > 0:
        itemlist.append(
            Item(channel=item.channel, title='[COLOR blue][B]'+config.get_localized_string(30161)+'[/B][/COLOR]', url=item.url,
                 action="add_serie_to_library", extra="episodios", show=item.show))

    return itemlist


def findvideos(item):
    logger.info(item.channel + 'findvideos')
    itemlist=[]
    logger.info('TYPE= ' + item.contentType)
    if item.contentType == 'movie':
        data = httptools.downloadpage(item.url, headers=headers).data
        logger.info('DATA= ' + data)
        item.url= scrapertoolsV2.find_single_match(data, r'<table>(.*?)<\/table>')

    urls = scrapertoolsV2.find_multiple_matches(item.url, r"<a href='([^']+)'.*?>.*?>.*?([a-zA-Z]+).*?<\/a>")
    
    for url, server in urls:
        itemlist.append(
            Item(channel=item.channel,
                 action='play',
                 title=item.title + ' [COLOR blue][' + server + '][/COLOR]',
                 server=server,
                 url=url))

    autoplay.start(itemlist, item)

    if item.contentType != 'episode':
        if config.get_videolibrary_support() and len(itemlist) > 0:
            itemlist.append(
                Item(channel=item.channel, title='[COLOR blue][B]'+config.get_localized_string(30161)+'[/B][/COLOR]', url=item.url,
                     action="add_pelicula_to_library", extra="findvideos", contentTitle=item.fulltitle))

    return itemlist


def play(item):

    data, c = unshortenit.unshorten(item.url)

    itemlist = servertools.find_video_items(data=data)

    for videoitem in itemlist:
        videoitem.title = item.title
        videoitem.fulltitle = item.fulltitle
        videoitem.show = item.show
        videoitem.thumbnail = item.thumbnail
        videoitem.channel = item.channel

    return itemlist


