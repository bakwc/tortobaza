from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import SectionPermission
from wishlist.models import Idea, WishlistItem
from wishlist.serializers import IdeaSerializer, WishlistItemSerializer


class WishlistListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]
    serializer_class = WishlistItemSerializer

    def get(self, request):
        return Response(self.serializer_class(WishlistItem.objects.all(), many=True).data)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class WishlistDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]
    serializer_class = WishlistItemSerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(WishlistItem.objects.all(), pk=pk)
        return Response(self.serializer_class(instance).data)

    def put(self, request, pk: int):
        instance = get_object_or_404(WishlistItem.objects.all(), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data)

    def delete(self, request, pk: int):
        instance = get_object_or_404(WishlistItem.objects.all(), pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IdeaListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]
    serializer_class = IdeaSerializer

    def get(self, request):
        return Response(self.serializer_class(Idea.objects.ordered(), many=True).data)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data, status=status.HTTP_201_CREATED)


class IdeaDetailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, SectionPermission("wishlist")]
    serializer_class = IdeaSerializer

    def get(self, request, pk: int):
        instance = get_object_or_404(Idea.objects.all(), pk=pk)
        return Response(self.serializer_class(instance).data)

    def put(self, request, pk: int):
        instance = get_object_or_404(Idea.objects.all(), pk=pk)
        serializer = self.serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self.serializer_class(instance).data)

    def delete(self, request, pk: int):
        instance = get_object_or_404(Idea.objects.all(), pk=pk)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
