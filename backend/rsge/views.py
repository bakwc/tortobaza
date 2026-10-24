from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rsge.models import Waybill
from rsge.serializers import WaybillSerializer


class WaybillListView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        waybills = Waybill.objects.prefetch_related("goods").all()
        return Response(WaybillSerializer(waybills, many=True).data)
