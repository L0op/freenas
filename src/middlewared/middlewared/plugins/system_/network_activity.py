# -*- coding=utf-8 -*-
import logging

from middlewared.service import accepts, CallError, private, Service

logger = logging.getLogger(__name__)


class SystemAdvancedService(Service):

    class Config:
        namespace = 'system.advanced'

    activities = {}

    @private
    def register_network_activity(self, name, description):
        if name in self.activities:
            raise RuntimeError(f'Network activity {name} is already registered')

        self.activities[name] = description

    @accepts()
    def network_activity_choices(self):
        """
        Returns allowed/forbidden network activity choices.
        """
        return sorted(list(self.activities.items()), key=lambda t: t[1].lower())

    @private
    async def can_perform_network_activity(self, name):
        if name not in self.activities:
            raise RuntimeError(f'Unknown network activity {name}')

        config = await self.middleware.call('system.advanced.config')
        if config['network_activity']['type'] == 'ALLOW':
            return name in config['network_activity']['activities']
        else:
            return name not in config['network_activity']['activities']

    @private
    async def will_perform_network_activity(self, name):
        if not await self.middleware.call('system.advanced.can_perform_network_activity', name):
            raise CallError(f'Network activity "{self.activities[name]}" is disabled')
