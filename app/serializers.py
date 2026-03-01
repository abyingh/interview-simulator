from rest_framework import serializers
from .models import InterviewSession, AnalysisResult

# Convert objects to JSON 

class SessionCreateSerializer(serializers.Serializer):
    company_description = serializers.CharField()


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSession
        fields = '__all__'


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = '__all__'
