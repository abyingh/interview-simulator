from django.db import models
from django.contrib.auth.models import User

# Data models for interview sessions, conversations, and analysis results
# Each class = one table. Each attribute = one column
class InterviewSession(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'),
                      ('running', 'Running'),
                      ('extracting', 'Extracting'),
                      ('clustering', 'Clustering'),
                      ('summarizing', 'Summarizing'),
                      ('completed', 'Completed'),
                      ('failed', 'Failed')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company_description = models.TextField()
    num_interviews = models.IntegerField()
    completed_interviews = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    roles = models.JSONField(default=list, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.id}: {self.status}"


class Conversation(models.Model):
    session = models.ForeignKey(InterviewSession, related_name='conversations', on_delete=models.CASCADE) # links to which session this conversation belongs to
    employee_role = models.CharField(max_length=200)
    messages = models.JSONField(default=list) # {"role": "interviewer/employee", "content": ...}
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.session_id}: {self.employee_role}"


class ExtractedAction(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='actions', on_delete=models.CASCADE)
    action_text = models.TextField()
    embedding = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.action_text[:30]


class AnalysisResult(models.Model):
    session = models.OneToOneField(InterviewSession, related_name='analysis', on_delete=models.CASCADE)
    themes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.session_id}: Analysis"
