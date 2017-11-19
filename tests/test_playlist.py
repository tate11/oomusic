# -*- coding: utf-8 -*-

import json

from . import test_common


class TestOomusicPlaylist(test_common.TestOomusicCommon):

    def test_00_create_interact(self):
        '''
        Test creation and basic interaction
        '''
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

        playlist = self.PlaylistObj.create({'name': 'crotte'})

        # _onchange_album_id
        album1 = self.AlbumObj.search([('name', '=', 'Album1')])
        playlist.album_id = album1
        playlist._onchange_album_id()
        self.assertEqual(playlist.album_id, self.AlbumObj)
        self.assertEqual(
            playlist.mapped('playlist_line_ids').mapped('track_id').mapped('name'),
            [u'Song1', u'Song2']
        )
        playlist.action_purge()

        # _onchange_artist_id
        artist1 = self.ArtistObj.search([('name', '=', 'Artist1')])
        playlist.artist_id = artist1
        playlist._onchange_artist_id()
        self.assertEqual(playlist.artist_id, self.ArtistObj)
        self.assertEqual(
            playlist.mapped('playlist_line_ids').mapped('track_id').mapped('name'),
            [u'Song3', u'Song4', u'Song1', u'Song2']
        )
        playlist.action_purge()

        # action_current
        playlist.action_current()
        playlist.invalidate_cache()
        playlist_search = self.PlaylistObj.search([('current', '=', True)])
        self.assertEqual(playlist_search, playlist)

        self.cleanUp()

    def test_10_create_interact(self):
        '''
        Test creation and basic interaction of playlist lines
        '''
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

        tracks = self.TrackObj.search([], limit=2)
        playlist = self.PlaylistObj.search([('current', '=', True)], limit=1)

        # Create
        playlist_line = self.PlaylistLineObj.create({
            'playlist_id': playlist.id,
            'track_id': tracks[0].id
        })
        self.assertEqual(tracks[0].in_playlist, True)

        # Write
        playlist_line.write({
            'track_id': tracks[1].id
        })
        self.assertEqual(tracks[0].in_playlist, False)
        self.assertEqual(tracks[1].in_playlist, True)

        # Unlink
        playlist_line.unlink()
        self.assertEqual(tracks[1].in_playlist, False)

        self.cleanUp()

    def test_20_player_interaction(self):
        '''
        Test player interaction: play, next...
        '''
        self.FolderScanObj.with_context(test_mode=True)._scan_folder(self.Folder.id)

        playlist1 = self.PlaylistObj.search([('current', '=', True)], limit=1)
        playlist2 = self.PlaylistObj.create({'name': 'crotte'})
        artist1 = self.ArtistObj.search([('name', '=', 'Artist1')])
        artist2 = self.ArtistObj.search([('name', '=', 'Artist2')])

        playlist1.artist_id = artist1
        playlist1.raw = True
        playlist1._onchange_artist_id()
        playlist2.artist_id = artist2
        playlist2._onchange_artist_id()

        # oomusic_set_current
        playlist1.playlist_line_ids[0].playing = True
        playlist2.playlist_line_ids[0].oomusic_set_current()
        playlist2.invalidate_cache()
        self.assertEqual(playlist1.current, False)
        self.assertEqual(playlist2.current, True)
        self.assertEqual(playlist1.playlist_line_ids[0].playing, False)
        self.assertEqual(playlist2.playlist_line_ids[0].playing, True)
        self.assertEqual(playlist2.playlist_line_ids[0].track_id.play_count, 1)

        # oomusic_play
        res = json.loads(playlist1.playlist_line_ids[0].with_context(test_mode=True).oomusic_play())
        track = playlist1.playlist_line_ids[0].track_id
        self.assertEqual(res['track_id'], track.id)
        self.assertEqual(res['title'], '{} - {}'.format(track.artist_id.name, track.name))
        self.assertEqual(res['duration'], track.duration)
        self.assertEqual(res['image'], 'TEST')
        src = res['src'][0].split('?')
        src[1] = src[1].split('&')
        src[1].sort()
        self.assertEqual(src[0], '/oomusic/trans/{}.mp3'.format(track.id))
        self.assertEqual(src[1], [u'norm=0', u'raw=1', u'seek=0'])
        src = res['src'][1].split('?')
        src[1] = src[1].split('&')
        src[1].sort()
        self.assertEqual(src[0], '/oomusic/trans/{}.opus'.format(track.id))
        self.assertEqual(src[1], [u'norm=0', u'raw=0', u'seek=0'])
        src = res['src'][2].split('?')
        src[1] = src[1].split('&')
        src[1].sort()
        self.assertEqual(src[0], '/oomusic/trans/{}.ogg'.format(track.id))
        self.assertEqual(src[1], [u'norm=0', u'raw=0', u'seek=0'])
        src = res['src'][3].split('?')
        src[1] = src[1].split('&')
        src[1].sort()
        self.assertEqual(src[0], u'/oomusic/trans/{}.mp3'.format(track.id))
        self.assertEqual(src[1], [u'norm=0', u'raw=0', u'seek=0'])

        # oomusic_next
        res = json.loads(playlist1.playlist_line_ids[0].with_context(test_mode=True).oomusic_next())
        track = playlist1.playlist_line_ids[1].track_id
        self.assertEqual(res['track_id'], track.id)
        res = json.loads(playlist1.playlist_line_ids[-1].with_context(test_mode=True).oomusic_next())
        track = playlist1.playlist_line_ids[0].track_id
        self.assertEqual(res['track_id'], track.id)

        # oomusic_previous
        res = json.loads(playlist1.playlist_line_ids[0].with_context(test_mode=True).oomusic_previous())
        track = playlist1.playlist_line_ids[-1].track_id
        self.assertEqual(res['track_id'], track.id)
        res = json.loads(playlist1.playlist_line_ids[1].with_context(test_mode=True).oomusic_previous())
        track = playlist1.playlist_line_ids[0].track_id
        self.assertEqual(res['track_id'], track.id)

        # oomusic_last_track
        res = json.loads(playlist1.playlist_line_ids[0].with_context(test_mode=True).oomusic_last_track())
        track = playlist2.playlist_line_ids[0].track_id
        self.assertEqual(res['track_id'], track.id)

        self.cleanUp()