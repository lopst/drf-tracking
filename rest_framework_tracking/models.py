from django.db import models
from django.conf import settings
from rest_framework_tracking.managers import PrefetchUserManager

from django.core import exceptions
from django.db.models.fields.related import ForeignKey
from django.db.utils import ConnectionHandler, ConnectionRouter

connections = ConnectionHandler()
router = ConnectionRouter()


class CrossForeignKey(ForeignKey):

    def validate(self, value, model_instance):
        if self.rel.parent_link:
            return
        # Call the grandparent rather than the parent to skip validation
        super(ForeignKey, self).validate(value, model_instance)
        if value is None:
            return

        using = router.db_for_read(self.rel.to, instance=model_instance)
        qs = self.rel.to._default_manager.using(using).filter(
            **{self.rel.field_name: value}
        )
        qs = qs.complex_filter(self.get_limit_choices_to())
        if not qs.exists():
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={
                    'model': self.rel.to._meta.verbose_name, 'pk': value,
                    'field': self.rel.field_name, 'value': value,
                },  # 'pk' is included for backwards compatibility
            )


class BaseAPIRequestLog(models.Model):
    """Logs API requests by time, user, etc"""
    # user or None for anon
    user = CrossForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True)

    # timestamp of request
    requested_at = models.DateTimeField(db_index=True)

    # number of milliseconds to respond
    response_ms = models.PositiveIntegerField(default=0)

    # request path
    path = models.CharField(max_length=200, db_index=True)

    # remote IP address of request
    remote_addr = models.GenericIPAddressField()

    # originating host of request
    host = models.URLField()

    # HTTP method (GET, etc)
    method = models.CharField(max_length=10)

    # query params
    query_params = models.TextField(db_index=True, null=True, blank=True)

    # POST body data
    data = models.TextField(null=True, blank=True)

    # response
    response = models.TextField(null=True, blank=True)

    # status code
    status_code = models.PositiveIntegerField(null=True, blank=True)

    # custom manager
    objects = PrefetchUserManager()

    class Meta:
        abstract = True


class APIRequestLog(BaseAPIRequestLog):
    pass