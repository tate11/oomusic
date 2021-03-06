# -*- coding: utf-8 -*-

import datetime
import hashlib
import logging
from random import sample
import time

import requests
from werkzeug.urls import url_fix

from odoo import models, api, fields
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class MusicLastfm(models.Model):
    _name = 'oomusic.lastfm'
    _description = 'LastFM Cache Management'

    name = fields.Char('URL Hash', index=True, required=True)
    url = fields.Char('URL', required=True)
    content = fields.Char('Result', required=True)
    expiry_date = fields.Datetime('Expiry Date', required=True)
    removal_date = fields.Datetime('Removal Date', required=True)

    _sql_constraints = [
        ('oomusic_lastfm_name_uniq', 'unique(name)', 'URL hash must be unique!'),
    ]

    def get_query(self, url, sleep=0.0, force=False):
        # Get LastFM key and cache duration
        ConfigParam = self.env['ir.config_parameter'].sudo()
        fm_key = ConfigParam.get_param('oomusic.lastfm_key')
        fm_cache = int(ConfigParam.get_param('oomusic.lastfm_cache', 112))
        fm_info = ConfigParam.get_param('oomusic.fm_info', 'auto')
        if not fm_key:
            return '{}'

        url = url_fix(url + '&api_key=' + fm_key + '&format=json').encode('utf-8')
        url_hash = hashlib.sha1(url).hexdigest()

        new_cr = self.pool.cursor()
        Lastfm = self.with_env(self.env(cr=new_cr)).search([('name', '=', url_hash)])
        if force or not Lastfm or Lastfm.expiry_date < fields.Datetime.now():
            content = '{}'
            if fm_info == 'manual' and not force:
                Lastfm.env.cr.rollback()
                Lastfm.env.cr.close()
                content = Lastfm.content or content
                return content
            try:
                time.sleep(sleep)
                r = requests.get(url, timeout=3.0)
                if r.status_code == 200:
                    content = r.content.decode('utf-8')
            except:
                _logger.info('Error while fetching URL "%s"', url, exc_info=True)

            expiry_date = datetime.datetime.utcnow() + datetime.timedelta(days=fm_cache)
            removal_date = datetime.datetime.utcnow() + datetime.timedelta(days=fm_cache + 14)

            # Save in cache
            with self.pool.cursor() as cr:
                new_self = Lastfm.with_env(self.env(cr=cr))
                if not Lastfm:
                    writer = new_self.create
                else:
                    writer = new_self.write
                writer({
                    'name': url_hash,
                    'url': url,
                    'content': content,
                    'expiry_date': expiry_date.strftime(DATETIME_FORMAT),
                    'removal_date': removal_date.strftime(DATETIME_FORMAT),
                })

        else:
            content = Lastfm.content or '{}'

        Lastfm.env.cr.rollback()
        Lastfm.env.cr.close()
        return content

    @api.model
    def cron_build_lastfm_cache(self):
        # Build cache for artists. Limit to 200 artists chosen randomly to avoid running for
        # unexpectedly long periods of time.
        self.env.cr.execute('SELECT name from oomusic_artist')
        res = self.env.cr.fetchall()
        artists = {r[0] for r in res}
        for artist in sample(artists, min(200, len(artists))):
            _logger.debug("Gettting LastFM cache for artist \"%s\"...", artist)
            url = 'https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist=' + artist
            self.get_query(url)
            url = 'https://ws.audioscrobbler.com/2.0/?method=artist.gettoptracks&artist=' + artist
            self.get_query(url)
            url = 'https://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist=' + artist
            self.get_query(url, sleep=1.0)

        # Clean-up outdated entries
        self.search([('removal_date', '<', fields.Datetime.now())]).unlink()
