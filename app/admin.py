from django.contrib import admin
from .models import InterviewSession, Conversation, ExtractedAction, AnalysisResult

admin.site.register(InterviewSession)
admin.site.register(Conversation)
admin.site.register(ExtractedAction)
admin.site.register(AnalysisResult)
