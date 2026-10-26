from django.contrib.auth import views as auth_views
from django.urls import path
from main.views.web import (
    CategoryCreateView,
    CategoryDeleteView,
    CategoryListView,
    CategoryUpdateView,
    DashboardView,
    EntryCreateView,
    EntryDeleteView,
    EntryUpdateView,
    GoalCreateView,
    GoalDeleteView,
    GoalListView,
    GoalUpdateView,
    RegisterView,
)

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='main/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', RegisterView.as_view(), name='register'),
    path('entries/new/', EntryCreateView.as_view(), name='entry-create'),
    path('entries/<int:pk>/edit/', EntryUpdateView.as_view(), name='entry-update'),
    path('entries/<int:pk>/delete/', EntryDeleteView.as_view(), name='entry-delete'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/new/', CategoryCreateView.as_view(), name='category-create'),
    path('categories/<int:pk>/edit/', CategoryUpdateView.as_view(), name='category-update'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category-delete'),
    path('goals/', GoalListView.as_view(), name='goal-list'),
    path('goals/new/', GoalCreateView.as_view(), name='goal-create'),
    path('goals/<int:pk>/edit/', GoalUpdateView.as_view(), name='goal-update'),
    path('goals/<int:pk>/delete/', GoalDeleteView.as_view(), name='goal-delete'),
]

