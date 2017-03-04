from django.db.models import CharField
import uuid

class UUIDField(CharField):
    def __init__(self, auto=True, *args, **kwargs):
        self.auto = auto
        kwargs['max_length'] = 32
        if auto:
            kwargs['editable'] = False
            kwargs['blank'] = True
            kwargs['unique'] = True
        super(UUIDField, self).__init__(*args, **kwargs)

    def _create_uuid(self):
        return uuid.uuid4()

    def db_type(self, connection=None):
        return 'char(%s)' % self.max_length

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname, None)
        if self.auto and add and not value:
            # Assign a new value for this attribute if required.
            value = self._create_uuid().hex
            setattr(model_instance, self.attname, value)
        return value

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        from south.modelsinspector import introspector
        field_class = "fields.UUIDField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)
