from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class PluginApp(AppConfig):
    name = 'pretix_dpsg_sepadebit'
    verbose_name = 'SEPA Direct debit for pretix for the dpsg accounting department'

    class PretixPluginMeta:
        name = gettext_lazy('SEPA Direct debit DPSG')
        category = 'PAYMENT'
        author = 'Lukas Bockstaller'
        description = gettext_lazy('This plugin adds SEPA direct debit support in a format the dpsg accounting department likes to pretix')
        visible = True
        version = '1.6.2'

    def ready(self):
        from . import signals  # NOQA


default_app_config = 'pretix_dpsg_sepadebit.PluginApp'
