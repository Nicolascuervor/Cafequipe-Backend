from rest_framework import serializers

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # We don't check if the user exists here intentionally to prevent user enumeration
        # The view will handle silent failure if user does not exist
        return value
