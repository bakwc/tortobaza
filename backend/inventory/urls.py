from django.urls import path

from inventory.views import (
    InventoryCountCloseView,
    InventoryCountDetailView,
    InventoryCountListView,
    MovementListView,
    ProductionDetailView,
    ProductionListView,
    StockView,
    SupplierDetailView,
    SupplierListView,
    SupplyDetailView,
    SupplyListView,
    SupplyTransactionListView,
    WriteOffDetailView,
    WriteOffListView,
    WriteOffReasonDetailView,
    WriteOffReasonListView,
)

urlpatterns = [
    path("inventory/stock/", StockView.as_view()),
    path("inventory/movements/", MovementListView.as_view()),
    path("inventory/suppliers/", SupplierListView.as_view()),
    path("inventory/suppliers/<int:pk>/", SupplierDetailView.as_view()),
    path("inventory/supplies/", SupplyListView.as_view()),
    path("inventory/supplies/<int:pk>/", SupplyDetailView.as_view()),
    path("inventory/supply-transactions/", SupplyTransactionListView.as_view()),
    path("inventory/productions/", ProductionListView.as_view()),
    path("inventory/productions/<int:pk>/", ProductionDetailView.as_view()),
    path("inventory/write-off-reasons/", WriteOffReasonListView.as_view()),
    path("inventory/write-off-reasons/<int:pk>/", WriteOffReasonDetailView.as_view()),
    path("inventory/write-offs/", WriteOffListView.as_view()),
    path("inventory/write-offs/<int:pk>/", WriteOffDetailView.as_view()),
    path("inventory/inventory-counts/", InventoryCountListView.as_view()),
    path("inventory/inventory-counts/<int:pk>/", InventoryCountDetailView.as_view()),
    path("inventory/inventory-counts/<int:pk>/close/", InventoryCountCloseView.as_view()),
]
