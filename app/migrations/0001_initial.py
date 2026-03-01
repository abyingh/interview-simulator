import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

# 1st migration: Create all tables
class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InterviewSession',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('company_description', models.TextField()),
                    ('num_interviews', models.IntegerField()),
                    ('completed_interviews', models.IntegerField(default=0)),
                    ('status', models.CharField(choices=[('pending', 'Pending'), ('running', 'Running'), ('extracting', 'Extracting'), ('clustering', 'Clustering'), ('summarizing', 'Summarizing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                    ('roles', models.JSONField(blank=True, default=list)),
                    ('created_at', models.DateTimeField(auto_now_add=True)),
                    ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL))]
        ),
        migrations.CreateModel(
            name='Conversation',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('employee_role', models.CharField(max_length=200)),
                    ('messages', models.JSONField(default=list)),
                    ('created_at', models.DateTimeField(auto_now_add=True)),
                    ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='app.interviewsession'))]
        ),
        migrations.CreateModel(
            name='ExtractedAction',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('action_text', models.TextField()),
                    ('embedding', models.JSONField(blank=True, null=True)),
                    ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='actions', to='app.conversation'))]
        ),
        migrations.CreateModel(
            name='AnalysisResult',
            fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('themes', models.JSONField(default=list)),
                    ('created_at', models.DateTimeField(auto_now_add=True)),
                    ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analysis', to='app.interviewsession'))]
        )
    ]
