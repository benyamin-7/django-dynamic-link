#!/usr/bin/python
# -*- coding:utf-8 -*-
# This Python file uses the following encoding: utf-8

__author__ = "Andreas Fritz - sources.e-blue.eu"
__copyright__ = "Copyright (c) " + "28.08.2010" + " Andreas Fritz"
__licence__ = "New BSD Licence"


import presettings
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
import random
import os
import datetime
from django.utils import timezone

class Download(models.Model):
    slug = models.SlugField(verbose_name=_('slug'), blank=False, unique=True)
    active = models.BooleanField(default=True,
                                 verbose_name=_(u'is aktive'),
                                 )
    file_path = models.FilePathField(
                                      path=presettings.DYNAMIC_LINK_MEDIA,
                                      help_text=_(u"Select the content your like \
                                      to provide."),
                                      verbose_name=_(u'content to serve'),
                                      blank=True,
                                      recursive=True
                                      )
    link_key = models.CharField(max_length=50, editable=False, unique=True)
    timestamp_creation = models.DateTimeField(
                                              auto_now=False,
                                              auto_now_add=True,
                                              editable=False,
                                              verbose_name=_(u'creation time'),
                                              )
    timeout_hours = models.IntegerField(verbose_name=_(u'timout in hours'), \
                                        default=72, help_text=_('Zero value means no timeout.'))
    max_clicks = models.IntegerField(verbose_name=_(u'maximum allowed clicks'), \
                                     default=3, help_text=_('Zero value means no limitation.'))
    current_clicks = models.IntegerField(default=0, verbose_name=_(u'current clicks'))

    def get_filename(self):
        return os.path.basename(self.file_path)

    def timeout_clicks(self):
        """If max clicks reached than it returns True"""
        # dont cange the order
        if not self.max_clicks == 0: # max clicks 0 means never expired through clicks
            if self.current_clicks >= self.max_clicks: # if number of max clicks reached
                return True

    def timeout_time(self):
        """If timout time is reached it returs True"""
        if not self.timeout_hours == 0: # never timeout through time
            if self.timestamp_creation + datetime.timedelta(hours=self.timeout_hours) < timezone.now():
                return True

    def timeout(self):
        """
        In case of timeout (clicks or expired time) it returns True
        """
        if self.timeout_time():
            return True
        if self.timeout_clicks():
            return True

    def get_timout_time(self):
        """Is shown at the admit list display"""
        if self.timeout_hours == 0:
            return '<span style="color: #FF7F00; ">%s</span>' % unicode(_(u'never expires'))
        return (self.timestamp_creation + datetime.timedelta(hours=self.timeout_hours)) - timezone.now()

    def set_link(self, file, slug='autogenerated', timeout=None, maxclicks=None):
        self.slug = slug
        self.file_path = file.split(os.path.basename(settings.MEDIA_ROOT))[-1]
        if timeout:
            self.timeout_hours = timeout
        if maxclicks:
            self.max_clicks = maxclicks
        self.save()

    def __setup_instance(self):
        """
        Check if object instance expired and keep values of the istance actual.
        """
        # Keep the order of the tests

        # 1. Test of timeout
        if self.timeout():
            if self.active:
                self.active = False
                self.save()
                raise IsExpiredError()

        # 2. set max click values
        if self.current_clicks < self.max_clicks:
            self.current_clicks += 1
            # check of last cklick
            if self.current_clicks == self.max_clicks:
                self.active = False # if it was the last allowed cklick then set to expired
            self.save()
        elif self.max_clicks == 0:
            self.current_clicks += 1
            self.save()

    def get_path(self):
        """
        if active it returns the full path of stored file to serve.
        if expired it returns None
        """
        self.__setup_instance()
        return self.file_path

    def __gen_key(self):
        """
        function for generating random keys
        """
        #key = str(time.time()).replace('.', '')
        key = '' # for shorter keys
        characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890'
        key_length = 30
        for y in range(key_length):
            key += characters[random.randint(0, len(characters)-1)]
        return key

    def save(self, * args, ** kwargs):
        """Perform custom methodes before saving."""
        # If not avalible set unique link key bevor saving
        if not self.link_key:
            self.link_key = self.__gen_key()
        # call the real save method
        super(Download, self).save(*args, ** kwargs) # Call the "real" save() method

    def __unicode__(self):
        return '%s: %s, %s: %s' % (unicode(_(u'Slug')), self.slug, unicode(_(u'Filename')), self.get_filename())

class IsExpiredError(Exception):
    """Error class for expired link objects"""
    def __init__(self, value=''):
        self.value = presettings.TEXT_REQUEST_IS_EXPIRED + value
    def __str__(self):
        return repr(self.value)
