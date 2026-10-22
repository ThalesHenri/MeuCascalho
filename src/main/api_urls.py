from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from main.views.api import CategoryViewSet, EntryViewSet, GoalViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('entries', EntryViewSet, basename='entry')
router.register('goals', GoalViewSet, basename='goal')

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
