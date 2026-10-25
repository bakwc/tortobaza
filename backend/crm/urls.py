from django.urls import path

from crm.views import (
    AnalyticsClientsView,
    AnalyticsLoadView,
    AnalyticsOverviewView,
    AnalyticsProductsView,
    CrmExpensesView,
    CrmSalariesView,
    CrmOrderClientMapView,
    CrmOrderClientView,
    CrmOrderDetailView,
    CrmOrderEventsView,
    CrmOrderListView,
    CrmOrderPaymentLinkView,
    CrmOrderMapView,
    ExchangeRatesView,
    FinanceAccountsView,
    FinanceTransactionDetailView,
    FinanceTransactionSearchView,
    FinanceTransactionsView,
    FlowwowWebhookView,
    ResolveGoogleAddressView,
    ResolveYandexAddressView,
)

urlpatterns = [
    path("webhooks/flowwow/", FlowwowWebhookView.as_view(), name="flowwow-webhook"),
    path("crm/analytics/overview/", AnalyticsOverviewView.as_view(), name="crm-analytics-overview"),
    path("crm/analytics/load/", AnalyticsLoadView.as_view(), name="crm-analytics-load"),
    path("crm/analytics/clients/", AnalyticsClientsView.as_view(), name="crm-analytics-clients"),
    path("crm/analytics/products/", AnalyticsProductsView.as_view(), name="crm-analytics-products"),
    path("crm/expenses/", CrmExpensesView.as_view(), name="crm-expenses"),
    path("crm/salaries/", CrmSalariesView.as_view(), name="crm-salaries"),
    path(
        "crm/finance/accounts/",
        FinanceAccountsView.as_view(),
        name="crm-finance-accounts",
    ),
    path(
        "crm/finance/transactions/search/",
        FinanceTransactionSearchView.as_view(),
        name="crm-finance-transaction-search",
    ),
    path(
        "crm/finance/transactions/<int:pk>/",
        FinanceTransactionDetailView.as_view(),
        name="crm-finance-transaction-detail",
    ),
    path(
        "crm/finance/transactions/",
        FinanceTransactionsView.as_view(),
        name="crm-finance-transactions",
    ),
    path(
        "crm/finance/exchange-rates/",
        ExchangeRatesView.as_view(),
        name="crm-finance-exchange-rates",
    ),
    path("crm/orders/map/", CrmOrderMapView.as_view(), name="crm-order-map"),
    path("crm/orders/", CrmOrderListView.as_view(), name="crm-order-list"),
    path(
        "crm/orders/client/<str:token>/map/",
        CrmOrderClientMapView.as_view(),
        name="crm-order-client-map",
    ),
    path(
        "crm/orders/client/<str:token>/",
        CrmOrderClientView.as_view(),
        name="crm-order-client",
    ),
    path("crm/orders/<int:pk>/", CrmOrderDetailView.as_view(), name="crm-order-detail"),
    path(
        "crm/orders/<int:pk>/payment-link/",
        CrmOrderPaymentLinkView.as_view(),
        name="crm-order-payment-link",
    ),
    path("crm/orders/<int:pk>/events/", CrmOrderEventsView.as_view(), name="crm-order-events"),
    path(
        "crm/resolve-yandex-address/",
        ResolveYandexAddressView.as_view(),
        name="crm-resolve-yandex-address",
    ),
    path(
        "crm/resolve-google-address/",
        ResolveGoogleAddressView.as_view(),
        name="crm-resolve-google-address",
    ),
]
