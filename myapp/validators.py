
# this imports ValidationError for raising exceptions during validation
from django.core.exceptions import ValidationError
# this import re module for regular expression operations
import re

class CustomPasswordValidator:
    # validate the given password
    def validate(self, password, user=None):
        # checks if the password length is less than 8 characters
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
       

    # provide a description of the password requirements
    def get_help_text(self):
        return "Your password must contain at least 8 characters, including an uppercase letter and one special character."


