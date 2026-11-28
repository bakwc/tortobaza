from django.urls import path

from wishlist.views import (
    IdeaDetailView,
    IdeaListView,
    TaskAssigneeListView,
    TaskCommentDetailView,
    TaskCommentListView,
    TaskDetailView,
    TaskListView,
    WishlistDetailView,
    WishlistListView,
)

urlpatterns = [
    path("wishlist/", WishlistListView.as_view()),
    path("wishlist/ideas/", IdeaListView.as_view()),
    path("wishlist/ideas/<int:pk>/", IdeaDetailView.as_view()),
    path("wishlist/tasks/assignees/", TaskAssigneeListView.as_view()),
    path("wishlist/tasks/", TaskListView.as_view()),
    path("wishlist/tasks/<int:pk>/", TaskDetailView.as_view()),
    path("wishlist/tasks/<int:pk>/comments/", TaskCommentListView.as_view()),
    path("wishlist/tasks/<int:pk>/comments/<int:comment_pk>/", TaskCommentDetailView.as_view()),
    path("wishlist/<int:pk>/", WishlistDetailView.as_view()),
]
