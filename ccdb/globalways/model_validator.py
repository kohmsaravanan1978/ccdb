from django.core.exceptions import ValidationError


class ModelValidator(object):
    """
    Use the model validator to outsource all validation concerns of your model into one place.
    Inherit this class and implement your model specific validation.

    class MyModelValidator(ModelValidator):

        def validate(self):
            self._validate_name()

        def _validate_name(self):
            if self.instance.name == 'Mustermann':
                # add a field errors
                self.add_field_error('name', 'Dont add test data)
                # add a global error
                self.add_error('Lorem Ipsum')


    class MyModel(models.Model):

        def clean(self):
            v = MyModelValidator(self)
            v.run()

    """

    def __init__(self, instance):
        """
        Constructor; Takes the model instance and makes it available under self.instance.
        Additionally introduces self.error_dict. Add your errors here in order to provide field-specific error
        messages.
        :param instance: the model instance
        """
        self.instance = instance
        self.errors = {"__all__": []}

    def run(self):
        """
        This is the public interface.
        Call this method in your model's clean method to trigger the cleaning process.
        """
        self.validate()
        if self._has_errors():
            raise ValidationError(self.errors)

    def validate(self):
        """
        Implement your custom validation methods here.
        Please outsource each cleaning concern to a separate method in order to provide better units for testing.
        :return: None
        """
        pass

    def add_field_error(self, field_name, msg):
        """
        Adds a field-specific error.
        :param field_name: name of the field
        :param msg: the error message
        """
        if field_name not in self.errors:
            self.errors[field_name] = []

        self.errors[field_name].append(msg)

    def add_error(self, msg):
        """
        Adds an error related to the whole model instance.
        :param msg:
        :return:
        """
        self.errors["__all__"].append(msg)

    def _has_errors(self):
        """
        Returns a boolean indicating whether or not there are errors.
        :return:
        """
        return len(self.errors["__all__"]) or len(self.errors.keys()) > 1
