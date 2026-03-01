from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    # Web pages
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.dashboard, name='dashboard'),

    # JWT auth
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # REST API: url + view
    path('api/sessions/', views.SessionListCreateView.as_view(), name='sessions'),
    path('api/sessions/<int:session_id>/start/', views.StartInterviewsView.as_view(), name='start'),
    path('api/sessions/<int:session_id>/progress/', views.ProgressView.as_view(), name='progress'),
    path('api/sessions/<int:session_id>/analysis/', views.AnalysisView.as_view(), name='analysis'),
    path('api/sessions/<int:session_id>/board-deck/', views.BoardDeckView.as_view(), name='board_deck'),
    path('api/sessions/<int:session_id>/conversations/', views.ConversationsListView.as_view(), name='conversations'),
    path('api/sessions/<int:session_id>/conversations/<int:conversation_id>/', views.ConversationDetailView.as_view(), name='conversation_detail')
]
